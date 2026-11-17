"""Diagnóstico: ¿se mueve el personaje cuando el bot pulsa teclas?"""
import sys
import time

import inputs


def frame_diff(a, b, size=(64, 36)):
    """Diferencia media (0..255) entre dos capturas, reducidas y en gris."""
    ga, gb = a.convert("L").resize(size), b.convert("L").resize(size)
    pa, pb = list(ga.tobytes()), list(gb.tobytes())
    return sum(abs(x - y) for x, y in zip(pa, pb)) / max(1, len(pa))


def moved(diff, noise):
    return diff > max(3 * noise, 4.0)


def is_admin():
    if not sys.platform.startswith("win"):
        return None
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return None


def advice(results, title, admin):
    """results: {'pyautogui': bool, 'scancode': bool|None}. Devuelve (modo_recomendado, líneas)."""
    py, sc = results.get("pyautogui"), results.get("scancode")
    out = []
    if py:
        return "pyautogui", [("ok", "El personaje se mueve con el método normal. Las teclas funcionan.")]
    if sc:
        return "scancode", [("ok", "El método normal NO movió al personaje pero el método por scancode SÍ. "
                                   "Lo dejo activado (input_mode = scancode).")]
    out.append(("bad", "El personaje no se movió con ningún método. Causas habituales, por orden:"))
    if admin is False:
        out.append(("warn", "1) Si Aion se ejecuta como administrador, Windows bloquea teclas de un programa normal: "
                            "cierra el bot y ábrelo con clic derecho en INICIAR.bat → Ejecutar como administrador."))
    else:
        out.append(("warn", "1) Si Aion va como administrador, el bot también debe ir como administrador."))
    out.append(("warn", "2) Aion debe estar en primer plano y en modo ventana o ventana sin bordes (no pantalla completa exclusiva)."
                        + (f" Ventana activa al probar: «{title}»." if title else "")))
    out.append(("warn", "3) Mira que 'W' sea tu tecla de avanzar (Opciones → Teclas) y que el personaje no esté en cinemática, muerto o escribiendo en el chat."))
    out.append(("warn", "4) Si usas un teclado no estándar, cambia las teclas de movimiento en config.json (behavior.wander_keys y approach_key)."))
    return None, out


def movement_test(grab, hold, sleep=time.sleep, key="w", back="s", secs=1.2):
    """Prueba cada método. grab() -> imagen; hold(mode, key, secs) mantiene la tecla.
    Devuelve {'pyautogui': bool, 'scancode': bool|None, 'noise': float}."""
    a = grab()
    sleep(0.5)
    noise = frame_diff(a, grab())
    res = {"noise": noise, "scancode": None}
    for mode in ("pyautogui", "scancode"):
        if mode == "scancode" and not inputs.available():
            continue
        before = grab()
        hold(mode, key, secs)
        sleep(0.3)
        after = grab()
        res[mode] = moved(frame_diff(before, after), noise)
        hold(mode, back, secs)               # vuelve al punto de partida
        sleep(0.4)
    return res
