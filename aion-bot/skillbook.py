"""Escaneo de la barra de acceso rápido y aprendizaje de habilidades.

El bot no conoce los nombres de tus habilidades: las reconoce por el ICONO
(huella visual), detecta cuándo están listas (el icono se oscurece en
enfriamiento) y aprende qué hace cada una OBSERVANDO el efecto tras lanzarla:
  - daño: cuánto baja la vida del objetivo comparado con el ataque básico,
  - curación: cuánto sube tu vida,
  - utilidad: no hace ninguna de las dos (no se usa sola; la puedes reasignar).
"""
import json
from dataclasses import dataclass
from pathlib import Path

HASH = 16            # huella de 16x16 = 256 bits
TOL = 30             # distancia máxima (bits) para considerar que es el mismo icono
READY_RATIO = 0.72   # brillo mínimo respecto al máximo visto para considerarla lista
MIN_CD = 2.5         # enfriamientos más cortos se confunden con el global (GCD)


@dataclass
class Slot:
    idx: int
    key: str
    occupied: bool
    sig: int
    bright: float
    x: int = 0          # centro del hueco en pantalla (para lanzar con clic)
    y: int = 0


def hamming(a, b):
    return bin(a ^ b).count("1")


def analyze_hotbar(img, hb):
    """img: imagen PIL (RGB) de la región completa de la barra → lista de Slot."""
    cols, rows = int(hb["cols"]), int(hb["rows"])
    w, h = img.size
    cw, ch = w / cols, h / rows
    mods = hb.get("row_mods") or []
    keys = hb.get("keys") or []
    click = hb.get("input", "click") == "click"
    ox, oy = (hb.get("region") or [0, 0])[:2]
    skip = set(hb.get("ignore_rows") or [])     # filas (0 = la de arriba) con pergaminos/consumibles
    slots = []
    for r in range(rows):
        mod = mods[r] if r < len(mods) else ""
        for c in range(cols):
            box = (int(c * cw + cw * .1), int(r * ch + ch * .1),
                   int((c + 1) * cw - cw * .1), int((r + 1) * ch - ch * .1))
            g = img.crop(box).convert("L")
            data = list(g.tobytes())
            n = max(1, len(data))
            mean = sum(data) / n
            std = (sum((v - mean) ** 2 for v in data) / n) ** .5
            small = list(g.resize((HASH, HASH)).tobytes())
            m = sum(small) / len(small)
            sig = 0
            for v in small:
                sig = (sig << 1) | (1 if v > m else 0)
            base = keys[c] if c < len(keys) else ""
            key = f"{mod}+{base}" if (mod and base) else base
            if click and not base:
                key = f"fila{r + 1}·{c + 1}"          # sin tecla: el hueco se identifica por su posición
            usable = bool(base) or click
            slots.append(Slot(r * cols + c, key, usable and r not in skip and std >= hb.get("occupied_std", 12),
                              sig, mean, int(ox + (c + .5) * cw), int(oy + (r + .5) * ch)))
    return slots


