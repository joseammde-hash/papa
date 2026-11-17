"""Motor del bot: percepción por pantalla, decisiones y planificador de zonas.

No lee memoria del juego ni inyecta nada: solo mira píxeles de la pantalla y
simula pulsaciones de teclado, como haría una persona.
"""
import json
import threading
import time
import random
from dataclasses import dataclass
from skillbook import SkillBook, analyze_hotbar
from monsters import MonsterDB, clean_name, plan_zone, xp_gain
from guide import load_guide, step_for
from gamescan import GameData
from pathlib import Path

BASE = Path(__file__).parent
CONFIG_PATH = BASE / "config.json"
KNOWLEDGE_PATH = BASE / "knowledge.json"
ROUTES_PATH = BASE / "routes.json"
LEARNED_PATH = BASE / "skills_learned.json"
MONSTERS_PATH = BASE / "monsters.json"


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------------
# Conocimiento de Aion: qué zona toca según el nivel
# --------------------------------------------------------------------------
class ZonePlanner:
    def __init__(self, zones):
        self.zones = sorted(zones, key=lambda z: z["min"])

    def recommend(self, level, gear_bonus=0):
        """Zona recomendada: la de mayor nivel mínimo que el nivel efectivo ya cumple.
        gear_bonus suma niveles 'virtuales' por llevar equipo muy fuerte."""
        eff = level + gear_bonus
        ok = [z for z in self.zones if z["min"] <= eff]
        if not ok:
            return self.zones[0]
        top = max(z["min"] for z in ok)
        return next(z for z in ok if z["min"] == top)      # con empate, la primera de la tabla

    def by_name(self, name):
        for z in self.zones:
            if z["name"].lower() == str(name).lower():
                return z
        return None


# --------------------------------------------------------------------------
# Percepción
# --------------------------------------------------------------------------
@dataclass
class Status:
    hp: float | None = None      # 0..1, None = barra sin calibrar
    mp: float | None = None
    thp: float | None = None     # vida del objetivo
    level: int | None = None
    slots: list | None = None    # barra de acceso rápido escaneada
    xp: float | None = None      # barra de experiencia (0..1)


def bar_fraction(pixels, color, tol=60):
    """Fracción llenada de una barra a partir de una fila de píxeles RGB.
    Cuenta desde la izquierda tolerando huecos de hasta 3 px (bordes, brillos)."""
    last, gap = -1, 0
    for i, p in enumerate(pixels):
        if all(abs(a - b) <= tol for a, b in zip(p[:3], color)):
            last, gap = i, 0
        else:
            gap += 1
            if gap > 3 and last >= 0:
                break
    return (last + 1) / len(pixels) if pixels else 0.0


class ScreenPerception:
    def __init__(self, cfg):
        import pyautogui  # import tardío: los tests no lo necesitan
        self.pg = pyautogui
        self.cfg = cfg

    def _bar(self, key):
        b = self.cfg["bars"].get(key) or {}
        if not b.get("region") or not b.get("color"):
            return None
        x1, y1, x2, y2 = b["region"]
        ymid = (y1 + y2) // 2
        img = self.pg.screenshot(region=(x1, ymid, max(1, x2 - x1), 1))
        px = [img.getpixel((i, 0)) for i in range(img.width)]
        return bar_fraction(px, b["color"], b.get("tol", 60))

    def _ocr(self, reg, whitelist=None, invert=False):
        try:
            import pytesseract
            x1, y1, x2, y2 = reg
            img = self.pg.screenshot(region=(x1, y1, x2 - x1, y2 - y1)).convert("L")
            img = img.point(lambda v: (0 if v > 140 else 255) if invert else (255 if v > 140 else 0))
            img = img.resize(((x2 - x1) * 3, (y2 - y1) * 3))
            cfg = "--psm 7" + (f" -c tessedit_char_whitelist={whitelist}" if whitelist else "")
            return pytesseract.image_to_string(img, config=cfg).strip()
        except Exception:
            return None

    def _level(self):
        reg = self.cfg["bars"].get("level_region")
        if not reg:
            return None
        try:
            lv = int(self._ocr(reg, "0123456789"))
            return lv if 1 <= lv <= 65 else None
        except (TypeError, ValueError):
            return None

    def game_focused(self, title):
        """True/False si la ventana activa contiene 'title'; None si no se puede saber."""
        from vision import foreground_title
        t = foreground_title()
        return None if t is None else title.lower() in t.lower()

    def read_name(self):
        """Nombre del objetivo actual (OCR). None si no hay región o no se puede leer."""
        reg = self.cfg["bars"].get("target_name_region")
        return clean_name(self._ocr(reg)) if reg else None

    def _slots(self):
        hb = self.cfg.get("hotbar") or {}
        if not hb.get("region"):
            return None
        x1, y1, x2, y2 = hb["region"]
        return analyze_hotbar(self.pg.screenshot(region=(x1, y1, x2 - x1, y2 - y1)), hb)

    def read(self):
        return Status(self._bar("hp"), self._bar("mp"), self._bar("target"),
                      self._level(), self._slots(), self._bar("xp"))


