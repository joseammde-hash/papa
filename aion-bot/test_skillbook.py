import unittest
from PIL import Image, ImageDraw
from skillbook import SkillBook, Slot, analyze_hotbar
from engine import Brain, Status, load_json, CONFIG_PATH, KNOWLEDGE_PATH
from test_engine import FakeAct, Clock

HB = {"cols": 10, "rows": 1, "keys": list("1234567890"), "row_mods": [""], "occupied_std": 12}
KN = load_json(KNOWLEDGE_PATH)


def icon(draw, x, pattern, dim=1.0):
    """Dibuja un icono distinto según 'pattern' dentro del hueco x (40 px)."""
    v = lambda c: int(c * dim)
    draw.rectangle([x, 0, x + 39, 39], fill=(v(40), v(40), v(40)))
    for i in range(6):
        if (pattern >> i) & 1:
            draw.rectangle([x + 4 + (i % 3) * 11, 4 + (i // 3) * 18, x + 12 + (i % 3) * 11, 18 + (i // 3) * 18],
                           fill=(v(230), v(180 - i * 20), v(60 + i * 25)))


def bar(patterns, dims=None):
    img = Image.new("RGB", (400, 40), (40, 40, 40))
    d = ImageDraw.Draw(img)
    for i, p in enumerate(patterns):
        if p is not None:
            icon(d, i * 40, p, (dims or {}).get(i, 1.0))
    return img


class T(unittest.TestCase):
    def test_scan_new_and_cooldown(self):
        b = SkillBook(log=lambda m: None)
        sl = analyze_hotbar(bar([5, 9, 18, None]), HB)
        self.assertEqual([s.occupied for s in sl[:4]], [True, True, True, False])
        self.assertEqual(len(b.update(sl, 0)), 3)
        self.assertEqual(len(b.update(analyze_hotbar(bar([5, 9, 18, None]), HB), 1)), 0)
        # enfriamiento: el icono 1 se oscurece pero sigue siendo el mismo
        b.update(analyze_hotbar(bar([5, 9, 18], {1: .4}), HB), 2)
        e1 = [e for e in b.entries.values() if e["key"] == "2"][0]
        self.assertFalse(b.live[e1["id"]]["ready"])
        self.assertEqual(len(b.entries), 3)
        b.update(analyze_hotbar(bar([5, 9, 18]), HB), 8)
        self.assertTrue(b.live[e1["id"]]["ready"])
        self.assertEqual(e1["cooldown"], 6.0)                 # enfriamiento medido
        # habilidad nueva aparece en el hueco 5
        new = b.update(analyze_hotbar(bar([5, 9, 18, None, None, 33]), HB), 9)
        self.assertEqual([e["key"] for e in new], ["6"])

    def test_ignore_scroll_row(self):
        hb = dict(HB, rows=3, ignore_rows=[0], row_mods=["", "shift", "ctrl"])
        img = Image.new("RGB", (400, 120), (40, 40, 40))
        d = ImageDraw.Draw(img)
        for r in range(3):
            for c, p in enumerate((5, 9)):
                icon(d, c * 40, p + r)          # icono distinto en cada fila
                img.paste(img.crop((c * 40, 0, c * 40 + 40, 40)), (c * 40, r * 40))
        sl = analyze_hotbar(img, hb)
        self.assertFalse(any(s.occupied for s in sl if s.idx < 10))        # fila de arriba ignorada
        self.assertEqual([s.key for s in sl if s.idx in (10, 11, 20)], ["shift+1", "shift+2", "ctrl+1"])
        self.assertTrue(sl[10].occupied and sl[20].occupied)

    def test_learning_roles(self):
        b = SkillBook(log=lambda m: None)
        b.update(analyze_hotbar(bar([5, 9, 18, 33]), HB), 0)
        ids = {e["key"]: e["id"] for e in b.entries.values()}
        for _ in range(3):   # ataque básico: ~4 pts de vida por ventana
            b.finish_obs(b.begin_obs("_basic", Status(1, 1, .9), 0), Status(1, 1, .86))
        for _ in range(2):   # "1": daño fuerte
            b.finish_obs(b.begin_obs(ids["1"], Status(1, 1, .9), 0), Status(1, 1, .70))
        for _ in range(2):   # "2": cura
            b.finish_obs(b.begin_obs(ids["2"], Status(.4, 1, .9), 0), Status(.6, 1, .86))
        for _ in range(2):   # "3": nada
            b.finish_obs(b.begin_obs(ids["3"], Status(1, 1, .9), 0), Status(1, 1, .86))
        r = {k: b.role(b.entries[i]) for k, i in ids.items()}
        self.assertEqual((r["1"], r["2"], r["3"], r["4"]), ("damage", "heal", "utility", "unknown"))

    def test_choose_policy_and_overrides(self):
        b = SkillBook(log=lambda m: None)
        b.update(analyze_hotbar(bar([5, 9, 18, 33]), HB), 0)
        e = {x["key"]: x for x in b.entries.values()}
        e["1"].update(role="damage", avg_drop=10.0)
        e["2"].update(role="damage", avg_drop=20.0)
        e["3"].update(role="utility")
        self.assertEqual(b.choose(Status(1, 1, .9), can_explore=False)[0]["key"], "2")
        self.assertEqual(b.choose(Status(1, 1, .9), can_explore=True)[1], "explore")   # la "4" es nueva
        e["2"]["role_user"] = "ignore"
        self.assertEqual(b.choose(Status(1, 1, .9), can_explore=False)[0]["key"], "1")
        b.excluded = {"1"}
        self.assertIsNone(b.choose(Status(1, 1, .9), can_explore=False))
        e["3"]["role_user"] = "heal"; e["3"]["avg_heal"] = 9
        b.excluded = set()
        self.assertEqual(b.choose(Status(.3, 1, .9), can_explore=False)[1], "heal")   # cura con poca vida

    def test_brain_uses_new_skill_and_learns(self):
        cfg = load_json(CONFIG_PATH)
        cfg["auto_skills"]["mode"] = "auto"
        cfg["skills"] = []
        ck, act = Clock(), FakeAct()
        sig = lambda p: analyze_hotbar(bar([p]), HB)[0].sig
        slot = Slot(8, "9", True, sig(21), 100.0)
        seq = [Status(1, 1, 1.0, slots=[slot]), Status(1, 1, .95, slots=[slot]),
               Status(1, 1, .5, slots=[slot]), Status(1, 1, .5, slots=[slot]),
               Status(1, 1, .5, slots=[slot])]

        class P:
            def __init__(s): s.i = 0
            def read(s):
                v = seq[min(s.i, len(seq) - 1)]; s.i += 1; return v
        b = Brain(cfg, KN, P(), act, clock=ck, log=lambda m: None, alert=lambda m: None,
                  sleep=lambda s: None, book=SkillBook(log=lambda m: None))
        out = []
        for _ in range(5):
            out += b.tick(); ck.adv(1.3)
        self.assertTrue(any(a.startswith("auto:") and a.endswith(":explore") for a in out))
        self.assertIn("9", act.keys)                       # pulsó la tecla de la habilidad nueva
        e = list(b.book.entries.values())[0]
        self.assertGreater(e["avg_drop"], 20)              # observó que baja mucho la vida del objetivo

    def test_potion_key_never_auto_used(self):
        cfg = load_json(CONFIG_PATH)
        b = Brain(cfg, KN, None, FakeAct(), clock=Clock(), log=lambda m: None, book=SkillBook(log=lambda m: None))
        self.assertIn(cfg["potions"]["hp"]["key"], b._excluded_keys())


if __name__ == "__main__":
    unittest.main()