class SkillBook:
    def __init__(self, data=None, log=print):
        data = data or {}
        self.entries = {k: self._fix(v) for k, v in data.get("entries", {}).items()}
        self.baseline = data.get("baseline", {"n": 0, "avg_drop": 0.0})
        self.log = log
        self.excluded = set()
        self.live = {}
        self.dirty = False

    @staticmethod
    def _fix(e):
        e["sig"] = int(e["sig"])
        return e

    # -- persistencia -----------------------------------------------------
    def to_json(self):
        ents = {k: {**v, "sig": str(v["sig"])} for k, v in self.entries.items()}
        return {"entries": ents, "baseline": self.baseline}

    def save(self, path):
        Path(path).write_text(json.dumps(self.to_json(), indent=1, ensure_ascii=False), encoding="utf-8")
        self.dirty = False

    @classmethod
    def load(cls, path, log=print):
        try:
            return cls(json.loads(Path(path).read_text(encoding="utf-8")), log)
        except (FileNotFoundError, ValueError):
            return cls(None, log)

    def forget(self):
        self.entries.clear()
        self.baseline = {"n": 0, "avg_drop": 0.0}
        self.live.clear()
        self.dirty = True

    # -- escaneo ----------------------------------------------------------
    def _match(self, sig):
        best, bd = None, TOL + 1
        for e in self.entries.values():
            d = hamming(sig, e["sig"])
            if d < bd:
                best, bd = e, d
        return best

    def update(self, slots, now):
        """Registra habilidades nuevas, su tecla actual y si están listas.
        Devuelve la lista de entradas nuevas."""
        new, present = [], set()
        for sl in slots:
            if not sl.occupied or sl.key in self.excluded:
                continue
            e = self._match(sl.sig)
            if e is None:
                eid = f"s{len(self.entries) + 1}_{sl.sig & 0xffff:04x}"
                e = {"id": eid, "sig": sl.sig, "name": f"Habilidad {sl.key}", "key": sl.key,
                     "role": "unknown", "role_user": "auto", "n": 0, "avg_drop": 0.0,
                     "avg_heal": 0.0, "cooldown": 0.0, "ref_bright": sl.bright, "pos": [sl.x, sl.y]}
                self.entries[eid] = e
                new.append(e)
                self.dirty = True
            if e["key"] != sl.key:
                e["key"] = sl.key
                self.dirty = True
            if sl.x:
                e["pos"] = [sl.x, sl.y]
            e["ref_bright"] = max(e.get("ref_bright", 0), sl.bright)
            ready = sl.bright >= READY_RATIO * e["ref_bright"]
            prev = self.live.get(e["id"])
            cd_start = prev.get("cd_start") if prev else None
            if prev and prev["ready"] and not ready:
                cd_start = now
            if prev and not prev["ready"] and ready and cd_start is not None:
                dur = now - cd_start
                if MIN_CD <= dur <= 600 and (not e["cooldown"] or dur < e["cooldown"]):
                    e["cooldown"] = round(dur, 1)
                    self.dirty = True
                cd_start = None
            self.live[e["id"]] = {"ready": ready, "cd_start": cd_start}
            present.add(e["id"])
        for k in list(self.live):
            if k not in present:
                del self.live[k]
        return new

    # -- roles ------------------------------------------------------------
    @staticmethod
    def role(e):
        u = e.get("role_user", "auto")
        return e.get("role", "unknown") if u in (None, "auto") else u

    def _classify(self, e):
        if e["n"] < 2:
            return
        base = self.baseline.get("avg_drop", 0.0)
        if e["avg_drop"] > base * 1.25 + 1.0:
            e["role"] = "damage"
        elif e["avg_heal"] >= 4:
            e["role"] = "heal"
        else:
            e["role"] = "utility"
        self.dirty = True

    # -- observación ------------------------------------------------------
    def begin_obs(self, eid, s, now):
        return {"id": eid, "t": now, "thp": s.thp, "hp": s.hp}

    def finish_obs(self, ob, s, potion_used=False):
        if ob["thp"] is None or s.thp is None:
            return
        drop = (ob["thp"] if s.thp <= 0.02 else max(0.0, ob["thp"] - s.thp)) * 100
        heal = 0.0 if (potion_used or ob["hp"] is None or s.hp is None) else max(0.0, (s.hp - ob["hp"]) * 100)
        tgt = self.baseline if ob["id"] == "_basic" else self.entries.get(ob["id"])
        if tgt is None:
            return
        n = tgt["n"] if "n" in tgt else 0
        tgt["avg_drop"] = (tgt["avg_drop"] * n + drop) / (n + 1)
        if ob["id"] != "_basic":
            tgt["avg_heal"] = (tgt["avg_heal"] * n + heal) / (n + 1)
        tgt["n"] = n + 1
        if ob["id"] != "_basic":
            self._classify(tgt)
        self.dirty = True

    # -- decisión ---------------------------------------------------------
    def choose(self, s, can_explore=True, explore_min_hp=60):
        """Devuelve (entrada, motivo) o None."""
        cands = [e for e in self.entries.values()
                 if self.live.get(e["id"], {}).get("ready") and e["key"] not in self.excluded
                 and self.role(e) != "ignore"]
        heals = [e for e in cands if self.role(e) == "heal"]
        if s.hp is not None and s.hp < 0.5 and heals:
            return max(heals, key=lambda e: e["avg_heal"]), "heal"
        buffs = [e for e in cands if self.role(e) == "buff"]
        if buffs:
            return buffs[0], "buff"
        if can_explore and s.thp is not None and s.thp > 0.3 and \
                (s.hp is None or s.hp * 100 >= explore_min_hp):
            unk = [e for e in cands if self.role(e) == "unknown"]
            if unk:
                return unk[0], "explore"
        dmg = [e for e in cands if self.role(e) == "damage"]
        if dmg:
            return max(dmg, key=lambda e: e["avg_drop"]), "damage"
        return None
