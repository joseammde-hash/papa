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

    def test_running_install_from_process_path(self):
        run = lambda cmd: "C:\\Juegos\\EUROaion\\bin64\\aion.bin\r\n"
        p = gamescan.running_install(run=run)
        self.assertEqual(p.name, "EUROaion")
        self.assertIsNone(gamescan.running_install(run=lambda cmd: ""))      # proceso no encontrado o sin permisos

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


class T2(unittest.TestCase):
    def test_stage_copies_only_important_paks_without_touching_game(self):
        game, work = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        for rel in ("Data/Europe/Npcs/Npcs.pak", "Data/Europe/skills/skills.pak", "Data/Sounds/music.pak", "L10N/2_esn/strings.pak"):
            f = game / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"x" * 1000)
        names = gamescan.stage_paks(game, work, log=lambda m: None)
        self.assertEqual(len(names), 3)                                       # music.pak no
        self.assertTrue(all((work / "PAK" / n).exists() for n in names))
        self.assertTrue((game / "Data/Europe/Npcs/Npcs.pak").exists())          # original intacto
        self.assertTrue(any("Npcs" in n for n in names))

    def test_import_reads_nested_folders(self):
        d = Path(tempfile.mkdtemp())
        (d / "Npcs" / "data").mkdir(parents=True)
        (d / "Npcs" / "data" / "client_npcs.xml").write_text(NPC_XML, encoding="utf-8")
        data = gamescan.import_dir(d, Path(tempfile.mkdtemp()) / "g.json", log=lambda m: None)
        self.assertEqual(data["monsters"]["Kobold Soldier"]["level"], 14)

    def test_report_marks_key_paks_status(self):
        game = Path(tempfile.mkdtemp())
        (game / "Data").mkdir()
        with zipfile.ZipFile(game / "Data" / "Skills.pak", "w") as z:
            z.writestr("a.xml", "<a/>")
        (game / "Data" / "Npcs.pak").write_bytes(os.urandom(70000))
        text = " | ".join(t for _, t in gamescan.report_lines(gamescan.inventory(game, log=lambda m: None)))
        self.assertIn("Skills.pak → legible (ZIP)", text)
        self.assertIn("Npcs.pak → cifrado", text)


AION_NPC = """<?xml version="1.0"?><npc_clients>
<npc_client><id>210001</id><name>wolf_a</name><desc>STR_MONSTER_WOLF2</desc><level>12</level></npc_client>
<npc_client><id>210002</id><name>drake_boss</name><desc>STR_MONSTER_DRAKE</desc><level>30</level></npc_client></npc_clients>"""
AION_STR = """<?xml version="1.0"?><strings>
<string><id>1</id><name>STR_MONSTER_WOLF2</name><body>Lobo Negro</body></string>
<string><id>2</id><name>STR_MONSTER_DRAKE</name><body>Drake Anciano</body></string></strings>"""


class T3(unittest.TestCase):
    def test_real_schema_desc_code_resolved_via_name_key(self):
        game, out = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        with zipfile.ZipFile(game / "Npcs.pak", "w") as z:
            z.writestr("client_npcs.xml", AION_NPC)
        sd = game / "L10N" / "2_esn" / "data" / "Strings"
        sd.mkdir(parents=True)
        (sd / "client_strings_monster.xml").write_text(AION_STR, encoding="utf-8")
        (game / "L10N" / "2_eng" / "data" / "Strings").mkdir(parents=True)
        (game / "L10N" / "2_eng" / "data" / "Strings" / "client_strings_monster.xml").write_text("<x/>")
        self.assertEqual(gamescan.extract_paks(game, out, log=lambda m: None), 1)
        self.assertEqual(gamescan.copy_strings(game, out, "esn", log=lambda m: None), 1)        # solo el idioma elegido
        data = gamescan.import_dir(out, Path(tempfile.mkdtemp()) / "g.json", log=lambda m: None)
        self.assertEqual(data["monsters"], {"Lobo Negro": {"level": 12}, "Drake Anciano": {"level": 30}})
        self.assertEqual(gamescan.encoded_count(out), (2, 0))

    def test_encoded_xml_is_counted(self):
        d = Path(tempfile.mkdtemp())
        (d / "a.xml").write_text("<a/>")
        (d / "b.xml").write_bytes(b"\x8f" + os.urandom(100))
        self.assertEqual(gamescan.encoded_count(d), (1, 1))
