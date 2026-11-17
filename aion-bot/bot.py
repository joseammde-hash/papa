#!/usr/bin/env python3
"""Bot de leveling por simulación de teclas (sin leer memoria del juego).

Uso:
  pip install pyautogui pynput
  python bot.py calibrate   # imprime posición y color bajo el ratón (para hp_pixel)
  python bot.py run         # arranca el bucle (tienes 5 s para enfocar la ventana del juego)

F10 pausa/reanuda, F12 detiene. Mueve el ratón a una esquina de la pantalla para parada de emergencia (failsafe de pyautogui).
"""
import json, random, sys, time, threading
from pathlib import Path

import pyautogui
from pynput import keyboard

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.02

CFG = json.loads((Path(__file__).parent / "config.json").read_text(encoding="utf-8"))
state = {"paused": False, "stop": False}


def jitter(x):
    j = CFG.get("random_jitter", 0)
    return max(0.0, x * (1 + random.uniform(-j, j)))


def sleep(x):
    end = time.time() + jitter(x)
    while time.time() < end and not state["stop"]:
        while state["paused"] and not state["stop"]:
            time.sleep(0.2)
        time.sleep(0.05)


def press(key):
    pyautogui.press(key)


def start_hotkeys():
    def on_press(k):
        name = getattr(k, "name", None)
        if name == CFG["pause_hotkey"]:
            state["paused"] = not state["paused"]
            print("PAUSA" if state["paused"] else "REANUDADO")
        elif name == CFG["stop_hotkey"]:
            state["stop"] = True
            print("DETENIENDO...")
    keyboard.Listener(on_press=on_press, daemon=True).start()


def hp_low():
    r = CFG["rest"]
    if not r["enabled"] or r["hp_pixel"] == [0, 0]:
        return False
    x, y = r["hp_pixel"]
    px = pyautogui.screenshot(region=(x, y, 1, 1)).getpixel((0, 0))
    tol = r["color_tolerance"]
    # Si el píxel de la barra ya NO tiene el color de "vida", la vida bajó de ese punto.
    return any(abs(a - b) > tol for a, b in zip(px[:3], r["hp_color_rgb"]))


def rest():
    r = CFG["rest"]
    print("Vida baja: descansando")
    if r.get("heal_key"):
        press(r["heal_key"])
        sleep(1.5)
    if r.get("sit_key"):
        press(r["sit_key"])
    sleep(r["rest_seconds"])
    if r.get("sit_key"):
        press(r["sit_key"])  # levantarse


def fight():
    last_used = {}
    t0 = time.time()
    while time.time() - t0 < CFG["fight_timeout_seconds"] and not state["stop"]:
        if hp_low():
            return
        for s in CFG["attack_rotation"]:
            if time.time() - last_used.get(s["key"], 0) >= s["cooldown"]:
                press(s["key"])
                last_used[s["key"]] = time.time()
                sleep(s["delay_after"])
                break
        else:
            sleep(0.3)


def loot():
    for _ in range(CFG["loot_presses"]):
        press(CFG["loot_key"])
        sleep(0.4)


def calibrate():
    print("Mueve el ratón sobre la barra de vida (parte llena). Ctrl+C para salir.")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"pos=({x},{y}) rgb={pyautogui.screenshot(region=(x, y, 1, 1)).getpixel((0, 0))[:3]}   ", end="\r")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print()


def run():
    print("Empieza en 5 s: enfoca la ventana de Aion. F10 pausa, F12 detiene.")
    time.sleep(5)
    start_hotkeys()
    t_start = time.time()
    last_buff = {b["key"]: 0 for b in CFG["buff_keys"]}
    while not state["stop"]:
        if time.time() - t_start > CFG["max_runtime_minutes"] * 60:
            print("Tiempo máximo alcanzado.")
            break
        for b in CFG["buff_keys"]:
            if time.time() - last_buff[b["key"]] >= b["every_seconds"]:
                press(b["key"]); last_buff[b["key"]] = time.time(); sleep(1.5)
        if hp_low():
            rest()
            continue
        press(CFG["target_key"])
        sleep(0.5)
        fight()
        loot()
        sleep(0.8)
    print("Bot detenido.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    {"calibrate": calibrate, "run": run}.get(cmd, run)()
