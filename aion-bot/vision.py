"""Vista del bot: dibuja sobre una captura de pantalla lo que el bot detecta."""
import sys

from PIL import ImageDraw

from engine import bar_fraction
from minimap import find_dots
from skillbook import analyze_hotbar, READY_RATIO

OK, BAD, WARN = "#5be0a8", "#ff4d6d", "#ffd166"
BAR_NAMES = {"hp": "Vida", "mp": "Maná", "target": "Objetivo", "xp": "Experiencia"}
ROLE_CHAR = {"damage": "D", "heal": "C", "buff": "B", "utility": "U", "unknown": "?", "ignore": "x"}
ROLE_COLOR = {"damage": "#ff8c42", "heal": "#5be0a8", "buff": "#5aa9ff", "utility": "#8a7bb0",
              "unknown": "#ffd166", "ignore": "#444444"}


def foreground_title():
    """Título de la ventana activa (solo Windows). None si no se puede saber."""
    if not sys.platform.startswith("win"):
        return None
    try:
        import ctypes
        u = ctypes.windll.user32
        h = u.GetForegroundWindow()
        n = u.GetWindowTextLengthW(h)
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(h, buf, n + 1)
        return buf.value
    except Exception:
        return None


def ocr_crop(img, reg, whitelist=None):
    try:
        import pytesseract
        x1, y1, x2, y2 = reg
        g = img.crop((x1, y1, x2, y2)).convert("L").point(lambda v: 255 if v > 140 else 0)
        g = g.resize(((x2 - x1) * 3, (y2 - y1) * 3))
        cfg = "--psm 7" + (f" -c tessedit_char_whitelist={whitelist}" if whitelist else "")
        return pytesseract.image_to_string(g, config=cfg).strip()
    except Exception:
        return None


def render_overlay(img, cfg, book=None):
    """Devuelve (imagen con anotaciones, [(nivel, texto)]) con nivel 'ok' | 'warn' | 'bad'."""
    img = img.convert("RGB").copy()
    d = ImageDraw.Draw(img)
    rep = [("ok", f"Captura de {img.width}x{img.height} píxeles")]

    def box(reg, color, label):
        d.rectangle(reg, outline=color, width=3)
        d.text((reg[0] + 2, max(0, reg[1] - 14)), label, fill=color)

    for k, name in BAR_NAMES.items():
        b = (cfg.get("bars") or {}).get(k) or {}
        if not b.get("region") or not b.get("color"):
            rep.append(("warn", f"{name}: sin marcar (pestaña Calibración)"))
            continue
        x1, y1, x2, y2 = b["region"]
        ymid = min(img.height - 1, (y1 + y2) // 2)
        row = [img.getpixel((x, ymid)) for x in range(max(0, x1), min(x2, img.width))]
        frac = bar_fraction(row, b["color"], b.get("tol", 60)) if row else 0.0
        if frac > 0:
            box(b["region"], OK, f"{name} {frac:.0%}")
            rep.append(("ok", f"{name}: la veo al {frac:.0%}"))
        else:
            box(b["region"], BAD, f"{name}: ¿?")
            msg = "no veo la barra. " + ("Es normal si no tienes objetivo." if k == "target" else
                                        "Revisa que la región y el color estén bien marcados.")
            rep.append(("warn" if k == "target" else "bad", f"{name}: {msg}"))

    for key, label, wl in (("target_name_region", "Nombre del objetivo", None), ("level_region", "Nivel", "0123456789")):
        reg = (cfg.get("bars") or {}).get(key)
        if not reg:
            rep.append(("warn", f"{label}: sin marcar (opcional, necesita Tesseract OCR)"))
            continue
        box(reg, WARN, label)
        txt = ocr_crop(img, reg, wl)
        rep.append(("ok" if txt else "warn", f"{label}: " + (f"leo «{txt}»" if txt else "no puedo leerlo (¿Tesseract instalado? ¿región bien marcada?)")))

    mm = (cfg.get("bars") or {}).get("minimap_region")
    if mm:
        box(mm, OK, "Minimapa")
        dots = find_dots(img, mm)
        cx, cy = (mm[0] + mm[2]) / 2, (mm[1] + mm[3]) / 2
        for dx, dy in dots:
            d.ellipse([cx + dx - 4, cy + dy - 4, cx + dx + 4, cy + dy + 4], outline=BAD, width=2)
        rep.append(("ok", f"Minimapa: veo {len(dots)} puntos rojos (monstruos cerca)"))
    else:
        rep.append(("warn", "Minimapa: sin marcar (opcional; permite saber si hay monstruos cerca y caminar si no los hay)"))

    hb = cfg.get("hotbar") or {}
    if hb.get("region"):
        x1, y1, x2, y2 = hb["region"]
        cols, rows = int(hb["cols"]), int(hb["rows"])
        cw, ch = (x2 - x1) / cols, (y2 - y1) / rows
        slots = analyze_hotbar(img.crop((x1, y1, x2, y2)), hb)
        skip = set(hb.get("ignore_rows") or [])
        n_occ = n_known = 0
        for s in slots:
            r, c = divmod(s.idx, cols)
            cell = (x1 + c * cw + 2, y1 + r * ch + 2, x1 + (c + 1) * cw - 2, y1 + (r + 1) * ch - 2)
            if r in skip:
                d.rectangle(cell, outline="#444444", width=1)
                d.text((cell[0] + 3, cell[1] + 2), "x", fill="#888888")
                continue
            if not s.occupied:
                d.rectangle(cell, outline="#333333", width=1)
                continue
            n_occ += 1
            e = book._match(s.sig) if book else None
            if e:
                n_known += 1
                role = book.role(e)
                col = ROLE_COLOR.get(role, WARN)
                cd = s.bright < READY_RATIO * e.get("ref_bright", s.bright)
                d.rectangle(cell, outline=col, width=2)
                d.text((cell[0] + 3, cell[1] + 2), ROLE_CHAR.get(role, "?") + ("*" if cd else ""), fill=col)
            else:
                d.rectangle(cell, outline=WARN, width=2)
                d.text((cell[0] + 3, cell[1] + 2), "?", fill=WARN)
        rep.append(("ok" if n_occ else "bad",
                    f"Barra de habilidades: {n_occ} huecos con habilidad ({n_known} ya conocidas)"
                    + (f"; filas ignoradas: {sorted(i + 1 for i in skip)}" if skip else "")))
        if not n_occ:
            rep.append(("bad", "No detecto habilidades: revisa la región marcada, las columnas y las filas."))
        rep.append(("ok", "Leyenda: D daño · C cura · B buff · U utilidad · ? por probar · x ignorada · * enfriando"))
    else:
        rep.append(("warn", "Barra de habilidades: sin marcar (pestaña Auto-habilidades)"))
    return img, rep
