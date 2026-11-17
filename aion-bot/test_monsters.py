import unittest
from monsters import MonsterDB, clean_name, plan_zone, xp_gain
from skillbook import SkillBook
from engine import Brain, Status, ZonePlanner, load_json, CONFIG_PATH, KNOWLEDGE_PATH
from test_engine import FakeAct, Clock

KN = load_json(KNOWLEDGE_PATH)


class T(unittest.TestCase):
    def test_xp_gain_and_levelup(self):
        self.assertAlmostEqual(xp_gain(.40, .45), .05)
        self.assertAlmostEqual(xp_gain(.95, .10), .15)          # subida de nivel
        self.assertIsNone(xp_gain(None, .2))
        self.assertEqual(clean_name("  Kobold  Warrior 12 "), "Kobold Warrior")
        self.assertIsNone(clean_name("1|"))

    def test_monster_policy(self):
        db = MonsterDB()
        for _ in range(3):
            db.record_kill("Lobo", 0.8, 10, 10)        # buen XP
            db.record_kill("Rata", 0.1, 8, 5)          # poca XP
            db.record_kill("Ogro", 2.0, 20, 90)        # mucha XP pero peligroso
        self.assertEqual(db.status("Lobo"), "farm")
        self.assertEqual(db.status("Rata"), "avoid")
        self.assertEqual(db.status("Ogro"), "avoid")
        self.assertEqual(db.status("Nuevo"), "learn")          # desconocido: se prueba
        db.monsters["Rata"]["pref"] = "farm"
        self.assertTrue(db.should_fight("Rata"))                 # el usuario manda
        self.assertTrue(db.should_fight(None))                   # sin nombre: se pelea

    def test_spots(self):
        db = MonsterDB()
        c = ["A", "B"]
        self.assertEqual(db.best_spot(c, ""), "A")               # explora el primero
        db.add_spot_time("A", 400); db.add_spot_kill("A", 5)
        self.assertEqual(db.best_spot(c, "A"), "B")              # A ya medido → explora B
        db.add_spot_time("B", 400); db.add_spot_kill("B", 10)
        self.assertEqual(db.best_spot(c, "A"), "B")              # B rinde el doble
        self.assertEqual(db.best_spot(c, "B"), "B")
        db.spots["A"]["xp"] = 9.0                                 # A casi igual → no cambia (histéresis)
        self.assertEqual(db.best_spot(c, "A"), "A")

    def test_plan_zone(self):
        pl = ZonePlanner(KN["zones"])
        cfg = {"farm_plan": [{"from_level": 5, "zone": "Ishalgen"}, {"from_level": 12, "zone": "Morheim"}]}
        self.assertEqual(plan_zone(cfg, pl, 8, 0)["name"], "Ishalgen")
        self.assertEqual(plan_zone(cfg, pl, 8, 4)["name"], "Morheim")      # equipo fuerte adelanta
        self.assertEqual(plan_zone({}, pl, 13, 0)["name"], "Morheim")      # sin plan: conocimiento

    def _brain(self, seq, names, db, cfg=None, routes=None):
        cfg = cfg or load_json(CONFIG_PATH)
        cfg["character"]["gear_power"] = 0

        class P:
            def __init__(s): s.i = 0; s.names = list(names)
            def read(s):
                v = seq[min(s.i, len(seq) - 1)]; s.i += 1; return v
            def read_name(s): return s.names.pop(0) if s.names else None
        ck, act = Clock(), FakeAct()
        b = Brain(cfg, KN, P(), act, clock=ck, log=lambda m: None, alert=lambda m: None,
                  sleep=lambda s: None, book=SkillBook(log=lambda m: None), db=db, routes=routes)
        return b, act, ck

    def test_brain_skips_bad_monster_and_records_xp(self):
        db = MonsterDB()
        for _ in range(3):
            db.record_kill("Lobo", 0.8, 10, 10); db.record_kill("Rata", 0.1, 8, 5)
        seq = [Status(1, 1, 1.0, xp=.40), Status(1, 1, 1.0, xp=.40),          # Rata → se descarta
               Status(1, 1, 0, xp=.40), Status(1, 1, 1.0, xp=.40),            # Lobo → se pelea
               Status(1, 1, .5, xp=.40), Status(1, 1, 0, xp=.50), Status(1, 1, 0, xp=.50)]
        b, act, ck = self._brain(seq, ["Rata", "Lobo"], db)
        out = []
        for _ in range(7):
            out += b.tick(); ck.adv(1.5)
        self.assertIn("skip:Rata", out)
        self.assertIn("escape", act.keys)
        self.assertEqual(db.monsters["Lobo"]["n"], 4)                 # 3 previos + este
        self.assertAlmostEqual(db.monsters["Lobo"]["xp"], 0.8 * 0.7 + 10 * 0.3, places=2)  # midió +10 % de barra
        self.assertEqual(b.kills, 1)

    def test_brain_patrols_and_changes_spot(self):
        cfg = load_json(CONFIG_PATH)
        cfg["character"].update(zone="Morheim", spot="A")
        cfg["spots"] = [{"name": "A", "zone": "Morheim"}, {"name": "B", "zone": "Morheim"}]
        cfg["behavior"]["wander_after_fails"] = 2
        step = [{"key": "w", "down": 0.0, "up": 0.01}]
        db = MonsterDB(); db.add_spot_time("A", 400); db.add_spot_kill("A", 1)
        b, act, ck = self._brain([Status(1, 1, 0)] * 10, [], db, cfg,
                                 routes={"patrol:B": step, "A->B": step})
        out = []
        for _ in range(6):
            out += b.tick(); ck.adv(31)
        self.assertEqual(cfg["character"]["spot"], "B")              # A medido, B sin explorar → va a B
        self.assertIn("down:w", act.keys)                              # recorrió la ruta
        self.assertIn("patrol", out)


if __name__ == "__main__":
    unittest.main()
