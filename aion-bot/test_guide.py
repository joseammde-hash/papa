import unittest
from guide import load_guide, step_for
from engine import Brain, Status, load_json, CONFIG_PATH, KNOWLEDGE_PATH
from skillbook import SkillBook
from monsters import MonsterDB
from test_engine import FakeAct, Clock

KN = load_json(KNOWLEDGE_PATH)


class T(unittest.TestCase):
    def test_guide_covers_all_levels_without_gaps(self):
        g = load_guide()
        for lv in range(1, 65):
            self.assertIsNotNone(step_for(g, lv), f"nivel {lv} sin tramo")
        self.assertEqual(step_for(g, 13)["zone"], "Altgard")
        self.assertEqual(step_for(g, 13)["mode"], "grind")
        self.assertEqual(step_for(g, 9)["mode"], "manual")
        self.assertEqual(step_for(g, 24)["zone"], "Morheim")

    def _brain(self, level, zone, policy="avisar"):
        cfg = load_json(CONFIG_PATH)
        cfg["character"].update(level=level, zone=zone)
        cfg["guide"].update(enabled=True, manual_policy=policy)
        alerts = []
        b = Brain(cfg, KN, type("P", (), {"read": lambda s: Status(1, 1, 0)})(), FakeAct(), clock=Clock(),
                  log=lambda m: None, alert=alerts.append, sleep=lambda s: None,
                  book=SkillBook(log=lambda m: None), db=MonsterDB())
        return b, alerts

    def test_grind_step_sets_zone(self):
        b, alerts = self._brain(22, "Altgard")                 # guía: 21-26 → Morheim
        b.tick()
        self.assertTrue(alerts and "Morheim" in alerts[0])

    def test_guardavieja_is_valid_for_10_19(self):
        for guide_on in (True, False):
            b, alerts = self._brain(13, "Guardavieja")
            b.cfg["guide"]["enabled"] = guide_on
            b.tick()
            self.assertEqual(alerts, [], f"guía={guide_on}")
        b, alerts = self._brain(22, "Guardavieja")             # al 21+ sí toca Morheim
        b.tick()
        self.assertTrue(alerts and "Morheim" in alerts[0])

    def test_in_right_zone_no_alert(self):
        b, alerts = self._brain(13, "Altgard")
        b.tick()
        self.assertEqual(alerts, [])

    def test_manual_step_alerts_and_pauses_once(self):
        b, alerts = self._brain(30, "Morheim")                 # 27-34: misiones de campaña
        b.tick()
        self.assertTrue(alerts and "amarillas" in alerts[0])
        self.assertTrue(b.request_pause)
        b.request_pause = False
        b.last_zone_check = 0
        b.tick()
        self.assertEqual(len(alerts), 1)                       # no repite el aviso

    def test_manual_step_can_keep_farming(self):
        b, alerts = self._brain(30, "Beluslan", policy="farmear")
        b.tick()
        self.assertFalse(b.request_pause)                       # ya está en la zona de la tabla (Beluslan): sigue farmeando
        self.assertEqual(alerts, [])


if __name__ == "__main__":
    unittest.main()
