"""Analizador de monstruos y puntos de farmeo.

Mide, por observación, cuánta experiencia da cada monstruo (barra de XP antes y
después de matarlo), cuánto tarda en morir y cuánta vida te cuesta, y con eso
calcula su rentabilidad (XP por minuto). Hace lo mismo con cada punto de farmeo.
"""
import json
import re
from pathlib import Path

ALPHA = 0.3  # peso de la última muestra (la media se adapta al subir de nivel)


def xp_gain(prev, cur):
    """Ganancia de experiencia como fracción de la barra. Una caída grande = subida de nivel."""
    if prev is None or cur is None:
        return None
    if cur + 0.30 < prev:
        return (1 - prev) + cur
    return max(0.0, cur - prev)


def clean_name(txt):
    """Normaliza un nombre leído por OCR. None si no parece un nombre."""
    t = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ' \-]", "", txt or "").strip()
    t = re.sub(r"\s+", " ", t)
    return t if len(t) >= 3 else None


def _ema(old, new, n):
    return new if n == 0 else old * (1 - ALPHA) + new * ALPHA


class MonsterDB:
    def __init__(self, data=None):
        data = data or {}
        self.monsters = data.get("monsters", {})
        self.spots = data.get("spots", {})
        self.dirty = False

    # -- persistencia -----------------------------------------------------
    def save(self, path):
        Path(path).write_text(json.dumps({"monsters": self.monsters, "spots": self.spots},
                                         indent=1, ensure_ascii=False), encoding="utf-8")
        self.dirty = False

    @classmethod
    def load(cls, path):
        try:
            return cls(json.loads(Path(path).read_text(encoding="utf-8")))
        except (FileNotFoundError, ValueError):
            return cls()

    def forget(self):
        self.monsters.clear()
        self.spots.clear()
        self.dirty = True

    # -- monstruos --------------------------------------------------------
    def record_kill(self, name, xp, ttk, hp_lost, potions=0):
        """xp: puntos porcentuales de la barra de nivel (None si no se pudo medir)."""
        if not name:
            return
        m = self.monsters.setdefault(name, {"n": 0, "xp": 0.0, "ttk": 0.0, "hp_lost": 0.0,
                                            "potions": 0.0, "xp_n": 0, "pref": "auto"})
        if xp is not None:
            m["xp"] = _ema(m["xp"], xp, m["xp_n"])
            m["xp_n"] += 1
        m["ttk"] = _ema(m["ttk"], ttk, m["n"])
        m["hp_lost"] = _ema(m["hp_lost"], hp_lost, m["n"])
        m["potions"] = _ema(m["potions"], potions, m["n"])
        m["n"] += 1
        self.dirty = True

    @staticmethod
    def score(m, overhead=6.0, rest_per_hp=0.3, potion_cost=15.0):
        """XP (puntos %) por minuto, descontando el tiempo de buscar, lootear y recuperarse."""
        secs = m["ttk"] + overhead + rest_per_hp * m["hp_lost"] + potion_cost * m["potions"]
        return m["xp"] / secs * 60 if secs > 0 else 0.0

    def status(self, name, min_samples=3, keep_ratio=0.6, max_danger=80):
        """'learn' | 'farm' | 'avoid' para un monstruo."""
        m = self.monsters.get(name)
        if m is None:
            return "learn"
        if m["pref"] in ("farm", "avoid"):
            return m["pref"]
        if m["n"] < min_samples:
            return "learn"
        if m["hp_lost"] > max_danger:
            return "avoid"
        known = [x for x in self.monsters.values() if x["n"] >= min_samples
                 and x["pref"] != "avoid" and x["hp_lost"] <= max_danger]
        best = max((self.score(x) for x in known), default=0.0)
        return "farm" if self.score(m) >= keep_ratio * best else "avoid"

    def should_fight(self, name, **kw):
        return not name or self.status(name, **kw) != "avoid"

    # -- puntos de farmeo ---------------------------------------------------
    def add_spot_time(self, spot, seconds):
        if spot:
            s = self.spots.setdefault(spot, {"xp": 0.0, "seconds": 0.0, "kills": 0})
            s["seconds"] += seconds
            self.dirty = True

    def add_spot_kill(self, spot, xp):
        if spot:
            s = self.spots.setdefault(spot, {"xp": 0.0, "seconds": 0.0, "kills": 0})
            s["kills"] += 1
            s["xp"] += xp or 0.0
            self.dirty = True

    def spot_rate(self, spot):
        s = self.spots.get(spot)
        return s["xp"] / (s["seconds"] / 60) if s and s["seconds"] >= 60 else None

    def best_spot(self, candidates, current, min_minutes=5, switch_ratio=0.7):
        """Decide a qué punto ir. Devuelve el nombre (puede ser el actual)."""
        if not candidates:
            return current
        mins = lambda n: self.spots.get(n, {}).get("seconds", 0) / 60
        # 1) explorar cada punto con pocos datos, uno tras otro (min_minutes en cada uno)
        unexplored = [c for c in candidates if mins(c) < min_minutes]
        if unexplored:
            if current in unexplored:
                return current
            return unexplored[0]
        # 2) todos medidos: el de mayor XP/min, con histéresis para no cambiar por ruido
        rates = {c: self.spot_rate(c) or 0.0 for c in candidates}
        best = max(rates, key=rates.get)
        if current in rates and rates[current] >= switch_ratio * rates[best]:
            return current
        return best


def plan_zone(cfg, planner, level, bonus):
    """Zona designada: el plan propio del usuario si existe; si no, la tabla de conocimiento."""
    plan = [p for p in cfg.get("farm_plan", []) if p.get("zone")]
    if plan:
        eff = level + bonus
        ok = [p for p in sorted(plan, key=lambda p: p["from_level"]) if p["from_level"] <= eff]
        z = ok[-1] if ok else sorted(plan, key=lambda p: p["from_level"])[0]
        known = planner.by_name(z["zone"]) or {"min": z["from_level"], "max": 99, "notas": "Plan propio"}
        return {**known, "name": z["zone"]}
    return planner.recommend(level, bonus)
