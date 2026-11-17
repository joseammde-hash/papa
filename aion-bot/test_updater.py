import io, json, tempfile, unittest, zipfile
from pathlib import Path
import updater


def make_zip(files, prefix="owner-repo-abc123/aion-bot/"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("owner-repo-abc123/", "")
        for k, v in files.items():
            z.writestr(prefix + k, v)
    return buf.getvalue()


class T(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "VERSION").write_text("1.0.0"); (self.d / "app.py").write_text("print('viejo')")
        (self.d / "config.json").write_text(json.dumps({"a": 1, "x": {"keep": "mio"}}))
        (self.d / "monsters.json").write_text("DATOS")
        (self.d / "update.json").write_text("{}")

    def test_versions(self):
        self.assertTrue(updater.is_newer("1.10.0", "1.9.3"))
        self.assertFalse(updater.is_newer("1.0.0", "1.0.0"))

    def test_apply_keeps_user_data_and_merges_config(self):
        z = make_zip({"VERSION": "1.1.0", "app.py": "print('nuevo')", "engine.py": "x = 1",
                      "config.json": json.dumps({"a": 99, "b": 2, "x": {"keep": "defecto", "new": 5}}),
                      "monsters.json": "PISADO", "update.json": "PISADO", "evil.exe": "MZ",
                      "sub/deep.py": "y"})
        written = updater.apply_package(z, self.d, "aion-bot")
        self.assertEqual((self.d / "app.py").read_text(), "print('nuevo')")
        self.assertEqual(updater.local_version(self.d), "1.1.0")
        cfg = json.loads((self.d / "config.json").read_text())
        self.assertEqual((cfg["a"], cfg["b"], cfg["x"]["keep"], cfg["x"]["new"]), (1, 2, "mio", 5))
        self.assertEqual((self.d / "monsters.json").read_text(), "DATOS")
        self.assertEqual((self.d / "update.json").read_text(), "{}")
        self.assertFalse((self.d / "evil.exe").exists() or (self.d / "deep.py").exists())
        self.assertIn("engine.py", written)

    def test_rejects_bad_syntax_without_touching_files(self):
        z = make_zip({"VERSION": "9.9.9", "app.py": "def (:"})
        with self.assertRaises(SyntaxError):
            updater.apply_package(z, self.d, "aion-bot")
        self.assertEqual((self.d / "app.py").read_text(), "print('viejo')")
        self.assertEqual(updater.local_version(self.d), "1.0.0")

    def test_rejects_package_without_app(self):
        with self.assertRaises(ValueError):
            updater.apply_package(make_zip({"engine.py": "x=1"}), self.d, "aion-bot")

    def test_rollback(self):
        updater.apply_package(make_zip({"VERSION": "1.1.0", "app.py": "print('nuevo')", "engine.py": "x = 1"}),
                              self.d, "aion-bot")
        updater.rollback(self.d)
        self.assertEqual((self.d / "app.py").read_text(), "print('viejo')")
        self.assertEqual(updater.local_version(self.d), "1.0.0")
        self.assertFalse((self.d / "engine.py").exists())          # el archivo nuevo también se retira


if __name__ == "__main__":
    unittest.main()
