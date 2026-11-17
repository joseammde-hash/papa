import os, tempfile, unittest, zipfile
from pathlib import Path
import gamescan
from engine import Brain, Status, load_json, CONFIG_PATH, KNOWLEDGE_PATH
from skillbook import SkillBook
from monsters import MonsterDB
from test_engine import FakeAct, Clock

NPC_XML = """<?xml version="1.0"?><client_npcs>
<npc><id>1</id><name>STR_NPC_WOLF</name><level>12</level><hp>900</hp></npc>
<npc><id>2</id><name>Kobold Soldier</name><level>14</level></npc>
<npc><id>3</id><name>Giant Rat</name><level>3</level></npc>
<npc><id>4</id><name>Elder Drake</name><level>30</level></npc></client_npcs>"""
STR_XML = """<?xml version="1.0"?><strings><string><id>STR_NPC_WOLF</id><body>Lobo Gris</body></string></strings>"""
SKILL_XML = """<?xml version="1.0"?><client_skills><skill id="11" name="Arrow Strike"/><skill id="12" name="Snipe"/></client_skills>"""


def make_game(root):
    root = Path(root)
    (root / "bin64").mkdir(parents=True); (root / "bin64" / "aion.bin").write_bytes(b"MZ")
    (root / "data").mkdir()
    with zipfile.ZipFile(root / "data" / "Skills.pak", "w") as z:
        z.writestr("skills/client_skills.xml", SKILL_XML)
        z.writestr("npc/client_npcs.xml", NPC_XML)
        z.writestr("l10n/client_strings_npc.xml", STR_XML)
        z.writestr("../evil/escape.xml", "<x/>")                     # ruta maliciosa dentro del zip
    (root / "data" / "Big.pak").write_bytes(os.urandom(70000))          # simula un pak cifrado
    (root / "data" / "readable.xml").write_text(NPC_XML, encoding="utf-8")
    (root / "data" / "enc.xml").write_bytes(b"\x8f" + os.urandom(4999))   # no empieza por "<"
    (root / "system.cfg").write_text("g_windowed=1\n")


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        make_game(self.d)

    def test_find_install(self):
        found = gamescan.find_install([Path(self.d).parent], max_depth=3)
        self.assertIn(Path(self.d), found)

    def test_find_private_server_client_without_aion_bin(self):
        base = Path(tempfile.mkdtemp())
        (base / "Juegos" / "EUROaion" / "data").mkdir(parents=True)
        (base / "Juegos" / "EUROaion" / "data" / "data.pak").write_bytes(b"x" * 100)
        (base / "Juegos" / "Otra" / "data").mkdir(parents=True)                     # no es Aion
        found = gamescan.find_install([base], max_depth=4)
        self.assertEqual(found, [base / "Juegos" / "EUROaion"])

    def test_inventory_classifies_files(self):
        inv = gamescan.inventory(self.d, log=lambda m: None)
        kinds = {p["file"]: p["kind"] for p in inv["paks"]}
        self.assertEqual(kinds["Skills.pak"], "zip")
        self.assertEqual(kinds["Big.pak"], "cifrado_o_comprimido")
        xs = {x["file"]: x["kind"] for x in inv["xml_samples"]}
        self.assertEqual((xs["readable.xml"], xs["enc.xml"]), ("xml", "codificado"))
        text = " | ".join(t for _, t in gamescan.report_lines(inv))
        self.assertIn("se pueden abrir como ZIP", text)
        self.assertIn("cifrados", text)
        self.assertNotIn(str(Path.home()) + os.sep, text.replace("~", ""))     # sin rutas personales

    def test_extract_and_import(self):
        out = Path(tempfile.mkdtemp())
        n = gamescan.extract_paks(self.d, out, log=lambda m: None)
        names = {p.name for p in out.glob("*.xml")}
        self.assertTrue({"client_skills.xml", "client_npcs.xml", "client_strings_npc.xml"} <= names, names)
        self.assertEqual(list(out.parent.glob("evil")), [])                      # no escribe fuera de 'out'
        data = gamescan.import_dir(out, Path(tempfile.mkdtemp()) / "g.json", log=lambda m: None)
        self.assertEqual(data["monsters"]["Lobo Gris"]["level"], 12)              # cadena resuelta por id
        self.assertEqual(data["monsters"]["Lobo Gris"]["hp"], 900)
        self.assertEqual(data["skills"]["11"], "Arrow Strike")
        self.assertGreaterEqual(n, 3)

    def test_level_lookup_tolerates_ocr_noise(self):
        gd = gamescan.GameData({"monsters": {"Kobold Soldier": {"level": 14}, "Lobo Gris": {"level": 12}}})
        self.assertEqual(gd.level_of("Kobold Soldier"), 14)
        self.assertEqual(gd.level_of("Kobold Sold1er"), 14)
        self.assertIsNone(gd.level_of("Dragon Rojo"))

    def test_brain_skips_by_level(self):
        cfg = load_json(CONFIG_PATH)
        cfg["character"]["level"] = 13
        names = ["Giant Rat", "Elder Drake", "Kobold Soldier"]               # niv 3 (gris), 30 (peligroso), 14 (ok)

        class P:
            def __init__(s): s.n = list(names)
            def read(s): return Status(1, 1, 1.0)
            def read_name(s): return s.n.pop(0)
        b = Brain(cfg, load_json(KNOWLEDGE_PATH), P(), FakeAct(), clock=Clock(), log=lambda m: None,
                  alert=lambda m: None, sleep=lambda s: None, book=SkillBook(log=lambda m: None), db=MonsterDB())
        b.gamedata = gamescan.GameData({"monsters": {"Giant Rat": {"level": 3}, "Elder Drake": {"level": 30},
                                                      "Kobold Soldier": {"level": 14}}})
        out = []
        for _ in range(3):
            out += b.tick(); b.in_combat = False
        self.assertEqual([a for a in out if a.startswith("skip")], ["skip:Giant Rat", "skip:Elder Drake"])


if __name__ == "__main__":
    unittest.main()
