"""Autoconfiguración: detecta las barras y la barra de habilidades en una captura de pantalla.

  python autoconfig.py captura.png            # muestra lo detectado y guarda autoconfig_preview.png
  python autoconfig.py captura.png --apply    # además lo escribe en config.json

Pensado para una captura con: vida y maná llenos, un enemigo seleccionado con vida llena y la barra de habilidades visible.
"""
import re
import sys

from PIL import Image, ImageChops, ImageFilter


# -- barras de color ----------------------------------------------------------
def _band(ch, lo, hi):
    return ch.point(lambda v: 255 if lo <= v <= hi else 0)


def color_mask(img, kind):
    r, g, b = img.convert("RGB").split()
    and_ = ImageChops.multiply
    if kind == "red":
        return and_(and_(_band(r, 150, 255), _band(g, 0, 100)), _band(b, 0, 100))
    if kind == "blue":
        return and_(and_(_band(b, 150, 255), _band(r, 0, 110)), _band(g, 40, 200))
    raise ValueError(kind)


def find_runs(mask, min_w):
    w, h = mask.size
    data = mask.tobytes()
    pat = re.compile(b"\xff{%d,}" % min_w)
    out = []
    for y in range(h):
        for m in pat.finditer(data[y * w:(y + 1) * w]):
            out.append((y, m.start(), m.end()))
    return out


def group_bars(runs, min_h=4, max_h=30, tol=8):
    open_, done = [], []
    for y, x1, x2 in runs:
        for b in open_:
            if abs(b["x1"] - x1) <= tol and abs(b["x2"] - x2) <= tol and 0 < y - b["y2"] <= 2:
                b["y2"] = y
                b["x1"], b["x2"] = min(b["x1"], x1), max(b["x2"], x2)
                break
        else:
            open_.append({"x1": x1, "x2": x2, "y1": y, "y2": y})
        for b in [b for b in open_ if y - b["y2"] > 2]:
            open_.remove(b)
            done.append(b)
    done += open_
    bars = [b for b in done if min_h <= b["y2"] - b["y1"] + 1 <= max_h]
    return sorted(bars, key=lambda b: (b["y1"], b["x1"]))


