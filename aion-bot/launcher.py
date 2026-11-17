#!/usr/bin/env python3
"""Launcher: busca actualizaciones y abre el bot.

  python launcher.py              ventana (o consola si no hay tkinter)
  python launcher.py --no-update  abre el bot sin comprobar nada
  python launcher.py --rollback   vuelve a la versión anterior
"""
import subprocess
import sys
import threading
from pathlib import Path

import updater

BASE = Path(__file__).parent
BG, PANEL, ACCENT, ACCENT2, TEXT, MUTED, DANGER = "#09050f", "#130b21", "#9b6dff", "#c9b3ff", "#e8e0ff", "#8a7bb0", "#ff4d6d"


def launch_app():
    subprocess.Popen([sys.executable, str(BASE / "app.py")], cwd=BASE)


def do_check(cfg):
    """('ok', None) | ('new', (remote, local, changelog)) | ('offline', msg) | ('off', None)"""
    if not cfg.get("repo") or not cfg.get("check_on_start", True):
        return "off", None
    try:
        newer, remote, local = updater.check(cfg)
    except Exception as e:  # sin conexión, repo privado sin token, rama inexistente…
        return "offline", str(e)
    if not newer:
        return "ok", local
    try:
        log = "\n".join(updater.fetch_text(cfg, "CHANGELOG.md").splitlines()[:18])
    except Exception:
        log = ""
    return "new", (remote, local, log)


def do_update(cfg):
    data = updater.download(cfg)
    return updater.apply_package(data, BASE, cfg.get("subdir", ""))


def run_console(cfg):
    state, info = do_check(cfg)
    if state == "new":
        remote, local, log = info
        print(f"Nueva versión {remote} (tienes {local})\n{log}\n")
        if input("¿Actualizar? [s/N] ").strip().lower() == "s":
            try:
                print("Actualizado:", ", ".join(do_update(cfg)))
            except Exception as e:
                print("No se pudo actualizar:", e)
    elif state == "offline":
        print("No se pudo comprobar actualizaciones:", info)
    launch_app()


def run_gui(cfg):
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    root.title("Asmodianos · Launcher")
    root.geometry("560x420")
    root.configure(bg=BG)
    tk.Label(root, text="ᚨᛊᛗᛟᛞᛁᚨᚾ", bg=BG, fg=ACCENT, font=("Segoe UI", 12)).pack(pady=(16, 0))
    tk.Label(root, text="ASMODIANOS", bg=BG, fg=ACCENT2, font=("Palatino Linotype", 22, "bold")).pack()
    tk.Label(root, text=f"Bot de Aion · versión {updater.local_version()}", bg=BG, fg=MUTED).pack()
    status = tk.Label(root, text="Buscando actualizaciones…", bg=BG, fg=TEXT, font=("Segoe UI", 11))
    status.pack(pady=12)
    box = tk.Text(root, height=9, bg=PANEL, fg=TEXT, relief="flat", wrap="word", font=("Consolas", 9))
    box.pack(fill="x", padx=20)
    box.pack_forget()
    bar = ttk.Frame(root)
    bar.pack(pady=14)
    result = {}

    def mk(txt, cmd, color=PANEL):
        b = tk.Button(bar, text=txt, command=cmd, bg=color, fg=TEXT if color == PANEL else "#0b0614",
                      relief="flat", padx=14, pady=6, font=("Segoe UI", 10, "bold"))
        b.pack(side="left", padx=6)
        return b

    def open_app():
        launch_app()
        root.destroy()

    def clear_buttons():
        for w in bar.winfo_children():
            w.destroy()

    def update_and_open():
        clear_buttons()
        status.config(text="Descargando e instalando…", fg=TEXT)

        def work():
            try:
                result["done"] = do_update(cfg)
            except Exception as e:  # noqa: BLE001
                result["err"] = str(e)
        t = threading.Thread(target=work, daemon=True)
        t.start()

        def poll():
            if t.is_alive():
                root.after(200, poll)
            elif "err" in result:
                status.config(text=f"No se pudo actualizar: {result['err']}", fg=DANGER)
                mk("Abrir la versión actual", open_app, ACCENT)
            else:
                status.config(text="¡Actualizado!", fg=ACCENT2)
                root.after(700, open_app)
        poll()

    def do_rollback():
        try:
            v = updater.rollback(BASE)
            status.config(text=f"Restaurada la copia {v}", fg=ACCENT2)
        except Exception as e:  # noqa: BLE001
            status.config(text=f"No se pudo revertir: {e}", fg=DANGER)

    def show(state, info):
        clear_buttons()
        if state == "new":
            remote, local, log = info
            status.config(text=f"Nueva versión {remote} disponible (tienes {local})", fg=ACCENT2)
            box.pack(fill="x", padx=20, before=bar)
            box.insert("1.0", log or "(sin notas de la versión)")
            box.config(state="disabled")
            mk("Actualizar y abrir", update_and_open, ACCENT)
            mk("Abrir sin actualizar", open_app)
        else:
            msg = {"ok": f"Estás al día (v{info})", "off": "Comprobación desactivada",
                   "offline": "No se pudo comprobar (sin conexión o sin acceso al repositorio)"}[state]
            status.config(text=msg, fg=MUTED if state != "ok" else ACCENT2)
            mk("Abrir el bot", open_app, ACCENT)
        if updater.last_backup(BASE):
            mk("Revertir a la anterior", do_rollback)

    def work():
        result["check"] = do_check(cfg)
    t = threading.Thread(target=work, daemon=True)
    t.start()

    def wait():
        if t.is_alive():
            root.after(150, wait)
        else:
            show(*result["check"])
    wait()
    root.mainloop()


def main():
    args = sys.argv[1:]
    if "--rollback" in args:
        print("Restaurada la copia", updater.rollback(BASE))
        return
    if "--no-update" in args:
        launch_app()
        return
    cfg = updater.load_update_cfg(BASE)
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return run_console(cfg)
    run_gui(cfg)


if __name__ == "__main__":
    main()
