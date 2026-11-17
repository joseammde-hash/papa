"""Teclas por 'scancode' (Windows): las aceptan juegos que ignoran las teclas virtuales normales."""
import sys
import time

SC = {"esc": 0x01, "escape": 0x01, "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9, "9": 10, "0": 11,
      "-": 12, "=": 13, "tab": 0x0F, "q": 0x10, "w": 0x11, "e": 0x12, "r": 0x13, "t": 0x14, "y": 0x15, "u": 0x16,
      "i": 0x17, "o": 0x18, "p": 0x19, "enter": 0x1C, "return": 0x1C, "ctrl": 0x1D, "a": 0x1E, "s": 0x1F, "d": 0x20,
      "f": 0x21, "g": 0x22, "h": 0x23, "j": 0x24, "k": 0x25, "l": 0x26, "shift": 0x2A, "z": 0x2C, "x": 0x2D,
      "c": 0x2E, "v": 0x2F, "b": 0x30, "n": 0x31, "m": 0x32, "alt": 0x38, "space": 0x39,
      "f1": 0x3B, "f2": 0x3C, "f3": 0x3D, "f4": 0x3E, "f5": 0x3F, "f6": 0x40, "f7": 0x41, "f8": 0x42, "f9": 0x43,
      "f10": 0x44, "f11": 0x57, "f12": 0x58}
EXT = {"up": 0x48, "left": 0x4B, "right": 0x4D, "down": 0x50}      # teclas extendidas


def scancode_for(name):
    n = name.lower()
    if n in SC:
        return SC[n], False
    if n in EXT:
        return EXT[n], True
    raise KeyError(f"tecla sin scancode: {name}")


def _send(name, up):
    import ctypes
    from ctypes import wintypes
    code, ext = scancode_for(name)

    class KI(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class MI(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class HI(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]

    class U(ctypes.Union):
        _fields_ = [("ki", KI), ("mi", MI), ("hi", HI)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", U)]

    flags = 0x0008 | (0x0002 if up else 0) | (0x0001 if ext else 0)     # SCANCODE | KEYUP | EXTENDED
    inp = INPUT(1, U(ki=KI(0, code, flags, 0, 0)))
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def available():
    return sys.platform.startswith("win")


def key_down(name):
    _send(name, False)


def key_up(name):
    _send(name, True)


def press(name, hold=0.05):
    key_down(name)
    time.sleep(hold)
    key_up(name)


def hotkey(names):
    *mods, last = names
    for m in mods:
        key_down(m)
        time.sleep(0.02)
    press(last)
    for m in reversed(mods):
        key_up(m)