def _entry(img, b):
    ymid = (b["y1"] + b["y2"]) // 2
    px = img.getpixel(((b["x1"] + b["x2"]) // 2, ymid))[:3]
    return {"region": [b["x1"], b["y1"], b["x2"], b["y2"] + 1], "color": list(px), "tol": 60}


# -- barra de habilidades -------------------------------------------------------
def _profile(img, vertical):
    w, h = img.size
    small = img.resize((1, h) if vertical else (w, 1), Image.BOX)
    return list(small.tobytes())


def _longest(flags, max_gap=10):
    best, cur_s, last = (0, 0), None, None
    for i, f in enumerate(flags):
        if f:
            if cur_s is None or i - last > max_gap:
                cur_s = i
            last = i
            if last - cur_s > best[1] - best[0]:
                best = (cur_s, last)
    return best


def _lines(rows, thr):
    """Agrupa filas contiguas con mucha densidad de bordes en 'líneas' horizontales (centro, densidad)."""
    out, cur = [], []
    for i, v in enumerate(rows):
        if v >= thr:
            if cur and i - cur[-1] > 2:
                out.append(cur); cur = []
            cur.append(i)
    if cur:
        out.append(cur)
    return [((c[0] + c[-1]) // 2, sum(rows[i] for i in c)) for c in out]


def find_hotbar(img):
    """Busca la barra de habilidades por los bordes horizontales de sus huecos y su paso regular."""
    W, H = img.size
    top = int(H * 0.5)
    gray = img.convert("L").crop((0, top, W, H))
    edges = gray.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 35 else 0)
    edges = edges.crop((3, 3, W - 3, edges.height - 3))            # FIND_EDGES marca el borde de la imagen
    rows = _profile(edges, True)
    med = sorted(rows)[len(rows) // 2]
    lines = _lines(rows, max(0.08 * 255, 4 * med))
    pairs = [(a, b, da + db) for a, da in lines for b, db in lines if 28 <= b - a <= 80]
    if not pairs:
        return None
    ya, yb, _ = max(pairs, key=lambda p: p[2])
    d, rows_n = yb - ya, 1
    centers = [c for c, _ in lines]
    while any(abs(c - (ya - d)) <= 3 for c in centers):
        ya -= d; rows_n += 1
    while any(abs(c - (yb + d)) <= 3 for c in centers):
        yb += d; rows_n += 1
    band = edges.crop((0, ya, edges.width, yb + 1))
    cols = _profile(band, False)
    cmed = sorted(cols)[len(cols) // 2]
    x1, x2 = _longest([v >= max(0.12 * 255, 2 * cmed) for v in cols], max_gap=14)
    if x2 - x1 < 80:
        return None
    m = max(cols[x1:x2 + 1])
    strong = [i for i in range(x1, x2 + 1) if cols[i] >= 0.6 * m]      # bordes verticales marcados de los huecos
    x1, x2 = strong[0], strong[-1]
    seg = cols[x1:x2 + 1]
    mean = sum(seg) / len(seg)
    best_lag, best_score = None, 0.0
    for lag in range(24, min(110, len(seg) // 2)):
        x_, y_ = seg[:-lag], seg[lag:]
        score = sum((p - mean) * (q - mean) for p, q in zip(x_, y_)) / len(x_)
        if score > best_score:
            best_lag, best_score = lag, score
    if not best_lag:
        return None
    cols_n = max(1, round((x2 - x1 + 1) / best_lag))
    return {"region": [x1 + 3, top + 3 + ya, x2 + 4, top + 3 + yb],
            "cols": cols_n, "rows": rows_n}


# -- todo junto ---------------------------------------------------------------
def detect(img):
    """Devuelve {'bars': {...}, 'hotbar': {...} | None, 'notes': [(nivel, texto)]}"""
    img = img.convert("RGB")
    W, H = img.size
    notes, bars = [], {}
    min_w = max(60, W // 25)
    red = group_bars(find_runs(color_mask(img, "red"), min_w))
    blue = group_bars(find_runs(color_mask(img, "blue"), min_w))
    if red:
        bars["hp"] = _entry(img, red[0])
        notes.append(("ok", f"Vida: barra roja en {bars['hp']['region']}"))
        others = [b for b in red[1:] if abs(b["x1"] - red[0]["x1"]) > 40 or abs(b["y1"] - red[0]["y1"]) > 40]
        if others:
            bars["target"] = _entry(img, others[0])
            notes.append(("ok", f"Objetivo: barra roja en {bars['target']['region']}"))
        else:
            notes.append(("warn", "No veo la barra del objetivo: selecciona un enemigo (con vida llena) y repite."))
    else:
        notes.append(("bad", "No encuentro la barra de vida (roja). ¿Se ve el juego en la captura?"))
    if blue:
        hp = red[0] if red else None
        near = [b for b in blue if hp is None or abs(b["x1"] - hp["x1"]) < 120 and 0 < b["y1"] - hp["y1"] < 90]
        mp = (near or blue)[0]
        bars["mp"] = _entry(img, mp)
        notes.append(("ok", f"Maná: barra azul en {bars['mp']['region']}"))
    else:
        notes.append(("warn", "No encuentro la barra de maná (azul)."))
    hb = find_hotbar(img)
    if hb:
        notes.append(("ok", f"Barra de habilidades: {hb['cols']} columnas × {hb['rows']} filas en {hb['region']}"))
    else:
        notes.append(("warn", "No pude localizar la barra de habilidades; márcala a mano en Auto-habilidades."))
    notes.append(("warn", "La barra de experiencia y el nombre del objetivo no se detectan solos: márcalos en Calibración si los quieres."))
    return {"bars": bars, "hotbar": hb, "notes": notes}


def apply(cfg, res):
    for k, v in res["bars"].items():
        cfg["bars"][k] = v
    if res["hotbar"]:
        cfg["hotbar"].update(res["hotbar"])
    return cfg


def main(argv):
    import json
    from pathlib import Path
    import vision
    if not argv:
        print(__doc__); return 1
    cfgp = Path(__file__).parent / "config.json"
    cfg = json.loads(cfgp.read_text(encoding="utf-8"))
    img = Image.open(argv[0]).convert("RGB")
    res = detect(img)
    for lvl, t in res["notes"]:
        print({"ok": "✔", "warn": "⚠", "bad": "✖"}[lvl], t)
    apply(cfg, res)
    out, _ = vision.render_overlay(img, cfg)
    out.save(Path(__file__).parent / "autoconfig_preview.png")
    if "--apply" in argv:
        cfgp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Guardado en config.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