class Actuator:
    def __init__(self, mode="pyautogui"):
        import pyautogui
        import inputs
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.02
        self.pg = pyautogui
        self.sc = mode == "scancode" and inputs.available()     # teclas por scancode (juegos que ignoran las normales)
        self.inputs = inputs

    def press(self, key):
        combo = "+" in key and key != "+"      # combinaciones tipo 'shift+1'
        if self.sc:
            self.inputs.hotkey(key.split("+")) if combo else self.inputs.press(key)
        elif combo:
            self.pg.hotkey(*key.split("+"))
        else:
            self.pg.press(key)

    def click(self, x, y):
        self.pg.click(x, y)

    def down(self, key):
        self.inputs.key_down(key) if self.sc else self.pg.keyDown(key)

    def up(self, key):
        self.inputs.key_up(key) if self.sc else self.pg.keyUp(key)


def excluded_keys(cfg):
    """Teclas que el bot nunca debe tratar como habilidades aprendidas (pociones, sistema, rotación manual)."""
    ex = {cfg["potions"]["hp"]["key"], cfg["potions"]["mp"]["key"]}
    ex |= set(cfg["keys"].values())
    if cfg.get("auto_skills", {}).get("mode") != "auto":
        ex |= {sk["key"] for sk in cfg["skills"]}
    return ex


