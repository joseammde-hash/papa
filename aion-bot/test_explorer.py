import unittest
from PIL import Image, ImageDraw
from explorer import Explorer
from minimap import find_dots
from engine import Brain, Status, load_json, CONFIG_PATH, KNOWLEDGE_PATH
from skillbook import SkillBook
from monsters import MonsterDB
from test_engine import FakeAct, Clock


def solid(v):
    return Image.new("RGB", (200, 120), (v, v, v))


def make(grab=None, dots=None, rnd=lambda: 0.0):
    cfg = load_json(CONFIG_PATH)
    act = FakeAct()
    return Explorer(cfg, act, grab, dots, sleep=lambda s: None, log=lambda m: None, rnd=rnd), act


class T(unittest.TestCase):
    def test_sweeps_a_full_circle_then_walks(self):
        ex, act = make(grab=lambda: solid(10))
        out = [ex.step() for _ in range(9)]
        self.assertEqual(out[:8], ["turn"] * 8)
        self.assertIn(out[8], ("walk", "stuck"))
        self.assertEqual(act.keys[:2], ["down:d", "up:d"])
        self.assertIn("down:w", act.keys)

    def test_detects_stuck_and_turns_away(self):
        ex, act = make(grab=lambda: solid(10), dots=lambda: 0)         # imagen idéntica = no avanza
        self.assertEqual(ex.step(), "stuck")
        self.assertEqual(ex.stuck_count, 1)
        self.assertEqual(act.keys[-2:], ["down:d", "up:d"])             # giró para salir

    def test_moving_scene_is_not_stuck(self):
        frames = iter([solid(10), solid(90)])
        ex, act = make(grab=lambda: next(frames), dots=lambda: 0)
        self.assertEqual(ex.step(), "walk")

    def test_empty_minimap_skips_sweep(self):
        ex, act = make(dots=lambda: 0)
        ex.step(); ex.step()
        self.assertNotIn("down:d", act.keys)                             # no gira: camina directo
        self.assertEqual(ex.empty_walks, 2)
        ex2, act2 = make(dots=lambda: 3)                                 # con monstruos cerca: barre
        self.assertEqual(ex2.step(), "turn")

    def test_find_dots_ignores_player_marker(self):
        img = Image.new("RGB", (120, 120), (20, 40, 20))
        d = ImageDraw.Draw(img)
        d.ellipse([58, 58, 62, 62], fill=(230, 30, 30))                  # el jugador (centro): se ignora
        d.ellipse([20, 30, 25, 35], fill=(230, 30, 30))
        d.ellipse([90, 80, 95, 85], fill=(230, 30, 30))
        d.rectangle([5, 5, 7, 7], fill=(40, 40, 230))                    # punto azul: no es monstruo
        dots = find_dots(img, [0, 0, 120, 120])
        self.assertEqual(len(dots), 2)
        self.assertTrue(any(dx < -30 and dy < -20 for dx, dy in dots))   # arriba-izquierda

    def test_brain_explores_when_no_targets(self):
        cfg = load_json(CONFIG_PATH)
        ck, act = Clock(), FakeAct()
        perc = type("P", (), {"read": lambda s: Status(1, 1, 0)})()
        b = Brain(cfg, load_json(KNOWLEDGE_PATH), perc, act, clock=ck, log=lambda m: None, alert=lambda m: None,
                  sleep=lambda s: None, book=SkillBook(log=lambda m: None), db=MonsterDB())
        out = []
        for _ in range(8):
            out += b.tick(); ck.adv(1.2)
        self.assertIn("explore:turn", out)
        self.assertIn("down:d", act.keys)


if __name__ == "__main__":
    unittest.main()
