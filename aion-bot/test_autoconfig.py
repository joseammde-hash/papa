import random
import unittest
from PIL import Image, ImageDraw
import autoconfig


def fake_screen(w=1280, h=720, hp_fill=1.0):
    random.seed(3)
    img = Image.new("RGB", (w, h), (30, 40, 30))
    d = ImageDraw.Draw(img)
    for _ in range(300):                                   # "escenario" con ruido
        x, y = random.randrange(w), random.randrange(h)
        d.rectangle([x, y, x + 20, y + 12], fill=tuple(random.randrange(20, 110) for _ in range(3)))
    d.rectangle([20, 20, 220, 30], fill=(60, 10, 10))      # marco vida
    d.rectangle([20, 20, 20 + int(200 * hp_fill), 30], fill=(200, 30, 30))
    d.rectangle([20, 36, 220, 46], fill=(20, 40, 150))     # maná
    d.rectangle([500, 20, 700, 30], fill=(200, 30, 30))    # objetivo
    for c in range(10):                                    # barra de habilidades 10 × 1, paso 44 px
        x = 400 + c * 44
        d.rectangle([x, 640, x + 40, 680], fill=(25, 25, 25), outline=(160, 160, 160))
        for i in range(5):
            d.rectangle([x + 4 + (i * 7) % 28, 644 + (i * 11) % 28, x + 12 + (i * 7) % 28, 652 + (i * 11) % 28],
                        fill=((c * 40 + i * 50) % 256, (c * 70 + i * 90) % 256, (c * 20 + i * 30 + 80) % 256))
    return img


class T(unittest.TestCase):
    def test_detects_bars(self):
        res = autoconfig.detect(fake_screen())
        b = res["bars"]
        near = lambda r, e: all(abs(a - b_) <= 3 for a, b_ in zip(r, e))
        self.assertTrue(near(b["hp"]["region"], [20, 20, 221, 31]), b["hp"])
        self.assertTrue(near(b["mp"]["region"], [20, 36, 221, 47]), b["mp"])
        self.assertTrue(near(b["target"]["region"], [500, 20, 701, 31]), b["target"])

    def test_detects_hotbar(self):
        hb = autoconfig.detect(fake_screen())["hotbar"]
        self.assertIsNotNone(hb)
        self.assertEqual(hb["cols"], 10)
        self.assertEqual(hb["rows"], 1)
        x1, y1, x2, y2 = hb["region"]
        self.assertLessEqual(abs(x1 - 400), 8)
        self.assertLessEqual(abs(y1 - 640), 8)
        self.assertLessEqual(abs(x2 - 840), 12)

    def test_no_game_gives_clear_errors(self):
        res = autoconfig.detect(Image.new("RGB", (800, 600), (0, 0, 0)))
        self.assertEqual(res["bars"], {})
        self.assertTrue(any(l == "bad" for l, _ in res["notes"]))

    def test_apply_updates_config(self):
        from engine import load_json, CONFIG_PATH
        cfg = load_json(CONFIG_PATH)
        autoconfig.apply(cfg, autoconfig.detect(fake_screen()))
        self.assertTrue(cfg["bars"]["hp"]["region"] and cfg["hotbar"]["cols"] == 10)


if __name__ == "__main__":
    unittest.main()