# --------------------------------------------------------------------------
# Cerebro
# --------------------------------------------------------------------------
class Brain:
    """Un 'tick' cada ~0.25 s: mira el estado y decide una acción."""

    def __init__(self, cfg, knowledge, perception, actuator,
                 clock=time.time, log=print, alert=None, routes=None, sleep=time.sleep,
                 book=None, db=None):
        self.cfg, self.perc, self.act = cfg, perception, actuator
        self.db = db if db is not None else MonsterDB.load(MONSTERS_PATH)
        self.should_stop = lambda: False
        self.guide = load_guide()
        self.gamedata = GameData.load()
        self.book = book if book is not None else SkillBook.load(LEARNED_PATH, log)
        self.sleep = sleep
        self.planner = ZonePlanner(knowledge["zones"])
        self.clock, self.log = clock, log
        self.alert_fn = alert or (lambda msg: log("⚠ " + msg))
        self.routes = routes or {}
        self.reset()

    def reset(self):
        self.last_used = {}
        self.in_combat = False
        self.opener_pending = False
        self.lost_ticks = 0
        self.kills = 0
        self.dead_ticks = 0
        self.resting = False
        self.rest_start = 0
        self.next_skill_time = 0
        self.last_target_try = 0
        self.target_fails = 0
        self.last_progress = 0
        self.last_thp = 1.0
        self.blind_until = 0
        self.last_kill_time = self.clock()
        self.last_zone_check = 0
        self.notified_zone = None
        self.request_pause = False
        self.started = self.clock()
        self.last_status = Status()
        self.pending_obs = []
        self.explored = 0
        self.fight = None
        self.pending_name = None
        self.xp_idle = None
        self.skip_streak = 0
        self.last_tick = None
        self.last_spot_check = 0
        self.last_approach = 0
        self.warned_routes = set()
        self.notified_step = None
        self.last_focus_warn = -1e9
        self.focus_state = None

    # -- utilidades -------------------------------------------------------
    @property
    def power(self):
        return int(self.cfg["character"].get("gear_power", 0))

    def _ready(self, name, cooldown, now):
        return now - self.last_used.get(name, -1e9) >= cooldown

    def _use(self, name, key, now):
        self.act.press(key)
        self.last_used[name] = now

    def _alert(self, msg):
        self.alert_fn(msg)

    def kills_per_hour(self):
        h = (self.clock() - self.started) / 3600
        return self.kills / h if h > 0.01 else 0.0

    # -- reglas -----------------------------------------------------------
    def _potions(self, s, now):
        pots = self.cfg["potions"]
        acts = []
        hp_below = max(10, pots["hp"]["below"] - 10 * self.power) / 100
        mp_below = pots["mp"]["below"] / 100
        if s.hp is not None and s.hp < hp_below and \
                self._ready("pot_hp", pots["hp"]["cooldown"], now):
            self._use("pot_hp", pots["hp"]["key"], now)
            self.log(f"Poción de vida (vida {s.hp:.0%})")
            if self.fight:
                self.fight["potions"] += 1
            acts.append("potion_hp")
        if s.mp is not None and s.mp < mp_below and \
                self._ready("pot_mp", pots["mp"]["cooldown"], now):
            self._use("pot_mp", pots["mp"]["key"], now)
            self.log(f"Poción de maná (maná {s.mp:.0%})")
            acts.append("potion_mp")
        return acts

    def _pick_skill(self, s, now):
        thp = 1.0 if s.thp is None else s.thp
        for sk in self.cfg["skills"]:
            if not sk.get("enabled", True):
                continue
            if sk.get("opener") and not self.opener_pending:
                continue
            if not self._ready("skill:" + sk["name"], sk.get("cooldown", 0), now):
                continue
            if thp * 100 > sk.get("target_hp_max", 100) or thp * 100 < sk.get("target_hp_min", 0):
                continue
            if s.hp is not None and s.hp * 100 > sk.get("self_hp_max", 100):
                continue
            if s.mp is not None and s.mp * 100 < sk.get("min_mp", 0):
                continue
            return sk
        return None

    def _fight(self, s, now):
        acts = []
        if not self.in_combat:
            self.in_combat = True
            self.opener_pending = True
            self.last_progress = now
            self.last_thp = s.thp if s.thp is not None else 1.0
            self.explored = 0
            self.fight = {"name": self.pending_name, "xp0": self.xp_idle, "hp0": s.hp, "t0": now,
                          "potions": 0, "minhp": s.hp if s.hp is not None else 1.0}
            self.log("Combate iniciado" + (f" contra {self.pending_name}" if self.pending_name else ""))
        if s.thp is not None:
            if s.thp < self.last_thp - 0.005:
                self.last_progress = now
            self.last_thp = s.thp
        if self.fight and s.hp is not None:
            self.fight["minhp"] = min(self.fight["minhp"], s.hp)
        bh = self.cfg["behavior"]
        if bh.get("approach_key") and s.thp is not None and \
                now - self.last_progress > bh.get("approach_after", 5) and now - self.last_approach > 3:
            self.last_approach = now
            self.act.down(bh["approach_key"])
            self.sleep(bh.get("approach_seconds", 0.6))
            self.act.up(bh["approach_key"])
            self.log("Sin daño al objetivo: me acerco")
            acts.append("approach")
        if now - self.last_progress > self.cfg["behavior"]["stuck_seconds"]:
            self.log("Objetivo atascado/inalcanzable: lo descarto")
            self.act.press(self.cfg["keys"]["esc"])
            self.in_combat = False
            self.last_progress = now
            return ["drop_target"]
        self._finish_due_obs(s, now)
        if now >= self.next_skill_time:
            mode = self.cfg.get("auto_skills", {}).get("mode", "manual")
            sk = self._pick_skill(s, now) if mode != "auto" else None
            auto = None if sk or mode == "manual" else self._auto_skill(s, now)
            if auto:
                acts.append(auto)
            elif sk:
                self._use("skill:" + sk["name"], sk["key"], now)
                if sk.get("opener"):
                    self.opener_pending = False
                self.next_skill_time = now + sk.get("after_delay", 1.0)
                acts.append("skill:" + sk["name"])
            elif self._ready("basic", 1.5, now):
                self._use("basic", self.cfg["keys"]["basic_attack"], now)
                if not self.pending_obs:
                    self.pending_obs.append(self.book.begin_obs("_basic", s, now))
                self.next_skill_time = now + 0.5
                acts.append("basic")
        return acts

    # -- habilidades aprendidas de la barra --------------------------------
    def _excluded_keys(self):
        return excluded_keys(self.cfg)

    def _scan_hotbar(self, s, now):
        if s.slots is None or not self.cfg.get("auto_skills", {}).get("enabled", True):
            return
        self.book.excluded = self._excluded_keys()
        new = self.book.update(s.slots, now)
        if len(new) > 3:
            self.log(f"✦ {len(new)} habilidades detectadas en la barra")
        else:
            for e in new:
                self.log(f"✦ Habilidad nueva detectada en {e['key']} ({e['name']}): la probaré en combate")

    def _auto_skill(self, s, now):
        ac = self.cfg.get("auto_skills", {})
        if not ac.get("enabled", True) or s.slots is None:
            return None
        pick = self.book.choose(s, self.explored < ac.get("explore_per_fight", 2),
                                ac.get("explore_min_hp", 60))
        if not pick:
            return None
        e, why = pick
        if self.cfg.get("hotbar", {}).get("input", "click") == "click" and e.get("pos"):
            self.act.click(*e["pos"])
        else:
            self.act.press(e["key"])
        self.last_used["auto:" + e["id"]] = now
        self.next_skill_time = now + ac.get("after_delay", 1.2)
        if why == "explore":
            self.explored += 1
        self.pending_obs = [o for o in self.pending_obs if o["id"] != "_basic"]
        self.pending_obs.append(self.book.begin_obs(e["id"], s, now))
        self.log(f"Uso {e['name']} [{why}]")
        return f"auto:{e['id']}:{why}"

    def _finish_due_obs(self, s, now, force=False):
        wait = self.cfg.get("auto_skills", {}).get("observe_seconds", 2.0)
        potion = now - self.last_used.get("pot_hp", -1e9) < wait + 1
        for ob in list(self.pending_obs):
            if force or now - ob["t"] >= wait:
                self.book.finish_obs(ob, s, potion)
                self.pending_obs.remove(ob)

    def _end_fight(self, now):
        self._finish_due_obs(Status(self.last_status.hp, self.last_status.mp, 0.0), now, force=True)
        self._record_fight(now)
        self.in_combat = False
        self.kills += 1
        self.last_kill_time = now
        self.target_fails = 0
        for _ in range(self.cfg["behavior"]["loot_presses"]):
            self.act.press(self.cfg["keys"]["loot"])
        self.log(f"Enemigo derrotado (#{self.kills}, {self.kills_per_hour():.0f}/h)")
        return ["loot"]

    def _rest(self, s, now):
        b = self.cfg["behavior"]
        low = max(15, b["rest_below"] - 15 * self.power) / 100
        if not self.resting and s.hp is not None and s.hp < low:
            self.act.press(self.cfg["keys"]["sit"])
            self.resting, self.rest_start = True, now
            self.log("Descansando")
            return ["sit"]
        if self.resting:
            recovered = (s.hp is None or s.hp >= b["rest_until"] / 100) and \
                        (s.mp is None or s.mp >= 0.5)
            if recovered or now - self.rest_start > b["rest_max_seconds"]:
                self.act.press(self.cfg["keys"]["sit"])
                self.resting = False
                return ["stand"]
            return ["resting"]
        return None

    def _check_zone(self, now, level):
        ch = self.cfg["character"]
        if not ch.get("auto_zone_check", True):
            return
        if now - self.last_zone_check < self.cfg["behavior"]["zone_check_seconds"]:
            return
        self.last_zone_check = now
        if level and level != ch["level"]:
            self.log(f"¡Nivel {level}!")
            ch["level"] = level
        g = self.cfg.get("guide", {})
        step = step_for(self.guide, ch["level"] + g.get("level_bonus", 0)) if g.get("enabled") else None
        if step and step["mode"] == "manual" and g.get("manual_policy", "avisar") == "avisar":
            sid = f"{step['from']}-{step['to']}"
            if sid != self.notified_step:
                self.notified_step = sid
                self._alert(f"Guía (niv. {step['from']}-{step['to']}): {step['title']}. {step['detalle']}")
                self.request_pause = True
            return
        if step and step["mode"] == "grind":
            rec = {"name": step["zone"], "min": step["from"], "max": step["to"], "notas": step["title"]}
            if ch["zone"] in step.get("zonas_validas", []):      # p. ej. Guardavieja vale como Altgard
                rec["name"] = ch["zone"]
        else:
            rec = plan_zone(self.cfg, self.planner, ch["level"], self.power)
            cur = self.planner.by_name(ch["zone"])
            if cur and cur["min"] <= ch["level"] + self.power <= cur["max"]:
                rec = cur                                         # ya estás en una zona válida para tu nivel
        if rec["name"] != ch["zone"] and rec["name"] != self.notified_zone:
            self.notified_zone = rec["name"]
            self._alert(f"Con nivel {ch['level']} y tu equipo, la zona ideal es "
                        f"{rec['name']} ({rec['min']}-{rec['max']}). Estás en {ch['zone']}.")
            key = f"{ch['zone']}->{rec['name']}"
            if ch.get("auto_route") and key in self.routes:
                self.log(f"Ejecutando ruta {key}")
                play_route(self.routes[key], self.act, stop=self.should_stop)
                ch["zone"] = rec["name"]
                ch["spot"] = ""
            elif ch.get("pause_on_zone_change", True):
                self.request_pause = True

    def _search(self, now):
        b = self.cfg["behavior"]
        if now - self.last_target_try < b["target_retry_seconds"]:
            return []
        self.last_target_try = now
        self.act.press(self.cfg["keys"]["target"])
        self.target_fails += 1
        acts = ["target"]
        patrol = self.routes.get("patrol:" + str(self.cfg["character"].get("spot", "")))
        if self.target_fails >= b["wander_after_fails"] and patrol:
            self.log("Sin objetivos cerca: patrullo el punto de farmeo")
            play_route(patrol, self.act, stop=self.should_stop)
            self.target_fails = 0
            acts.append("patrol")
        elif self.target_fails >= b["wander_after_fails"] and b.get("wander_keys"):
            k = random.choice(b["wander_keys"])
            self.act.down(k)
            self.sleep(b["wander_seconds"])
            self.act.up(k)
            self.log("Sin objetivos cerca: me muevo un poco")
            self.target_fails = 0
            acts.append("wander")
        if now - self.last_kill_time > b["idle_alert_seconds"]:
            self.last_kill_time = now
            self._alert("Llevo un rato sin matar nada: ¿zona vacía? Revisa el personaje.")
            if b.get("pause_on_idle", True):
                self.request_pause = True
        return acts

    # -- analizador de monstruos y puntos de farmeo ------------------------
    def _monster_policy(self, now):
        """Al seleccionar objetivo: lee su nombre y descarta los poco rentables o peligrosos."""
        mc = self.cfg.get("monsters", {})
        self.pending_name = None
        if not mc.get("enabled", True):
            return None
        reader = getattr(self.perc, "read_name", None)
        name = reader() if reader else None
        self.pending_name = name
        if name and (not self.db.should_fight(name, min_samples=mc.get("min_samples", 3),
                                              keep_ratio=mc.get("keep_ratio", 0.6),
                                              max_danger=mc.get("max_danger", 80))
                     or self._level_bad(name, mc)) \
                and self.skip_streak < mc.get("max_skips", 6):
            self.skip_streak += 1
            self.act.press(self.cfg["keys"]["esc"])
            self.last_target_try = now
            self.log(f"Descarto {name}: poca experiencia o demasiado peligroso")
            return "skip:" + name
        self.skip_streak = 0
        return None

    def _level_bad(self, name, mc):
        """Con los datos del juego: descarta monstruos muy por debajo (casi sin XP) o muy por encima (peligrosos) de tu nivel."""
        if not mc.get("use_levels", True) or self.db.monsters.get(name, {}).get("pref") == "farm":
            return False
        lv = self.gamedata.level_of(name)
        if lv is None:
            return False
        diff = lv - self.cfg["character"]["level"]
        return diff <= -mc.get("grey_below", 5) or diff >= mc.get("danger_above", 6)

    def _record_fight(self, now):
        f, self.fight = self.fight, None
        if not f:
            return
        st = self.last_status
        gain = xp_gain(f["xp0"], st.xp)
        xp_pts = None if gain is None else gain * 100
        hp_lost = 0.0 if f["hp0"] is None else max(0.0, (f["hp0"] - f["minhp"]) * 100)
        self.db.record_kill(f["name"], xp_pts, now - f["t0"], hp_lost, f["potions"])
        self.db.add_spot_kill(self.cfg["character"].get("spot", ""), xp_pts)
        if st.xp is not None:
            self.xp_idle = st.xp
        if xp_pts is not None:
            self.log(f"+{xp_pts:.2f}% XP" + (f" ({f['name']})" if f["name"] else ""))

    def _check_spot(self, now):
        mc = self.cfg.get("monsters", {})
        ch = self.cfg["character"]
        if not mc.get("auto_spot", True) or self.in_combat or \
                now - self.last_spot_check < mc.get("spot_check_seconds", 30):
            return
        self.last_spot_check = now
        cands = [sp["name"] for sp in self.cfg.get("spots", []) if sp.get("zone") == ch["zone"]]
        if not cands:
            return
        cur = ch.get("spot", "")
        target = self.db.best_spot(cands, cur if cur in cands else "",
                                   mc.get("explore_minutes", 5), mc.get("switch_ratio", 0.7))
        if target == cur:
            return
        key = f"{cur or ch['zone']}->{target}"
        if key in self.routes:
            self.log(f"Voy al punto de farmeo {target} ({key})")
            play_route(self.routes[key], self.act, stop=self.should_stop)
        elif cur and key not in self.warned_routes:
            self.warned_routes.add(key)
            self._alert(f"Quiero ir a {target} pero falta la ruta {key}: grábala en 'Zonas y rutas'.")
            return
        ch["spot"] = target
        self.db.dirty = True

    # -- bucle ------------------------------------------------------------
    def tick(self):
        now = self.clock()
        s = self.perc.read()
        self.last_status = s
        b = self.cfg["behavior"]

        gw = b.get("game_window", "")
        focused = getattr(self.perc, "game_focused", None)
        self.focus_state = focused(gw) if (gw and focused) else None
        if gw and focused and self.focus_state is False:      # las teclas irían a otra aplicación
            if now - self.last_focus_warn > 10:
                self.last_focus_warn = now
                self._alert(f"La ventana '{gw}' no está en primer plano: espero sin pulsar nada.")
            return ["no_focus"]

        if s.hp is not None and s.hp <= 0.01:
            self.dead_ticks += 1
            if self.dead_ticks >= b["dead_ticks"]:
                self._alert("Vida a 0: posible muerte. Bot en pausa.")
                self.request_pause = True
                self.dead_ticks = 0
                return ["dead"]
        else:
            self.dead_ticks = 0

        dt = min(2.0, now - self.last_tick) if self.last_tick else 0.0
        self.last_tick = now
        self.db.add_spot_time(self.cfg["character"].get("spot", ""), dt)
        if not self.in_combat and s.xp is not None:
            self.xp_idle = s.xp

        acts = self._potions(s, now)
        self._scan_hotbar(s, now)
        self._check_zone(now, s.level)
        self._check_spot(now)

        has_target = (s.thp is not None and s.thp > 0.02) or \
                     (s.thp is None and now < self.blind_until)

        if self.in_combat and not has_target:
            self.lost_ticks += 1
            if self.lost_ticks >= 2:
                self.lost_ticks = 0
                return acts + self._end_fight(now)
            return acts
        self.lost_ticks = 0

        if has_target and not self.in_combat:
            skip = self._monster_policy(now)
            if skip:
                return acts + [skip]
        if has_target:
            return acts + self._fight(s, now)

        r = self._rest(s, now)
        if r is not None:
            return acts + r
        acts += self._search(now)
        if s.thp is None and "target" in acts:   # sin barra de objetivo: modo ciego
            self.blind_until = now + b["blind_fight_seconds"]
        return acts


