import unittest
from engine import Brain, Status, ZonePlanner, bar_fraction, load_json, CONFIG_PATH, KNOWLEDGE_PATH

KN = load_json(KNOWLEDGE_PATH)


class FakePerc:
    def __init__(self, seq): self.seq = list(seq); self.cur = Status(1, 1, 0)
    def read(self):
        if self.seq: self.cur = self.seq.pop(0)
        return self.cur


class FakeAct:
    def __init__(self): self.keys = []
    def press(self, k): self.keys.append(k)
    def down(self, k): self.keys.append("down:" + k)
    def click(self, x, y): self.keys.append(f"click:{x},{y}")
    def up(self, k): self.keys.append("up:" + k)


class Clock:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t
    def adv(self, s): self.t += s


def make(seq, power=0):
    cfg = load_json(CONFIG_PATH); cfg["character"]["gear_power"] = power
    ck, act = Clock(), FakeAct()
    return Brain(cfg, KN, FakePerc(seq), act, clock=ck, log=lambda m: None,
                 alert=lambda m: None, sleep=lambda s: None), act, ck


class T(unittest.TestCase):
    def test_bar_fraction(self):
        px = [(200, 30, 30)] * 60 + [(20, 20, 20)] * 40
        self.assertAlmostEqual(bar_fraction(px, (200, 30, 30)), 0.6)
        self.assertEqual(bar_fraction([(0, 0, 0)] * 10, (200, 30, 30)), 0.0)

    def test_zones(self):
        p = ZonePlanner(KN["zones"])
        self.assertEqual(p.recommend(9, 0)["name"], "Ishalgen")
        self.assertEqual(p.recommend(13, 0)["name"], "Altgard")
        self.assertEqual(p.recommend(9, 2)["name"], "Altgard")    # equipo fuerte adelanta
        self.assertEqual(p.recommend(28, 2)["name"], "Beluslan")
        self.assertEqual([p.recommend(l, 0)["name"] for l in (9, 10, 20, 30, 45, 51, 56, 65)],
                         ["Ishalgen", "Altgard", "Morheim", "Beluslan", "Brusthonin", "Gelkmaros", "Enshar", "Enshar"])

    def test_potion_threshold_depends_on_gear(self):
        b, act, _ = make([Status(0.30, 1, 0)], power=0)
        b.tick(); self.assertIn("7", act.keys)
        b, act, _ = make([Status(0.30, 1, 0)], power=2)           # umbral 25 %
        b.tick(); self.assertNotIn("7", act.keys)
        b, act, _ = make([Status(0.20, 1, 0)], power=2)
        b.tick(); self.assertIn("7", act.keys)

    def test_kill_cycle(self):
        b, act, ck = make([Status(1, 1, 0), Status(1, 1, 1.0), Status(1, 1, 0.8),
                           Status(1, 1, 0.5), Status(1, 1, 0.2), Status(1, 1, 0), Status(1, 1, 0)])
        out = []
        for _ in range(7):
            out += b.tick(); ck.adv(1.6)
        self.assertEqual(act.keys[0], "tab")
        self.assertIn("skill:Apertura a distancia", out)       # abre con la apertura
        self.assertEqual(out.count("skill:Apertura a distancia"), 1)
        self.assertIn("skill:Remate", out)                    # remata con poca vida
        self.assertEqual(b.kills, 1)
        self.assertIn("f", act.keys)                          # looteo

    def test_emergency_skill_first(self):
        b, act, _ = make([Status(0.25, 1, 0.9)], power=2)
        out = b.tick()
        self.assertEqual(out, ["skill:Defensiva / escape"])

    def test_zone_alert_and_pause(self):
        cfg = load_json(CONFIG_PATH); cfg["character"].update(level=19, gear_power=2)
        ck, alerts = Clock(), []
        b = Brain(cfg, KN, FakePerc([Status(1, 1, 0)]), FakeAct(), clock=ck,
                  log=lambda m: None, alert=alerts.append, sleep=lambda s: None)
        b.tick()
        self.assertTrue(alerts and "Morheim" in alerts[0])
        self.assertTrue(b.request_pause)

    def test_death_pauses(self):
        b, _, ck = make([Status(0, 0, 0)] * 12)
        for _ in range(12): b.tick(); ck.adv(0.25)
        self.assertTrue(b.request_pause)


if __name__ == "__main__":
    unittest.main()
