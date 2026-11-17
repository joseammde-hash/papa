import unittest
from PIL import Image
import diagnostics, inputs
from engine import load_json, CONFIG_PATH


def solid(v):
    return Image.new("RGB", (200, 120), (v, v, v))


class T(unittest.TestCase):
    def test_frame_diff_and_moved(self):
        self.assertEqual(diagnostics.frame_diff(solid(50), solid(50)), 0)
        self.assertAlmostEqual(diagnostics.frame_diff(solid(50), solid(80)), 30)
        self.assertTrue(diagnostics.moved(30, 1.0))
        self.assertFalse(diagnostics.moved(2.0, 1.0))                # dentro del ruido
        self.assertFalse(diagnostics.moved(10, 5.0))                 # el ruido es alto: no se fía

    def test_movement_test_picks_working_mode(self):
        state = {"v": 50}
        def hold(mode, key, secs):
            if mode == "scancode" and key == "w":
                state["v"] += 40                                     # solo scancode "mueve"
        res = diagnostics.movement_test(lambda: solid(state["v"]), hold, sleep=lambda s: None)
        self.assertEqual((res["pyautogui"], res["scancode"]), (False, True) if inputs.available() else (False, None))
        mode, _ = diagnostics.advice({"pyautogui": False, "scancode": True}, "Aion", False)
        self.assertEqual(mode, "scancode")
        mode, lines = diagnostics.advice({"pyautogui": False, "scancode": False}, "Otra", False)
        self.assertIsNone(mode)
        self.assertTrue(any("administrador" in t for _, t in lines))
        self.assertEqual(diagnostics.advice({"pyautogui": True}, "Aion", True)[0], "pyautogui")

    def test_all_configured_keys_have_scancodes(self):
        cfg = load_json(CONFIG_PATH)
        names = set(cfg["keys"].values()) | {"w", "s"} | set(cfg["behavior"]["wander_keys"]) | {cfg["behavior"]["approach_key"]}
        names |= {sk["key"] for sk in cfg["skills"]} | {cfg["potions"]["hp"]["key"], cfg["potions"]["mp"]["key"]}
        for n in names:
            for part in n.split("+"):
                inputs.scancode_for(part)
        self.assertEqual(inputs.scancode_for("w"), (0x11, False))
        self.assertEqual(inputs.scancode_for("up"), (0x48, True))


if __name__ == "__main__":
    unittest.main()
