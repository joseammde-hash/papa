"""Guía de leveling: qué hacer en cada tramo de nivel.

Cada tramo es 'grind' (el bot puede hacerlo solo: farmear una zona) o 'manual'
(misiones, instancias… que el bot no sabe hacer: te avisa y se pausa)."""
from pathlib import Path
import json

GUIDE_PATH = Path(__file__).parent / "guide.json"


def load_guide(path=GUIDE_PATH):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def step_for(guide, level):
    if not guide:
        return None
    for s in guide.get("steps", []):
        if s["from"] <= level <= s["to"]:
            return s
    return None