def preflight(perc, cfg):
    """Comprobación de conexión con la pantalla del juego. Devuelve (ok, [(nivel, texto)])."""
    s = perc.read()
    pct = lambda v: "sin calibrar" if v is None else f"{v:.0%}"
    L = [("ok" if s.hp else "bad", f"Vida: {pct(s.hp)}"), ("ok" if s.mp else "warn", f"Maná: {pct(s.mp)}"),
         ("ok" if s.thp is not None else "warn", f"Objetivo: {pct(s.thp)}"),
         ("ok" if s.slots else "warn", "Barra de habilidades: " + ("sin marcar" if s.slots is None else
                                                                 f"{sum(1 for x in s.slots if x.occupied)} huecos con habilidad"))]
    gw = cfg["behavior"].get("game_window", "")
    f = getattr(perc, "game_focused", None)
    if gw and f:
        st = f(gw)
        L.append(("ok" if st else "bad" if st is False else "warn",
                  f"Ventana «{gw}»: " + ("activa" if st else "NO está en primer plano" if st is False else "no se puede comprobar")))
    ok = bool(s.hp) and not (gw and f and f(gw) is False)
    return ok, L


# --------------------------------------------------------------------------
# Rutas grabadas (para cambiar de zona automáticamente)
# --------------------------------------------------------------------------
def play_route(steps, act, stop=lambda: False):
    """steps: [{'key':'w','down':0.0,'up':3.2}, ...] (tiempos en segundos)."""
    events = []
    for st in steps:
        events.append((st["down"], "down", st["key"]))
        events.append((st["up"], "up", st["key"]))
    events.sort(key=lambda e: e[0])
    t0, held = time.time(), set()
    try:
        for t, kind, key in events:
            while time.time() - t0 < t:
                if stop():
                    return
                time.sleep(0.01)
            (act.down if kind == "down" else act.up)(key)
            held.add(key) if kind == "down" else held.discard(key)
    finally:
        for k in held:
            act.up(k)


