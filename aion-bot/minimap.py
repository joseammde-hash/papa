"""Minimapa: cuenta los puntos de monstruo (rojos) que se ven en el minimapa del juego."""
from collections import deque

from autoconfig import color_mask


def find_dots(img, region, min_area=3, max_area=90, ignore_center=6):
    """Devuelve [(dx, dy)] de cada punto rojo respecto al centro del minimapa (el jugador)."""
    x1, y1, x2, y2 = region
    crop = img.convert("RGB").crop((x1, y1, x2, y2))
    w, h = crop.size
    data = color_mask(crop, "red").tobytes()
    seen = bytearray(w * h)
    out = []
    for start in range(w * h):
        if not data[start] or seen[start]:
            continue
        q, area, sx, sy = deque([start]), 0, 0, 0
        seen[start] = 1
        while q:
            p = q.popleft()
            y, x = divmod(p, w)
            area += 1
            sx += x
            sy += y
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < h:
                    n = ny * w + nx
                    if data[n] and not seen[n]:
                        seen[n] = 1
                        q.append(n)
        if min_area <= area <= max_area:
            dx, dy = sx / area - w / 2, sy / area - h / 2
            if (dx * dx + dy * dy) ** 0.5 > ignore_center:
                out.append((round(dx, 1), round(dy, 1)))
    return out
