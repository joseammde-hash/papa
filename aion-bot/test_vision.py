import unittest
from PIL import Image, ImageDraw
from vision import render_overlay
from skillbook import SkillBook, analyze_hotbar
from engine import Brain, Status, load_json, CONFIG_PATH, KNOWLEDGE_PATH
from monsters import MonsterDB
from test_engine import FakePerc, FakeAct, Clock
from test_skillbook import bar, HB

KN = load_json(KNOWLEDGE_PATH)


def cfg_with_bars():
    cfg = load_json(CONFIG_PATH)
    cfg["bars"]["hp"] = {"region": [20, 20, 220, 30], "color": [200, 30, 30], "tol": 40}
    cfg["bars"]["target"] = {"region": [20, 60, 220, 70], "color": [200, 30, 30], "tol": 40}
    return cfg


class T(unittest.TestCase):
    def test_reads_bar_and_reports_missing(self):
        img = Image.new("RGB", (400, 200), (10, 10, 10))
        ImageDraw.Draw(img).rectangle([20, 20, 140, 30], fill=(200, 30, 30))      # 60 % de 200 px
        out, rep = render_overlay(img, cfg_with_bars())
        txt = " | ".join(t for _, t in rep)
        self.assertIn("Vida: la veo al 60%", txt)
        self.assertIn("Objetivo: no veo la barra", txt)            # sin objetivo: aviso, no error
        self.assertIn("Maná: sin marcar", txt)
        self.assertEqual(out.size, img.size)
        self.assertNotEqual(out.tobytes(), img.tobytes())          # dibujó encima

    def test_hotbar_legend_and_known_skills(self):
        cfg = cfg_with_bars()
        cfg["hotbar"].update(region=[0, 100, 400, 140], cols=10, rows=1, ignore_rows=[], input="click")
        screen = Image.new("RGB", (400, 200), (40, 40, 40))
        screen.paste(bar([5, 9, 18]), (0, 100))
        book = SkillBook(log=lambda m: None)
        sl = analyze_hotbar(screen.crop((0, 100, 400, 140)), dict(HB, input="click"))
        book.update(sl, 0)
        _, rep = render_overlay(screen, cfg, book)
        self.assertTrue(any("3 huecos con habilidad (3 ya conocidas)" in t for _, t in rep))

    def test_no_focus_blocks_actions(self):
        cfg = load_json(CONFIG_PATH)
        cfg["behavior"]["game_window"] = "aion"
        perc = FakePerc([Status(1, 1, 1.0)])
        perc.game_focused = lambda title: False
        alerts, act = [], FakeAct()
        b = Brain(cfg, KN, perc, act, clock=Clock(), log=lambda m: None, alert=alerts.append,
                  sleep=lambda s: None, book=SkillBook(log=lambda m: None), db=MonsterDB())
        self.assertEqual(b.tick(), ["no_focus"])
        self.assertEqual(act.keys, [])                              # no pulsó nada
        self.assertEqual(len(alerts), 1)


if __name__ == "__main__":
    unittest.main()