def record_route(stop_key="f9", max_seconds=300):
    """Graba pulsaciones hasta pulsar stop_key. Devuelve la lista de pasos."""
    from pynput import keyboard
    t0, downs, steps, done = time.time(), {}, [], threading.Event()

    def name(k):
        return getattr(k, "char", None) or getattr(k, "name", str(k))

    def on_press(k):
        n = name(k)
        if n == stop_key:
            done.set()
            return False
        downs.setdefault(n, time.time() - t0)

    def on_release(k):
        n = name(k)
        if n in downs:
            steps.append({"key": n, "down": round(downs.pop(n), 3),
                          "up": round(time.time() - t0, 3)})

    with keyboard.Listener(on_press=on_press, on_release=on_release):
        done.wait(max_seconds)
    return steps


# --------------------------------------------------------------------------
# Ejecución en segundo plano con pausa/parada
# --------------------------------------------------------------------------
class BotRunner:
    def __init__(self, cfg, knowledge, log=print, on_status=lambda b: None, alert=None, book=None, db=None):
        self.cfg, self.kn, self.log = cfg, knowledge, log
        self.book, self.db = book, db
        self.on_status, self.alert = on_status, alert
        self.paused = False
        self.stopped = threading.Event()
        self.thread = None

    def start(self):
        self.stopped.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stopped.set()

    def toggle_pause(self):
        self.paused = not self.paused
        self.log("PAUSA" if self.paused else "REANUDADO")

    def _loop(self):
        try:
            brain = Brain(self.cfg, self.kn, ScreenPerception(self.cfg),
                          Actuator(self.cfg["behavior"].get("input_mode", "pyautogui")),
                          log=self.log, alert=self.alert, book=self.book, db=self.db,
                          routes=load_json(ROUTES_PATH, {}))
            brain.should_stop = self.stopped.is_set
            last_save = time.time()
            self.log("Empezando en 5 s: pon la ventana de Aion en primer plano.")
            for _ in range(50):
                if self.stopped.is_set():
                    return
                time.sleep(0.1)
            ok, lines = preflight(brain.perc, self.cfg)
            for lvl, txt in lines:
                self.log(("✔ " if lvl == "ok" else "⚠ " if lvl == "warn" else "✖ ") + "Conexión · " + txt)
            if not ok:
                if self.alert:
                    self.alert("El bot NO está conectado a la pantalla del juego (no veo la barra de vida o Aion no está en "
                               "primer plano). Revisa la pestaña 👁 Vista o usa ✨ Configurar automáticamente. No arranco.")
                return
            limit = self.cfg["behavior"]["max_runtime_minutes"] * 60
            while not self.stopped.is_set():
                if time.time() - brain.started > limit:
                    self.log("Tiempo máximo alcanzado.")
                    break
                if brain.request_pause:
                    brain.request_pause, self.paused = False, True
                    self.log("PAUSA automática (mira el aviso)")
                if not self.paused:
                    brain.tick()
                self.on_status(brain)
                if time.time() - last_save > 20:
                    if brain.book.dirty:
                        brain.book.save(LEARNED_PATH)
                    if brain.db.dirty:
                        brain.db.save(MONSTERS_PATH)
                    last_save = time.time()
                time.sleep(0.25)
        except Exception as e:  # noqa: BLE001
            self.log(f"ERROR: {e}")
        finally:
            try:
                if self.book is not None:
                    self.book.save(LEARNED_PATH)
                if self.db is not None:
                    self.db.save(MONSTERS_PATH)
            except OSError:
                pass
            self.log("Bot detenido.")
            self.stopped.set()
