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
from pathlib import Path

BASE = Path(__file__).parent
CONFIG_PATH = BASE / "config.json"
KNOWLEDGE_PATH = BASE / "knowledge.json"
ROUTES_PATH = BASE / "routes.json"
LEARNED_PATH = BASE / "skills_learned.json"


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
        return ok[-1] if ok else self.zones[0]

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

    def _level(self):
        reg = self.cfg["bars"].get("level_region")
        if not reg:
            return None
        try:
            import pytesseract
            x1, y1, x2, y2 = reg
            img = self.pg.screenshot(region=(x1, y1, x2 - x1, y2 - y1)).convert("L")
            img = img.point(lambda v: 255 if v > 150 else 0).resize(((x2 - x1) * 3, (y2 - y1) * 3))
            txt = pytesseract.image_to_string(
                img, config="--psm 7 -c tessedit_char_whitelist=0123456789").strip()
            lv = int(txt)
            return lv if 1 <= lv <= 65 else None
        except Exception:
            return None

    def _slots(self):
        hb = self.cfg.get("hotbar") or {}
        if not hb.get("region"):
            return None
        x1, y1, x2, y2 = hb["region"]
        return analyze_hotbar(self.pg.screenshot(region=(x1, y1, x2 - x1, y2 - y1)), hb)

    def read(self):
        return Status(self._bar("hp"), self._bar("mp"), self._bar("target"),
                      self._level(), self._slots())


class Actuator:
    def __init__(self):
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.02
        self.pg = pyautogui

    def press(self, key):
        if "+" in key and key != "+":      # combinaciones tipo 'shift+1'
            self.pg.hotkey(*key.split("+"))
        else:
            self.pg.press(key)

    def down(self, key):
        self.pg.keyDown(key)

    def up(self, key):
        self.pg.keyUp(key)


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
                 book=None):
        self.cfg, self.perc, self.act = cfg, perception, actuator
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
            self.log("Combate iniciado")
        if s.thp is not None:
            if s.thp < self.last_thp - 0.005:
                self.last_progress = now
            self.last_thp = s.thp
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
        rec = self.planner.recommend(ch["level"], self.power)
        if rec["name"] != ch["zone"] and rec["name"] != self.notified_zone:
            self.notified_zone = rec["name"]
            self._alert(f"Con nivel {ch['level']} y tu equipo, la zona ideal es "
                        f"{rec['name']} ({rec['min']}-{rec['max']}). Estás en {ch['zone']}.")
            key = f"{ch['zone']}->{rec['name']}"
            if ch.get("auto_route") and key in self.routes:
                self.log(f"Ejecutando ruta {key}")
                play_route(self.routes[key], self.act)
                ch["zone"] = rec["name"]
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
        if self.target_fails >= b["wander_after_fails"] and b.get("wander_keys"):
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

    # -- bucle ------------------------------------------------------------
    def tick(self):
        now = self.clock()
        s = self.perc.read()
        self.last_status = s
        b = self.cfg["behavior"]

        if s.hp is not None and s.hp <= 0.01:
            self.dead_ticks += 1
            if self.dead_ticks >= b["dead_ticks"]:
                self._alert("Vida a 0: posible muerte. Bot en pausa.")
                self.request_pause = True
                self.dead_ticks = 0
                return ["dead"]
        else:
            self.dead_ticks = 0

        acts = self._potions(s, now)
        self._scan_hotbar(s, now)
        self._check_zone(now, s.level)

        has_target = (s.thp is not None and s.thp > 0.02) or \
                     (s.thp is None and now < self.blind_until)

        if self.in_combat and not has_target:
            self.lost_ticks += 1
            if self.lost_ticks >= 2:
                self.lost_ticks = 0
                return acts + self._end_fight(now)
            return acts
        self.lost_ticks = 0

        if has_target:
            return acts + self._fight(s, now)

        r = self._rest(s, now)
        if r is not None:
            return acts + r
        acts += self._search(now)
        if s.thp is None and "target" in acts:   # sin barra de objetivo: modo ciego
            self.blind_until = now + b["blind_fight_seconds"]
        return acts


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
    def __init__(self, cfg, knowledge, log=print, on_status=lambda b: None, alert=None, book=None):
        self.cfg, self.kn, self.log = cfg, knowledge, log
        self.book = book
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
            brain = Brain(self.cfg, self.kn, ScreenPerception(self.cfg), Actuator(),
                          log=self.log, alert=self.alert, book=self.book,
                          routes=load_json(ROUTES_PATH, {}))
            last_save = time.time()
            self.log("Empezando en 5 s: pon la ventana de Aion en primer plano.")
            for _ in range(50):
                if self.stopped.is_set():
                    return
                time.sleep(0.1)
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
                if brain.book.dirty and time.time() - last_save > 20:
                    brain.book.save(LEARNED_PATH)
                    last_save = time.time()
                time.sleep(0.25)
        except Exception as e:  # noqa: BLE001
            self.log(f"ERROR: {e}")
        finally:
            try:
                if self.book is not None:
                    self.book.save(LEARNED_PATH)
            except OSError:
                pass
            self.log("Bot detenido.")
            self.stopped.set()
