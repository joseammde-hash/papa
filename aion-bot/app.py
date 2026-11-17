#!/usr/bin/env python3
"""Ventana del bot con tema asmodiano (violeta oscuro y plata).

pip install pyautogui pynput pillow   (opcional para leer el nivel: pytesseract)
python app.py
"""
import json
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import engine
from engine import BotRunner, load_json, save_json
from skillbook import SkillBook
from monsters import MonsterDB
import updater
from guide import load_guide, step_for
import vision
import inputs
import diagnostics
import autoconfig
import gamescan
from tkinter import filedialog

# --- Paleta asmodiana ------------------------------------------------------
BG, PANEL, PANEL2 = "#09050f", "#130b21", "#1c1031"
LINE, ACCENT, ACCENT2 = "#33205c", "#9b6dff", "#c9b3ff"
TEXT, MUTED, DANGER, OK = "#e8e0ff", "#8a7bb0", "#ff4d6d", "#5be0a8"
RUNES = "ᚨ ᛊ ᛗ ᛟ ᛞ ᛁ ᚨ ᚾ"
TITLE_FONT = ("Palatino Linotype", 20, "bold")
BODY = ("Segoe UI", 10)

cfg = load_json(engine.CONFIG_PATH)
kn = load_json(engine.KNOWLEDGE_PATH)
planner = engine.ZonePlanner(kn["zones"])
# claves nuevas por si el config.json viene de una versión anterior
cfg["bars"].setdefault("xp", {"region": None, "color": None, "tol": 60})
cfg["bars"].setdefault("target_name_region", None)
cfg["bars"].setdefault("minimap_region", None)
cfg.setdefault("explore", {"enabled": True, "turn_keys": ["d"], "forward_key": "w", "turn_seconds": 0.45,
                           "sweeps_per_circle": 8, "walk_seconds": [2.0, 4.0], "stuck_threshold": 3.0, "sweep_after_fails": 2})
cfg.setdefault("monsters", {"enabled": True, "min_samples": 3, "keep_ratio": 0.6, "max_danger": 80, "max_skips": 6,
                            "auto_spot": True, "spot_check_seconds": 30, "explore_minutes": 5, "switch_ratio": 0.7})
cfg.setdefault("spots", [])
cfg.setdefault("farm_plan", [])
cfg.setdefault("guide", {"enabled": True, "manual_policy": "avisar", "level_bonus": 0})
guide = load_guide()
cfg["character"].setdefault("spot", "")
cfg["behavior"].setdefault("approach_key", "w")
db = MonsterDB.load(engine.MONSTERS_PATH)
runner = None
events = queue.Queue()

root = tk.Tk()
root.title("Asmodianos · EUROaion · Ranger")
root.geometry("900x680")
root.configure(bg=BG)

# --- Estilos ---------------------------------------------------------------
st = ttk.Style(root)
st.theme_use("clam")
st.configure(".", background=BG, foreground=TEXT, fieldbackground=PANEL2, font=BODY,
             bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
st.configure("TFrame", background=BG)
st.configure("Card.TFrame", background=PANEL)
st.configure("TLabel", background=BG, foreground=TEXT)
st.configure("Card.TLabel", background=PANEL)
st.configure("Muted.TLabel", background=PANEL, foreground=MUTED)
st.configure("Big.TLabel", background=PANEL, foreground=ACCENT2, font=("Palatino Linotype", 16, "bold"))
st.configure("TNotebook", background=BG, borderwidth=0)
st.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(16, 8))
st.map("TNotebook.Tab", background=[("selected", PANEL2)], foreground=[("selected", ACCENT2)])
st.configure("TButton", background=PANEL2, foreground=TEXT, padding=(12, 6), borderwidth=1)
st.map("TButton", background=[("active", LINE)])
st.configure("Accent.TButton", background=ACCENT, foreground="#0b0614", font=("Segoe UI", 10, "bold"))
st.map("Accent.TButton", background=[("active", ACCENT2)])
st.configure("Danger.TButton", background=DANGER, foreground="#0b0614", font=("Segoe UI", 10, "bold"))
st.configure("TCheckbutton", background=PANEL, foreground=TEXT)
st.configure("TRadiobutton", background=PANEL, foreground=TEXT)
st.configure("TEntry", fieldbackground=PANEL2, foreground=TEXT)
st.configure("TCombobox", fieldbackground=PANEL2, foreground=TEXT, arrowcolor=ACCENT2)
st.configure("TSpinbox", fieldbackground=PANEL2, foreground=TEXT, arrowcolor=ACCENT2)
st.configure("Treeview", background=PANEL2, fieldbackground=PANEL2, foreground=TEXT, rowheight=26)
st.configure("Treeview.Heading", background=LINE, foreground=ACCENT2, font=("Segoe UI", 10, "bold"))
st.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#0b0614")])
for name, col in (("hp", "#d6334f"), ("mp", "#3b82f6"), ("tg", "#e0a030")):
    st.configure(f"{name}.Horizontal.TProgressbar", background=col, troughcolor=PANEL2,
                 bordercolor=LINE, lightcolor=col, darkcolor=col)

# --- Cabecera --------------------------------------------------------------
hdr = tk.Canvas(root, height=78, bg=BG, highlightthickness=0)
hdr.pack(fill="x")


def draw_header(_e=None):
    hdr.delete("all")
    w = hdr.winfo_width()
    for i in range(78):                      # degradado negro → violeta
        t = i / 78
        r, g, b = int(9 + 40 * t), int(5 + 18 * t), int(15 + 90 * t)
        hdr.create_line(0, i, w, i, fill=f"#{r:02x}{g:02x}{b:02x}")
    for sx in (1, -1):                       # alas estilizadas
        x0 = w // 2
        pts = [(x0 + sx * 40, 42), (x0 + sx * 120, 14), (x0 + sx * 200, 30),
               (x0 + sx * 150, 38), (x0 + sx * 210, 52), (x0 + sx * 130, 52),
               (x0 + sx * 90, 62), (x0 + sx * 40, 50)]
        hdr.create_polygon(pts, fill="#1f1245", outline=ACCENT, width=1)
    hdr.create_text(w // 2, 30, text="ASMODIANOS", fill=ACCENT2, font=TITLE_FONT)
    hdr.create_text(w // 2, 58, text=f"EUROaion  ·  Ranger  ·  Daeva de Pandaemonium  ·  v{updater.local_version()}",
                    fill=MUTED, font=("Segoe UI", 9))
    hdr.create_text(16, 12, text=RUNES, fill=ACCENT, anchor="w", font=("Segoe UI", 11))
    hdr.create_text(w - 16, 12, text=RUNES, fill=ACCENT, anchor="e", font=("Segoe UI", 11))
    hdr.create_line(0, 77, w, 77, fill=ACCENT)


hdr.bind("<Configure>", draw_header)

nb = ttk.Notebook(root)
nb.pack(fill="both", expand=True, padx=12, pady=(8, 12))


def card(parent, **kw):
    f = ttk.Frame(parent, style="Card.TFrame", padding=12)
    f.pack(**kw)
    return f


# ===========================================================================
# Pestaña Batalla
# ===========================================================================
tab_run = ttk.Frame(nb)
nb.add(tab_run, text="⚔  Batalla")
top = card(tab_run, fill="x", padx=6, pady=6)
bars = {}
for i, (k, label, sty) in enumerate((("hp", "Vida", "hp"), ("mp", "Maná", "mp"), ("tg", "Objetivo", "tg"))):
    ttk.Label(top, text=label, style="Card.TLabel").grid(row=i, column=0, sticky="w", pady=3)
    pb = ttk.Progressbar(top, length=360, maximum=100, style=f"{sty}.Horizontal.TProgressbar")
    pb.grid(row=i, column=1, padx=10)
    lab = ttk.Label(top, text="—", style="Muted.TLabel", width=6)
    lab.grid(row=i, column=2)
    bars[k] = (pb, lab)
info = ttk.Frame(top, style="Card.TFrame")
info.grid(row=0, column=3, rowspan=3, padx=24)
lbl_kills = ttk.Label(info, text="0 kills", style="Big.TLabel")
lbl_kills.pack(anchor="w")
lbl_kph = ttk.Label(info, text="0 / hora", style="Muted.TLabel")
lbl_kph.pack(anchor="w")
lbl_zone = ttk.Label(info, text="", style="Card.TLabel")
lbl_zone.pack(anchor="w", pady=(8, 0))
conn = ttk.Frame(top, style="Card.TFrame")
conn.grid(row=3, column=0, columnspan=4, sticky="w", pady=(10, 0))
ttk.Label(conn, text="Conexión con el juego:", style="Muted.TLabel").pack(side="left", padx=(0, 10))
lamps = {}
for _k in ("win", "hp", "tg", "bar"):
    lamps[_k] = tk.Label(conn, text="● sin iniciar", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
    lamps[_k].pack(side="left", padx=(0, 14))


def set_lamp(k, ok, text):
    lamps[k].config(text="● " + text, fg=OK if ok is True else DANGER if ok is False else MUTED)

btns = ttk.Frame(tab_run)
btns.pack(fill="x", padx=6)
b_start = ttk.Button(btns, text="▶  Iniciar", style="Accent.TButton")
b_pause = ttk.Button(btns, text="⏸  Pausar / Reanudar")
b_stop = ttk.Button(btns, text="■  Detener", style="Danger.TButton")
for b in (b_start, b_pause, b_stop):
    b.pack(side="left", padx=(0, 8), pady=8)
ttk.Label(btns, text="F10 pausa · F12 parada · ratón a una esquina = emergencia", foreground=MUTED).pack(side="right")

log_box = tk.Text(tab_run, bg=PANEL2, fg=TEXT, insertbackground=TEXT, relief="flat", height=14,
                  font=("Consolas", 9), state="disabled", highlightthickness=1, highlightbackground=LINE)
log_box.pack(fill="both", expand=True, padx=6, pady=(0, 6))
log_box.tag_configure("warn", foreground="#ffd166")


def log(msg, tag=None):
    events.put(("log", f"[{time.strftime('%H:%M:%S')}] {msg}\n", tag))


def alert(msg):
    log("⚠ " + msg, "warn")
    events.put(("beep", None, None))


def on_status(brain):
    events.put(("status", brain, None))


# ===========================================================================
# Pestaña Personaje
# ===========================================================================
tab_char = ttk.Frame(nb)
nb.add(tab_char, text="🜂  Personaje")
c = card(tab_char, fill="x", padx=6, pady=6)
ch = cfg["character"]
v_level = tk.IntVar(value=ch["level"])
v_zone = tk.StringVar(value=ch["zone"])
v_power = tk.IntVar(value=ch["gear_power"])
v_auto = tk.BooleanVar(value=ch["auto_zone_check"])
v_pausez = tk.BooleanVar(value=ch["pause_on_zone_change"])
v_route = tk.BooleanVar(value=ch["auto_route"])
ttk.Label(c, text="Nivel", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=4)
ttk.Spinbox(c, from_=1, to=65, textvariable=v_level, width=6).grid(row=0, column=1, sticky="w", padx=8)
ttk.Label(c, text="Zona actual", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=4)
cb_zone = ttk.Combobox(c, textvariable=v_zone, values=[z["name"] for z in kn["zones"]], width=22)
cb_zone.grid(row=1, column=1, sticky="w", padx=8)      # editable: puedes escribir el nombre de tu zona
ttk.Label(c, text="Poder del equipo", style="Card.TLabel").grid(row=2, column=0, sticky="nw", pady=4)
pw = ttk.Frame(c, style="Card.TFrame")
pw.grid(row=2, column=1, sticky="w", padx=8)
for val, txt in ((0, "Normal"), (1, "Fuerte"), (2, "Muy fuerte (este servidor)")):
    ttk.Radiobutton(pw, text=txt, value=val, variable=v_power).pack(anchor="w")
ttk.Checkbutton(c, text="Comprobar si toca cambiar de zona", variable=v_auto).grid(row=3, column=0, columnspan=2, sticky="w", pady=2)
ttk.Checkbutton(c, text="Pausar y avisarme al cambiar de zona", variable=v_pausez).grid(row=4, column=0, columnspan=2, sticky="w")
ttk.Checkbutton(c, text="Ejecutar ruta grabada automáticamente (si existe)", variable=v_route).grid(row=5, column=0, columnspan=2, sticky="w")
lbl_rec = ttk.Label(c, text="", style="Big.TLabel")
lbl_rec.grid(row=6, column=0, columnspan=3, sticky="w", pady=(14, 2))
lbl_note = ttk.Label(c, text="", style="Muted.TLabel", wraplength=700)
lbl_note.grid(row=7, column=0, columnspan=3, sticky="w")


def refresh_rec(*_):
    try:
        rec = planner.recommend(int(v_level.get()), int(v_power.get()))
    except (tk.TclError, ValueError):
        return
    lbl_rec.config(text=f"Zona recomendada: {rec['name']}  (niv. {rec['min']}-{rec['max']})")
    lbl_note.config(text=rec.get("notas", "") + "  ·  " + kn["gear_power_bonus"][str(v_power.get())])


for v in (v_level, v_power):
    v.trace_add("write", refresh_rec)
refresh_rec()

# ===========================================================================
# Pestaña Habilidades
# ===========================================================================
tab_sk = ttk.Frame(nb)
nb.add(tab_sk, text="🏹  Rotación manual")
tv = ttk.Treeview(tab_sk, columns=("name", "key", "cd", "opener", "thp", "shp", "mp", "on"), show="headings", height=8)
for col, txt, w in (("name", "Habilidad", 210), ("key", "Tecla", 55), ("cd", "Enfr. (s)", 70), ("opener", "Apertura", 70),
                    ("thp", "Objetivo ≤ %", 90), ("shp", "Mi vida ≤ %", 90), ("mp", "Maná ≥ %", 80), ("on", "Activa", 60)):
    tv.heading(col, text=txt)
    tv.column(col, width=w, anchor="center" if col != "name" else "w")
tv.pack(fill="x", padx=6, pady=6)
ttk.Label(tab_sk, text="El orden es la prioridad: la de arriba se usa antes si cumple sus condiciones.",
          foreground=MUTED).pack(anchor="w", padx=8)


def refresh_skills():
    tv.delete(*tv.get_children())
    for s in cfg["skills"]:
        tv.insert("", "end", values=(s["name"], s["key"], s.get("cooldown", 0), "sí" if s.get("opener") else "",
                                     s.get("target_hp_max", 100), s.get("self_hp_max", 100), s.get("min_mp", 0),
                                     "sí" if s.get("enabled", True) else "no"))


form = card(tab_sk, fill="x", padx=6, pady=6)
fv = {k: tk.StringVar() for k in ("name", "key", "cooldown", "target_hp_max", "self_hp_max", "min_mp")}
fo, fe = tk.BooleanVar(), tk.BooleanVar(value=True)
for i, (k, txt) in enumerate((("name", "Nombre"), ("key", "Tecla"), ("cooldown", "Enfriamiento (s)"),
                              ("target_hp_max", "Objetivo ≤ %"), ("self_hp_max", "Mi vida ≤ %"), ("min_mp", "Maná mín. %"))):
    ttk.Label(form, text=txt, style="Card.TLabel").grid(row=i // 3 * 2, column=i % 3, sticky="w", padx=6)
    ttk.Entry(form, textvariable=fv[k], width=22 if k == "name" else 10).grid(row=i // 3 * 2 + 1, column=i % 3, sticky="w", padx=6, pady=(0, 6))
ttk.Checkbutton(form, text="Solo apertura", variable=fo).grid(row=4, column=0, sticky="w", padx=6)
ttk.Checkbutton(form, text="Activa", variable=fe).grid(row=4, column=1, sticky="w")


def skill_from_form():
    def num(k, d):
        try:
            return float(fv[k].get()) if fv[k].get() != "" else d
        except ValueError:
            return d
    s = {"name": fv["name"].get() or "Habilidad", "key": fv["key"].get(), "cooldown": num("cooldown", 0),
         "after_delay": 1.2, "enabled": fe.get()}
    if fo.get():
        s["opener"] = True
    for k in ("target_hp_max", "self_hp_max", "min_mp"):
        v = num(k, None)
        if v is not None:
            s[k] = v
    return s


def sel_idx():
    s = tv.selection()
    return tv.index(s[0]) if s else None


def on_select(_e=None):
    i = sel_idx()
    if i is None:
        return
    s = cfg["skills"][i]
    for k in fv:
        fv[k].set(s.get(k, ""))
    fo.set(bool(s.get("opener")))
    fe.set(s.get("enabled", True))


tv.bind("<<TreeviewSelect>>", on_select)


def add_skill():
    cfg["skills"].append(skill_from_form()); refresh_skills()


def upd_skill():
    i = sel_idx()
    if i is not None:
        keep = cfg["skills"][i].get("after_delay", 1.2)
        cfg["skills"][i] = skill_from_form(); cfg["skills"][i]["after_delay"] = keep; refresh_skills()


def del_skill():
    i = sel_idx()
    if i is not None:
        cfg["skills"].pop(i); refresh_skills()


def move_skill(d):
    i = sel_idx()
    if i is None or not 0 <= i + d < len(cfg["skills"]):
        return
    cfg["skills"][i], cfg["skills"][i + d] = cfg["skills"][i + d], cfg["skills"][i]
    refresh_skills(); tv.selection_set(tv.get_children()[i + d])


bar = ttk.Frame(tab_sk)
bar.pack(fill="x", padx=6)
for txt, fn in (("Añadir", add_skill), ("Actualizar", upd_skill), ("Borrar", del_skill),
                ("▲ Subir", lambda: move_skill(-1)), ("▼ Bajar", lambda: move_skill(1))):
    ttk.Button(bar, text=txt, command=fn).pack(side="left", padx=(0, 6))

pot = card(tab_sk, fill="x", padx=6, pady=10)
pv = {}
for r, (k, txt) in enumerate((("hp", "Poción de vida"), ("mp", "Poción de maná"))):
    p = cfg["potions"][k]
    pv[k] = (tk.StringVar(value=p["key"]), tk.StringVar(value=p["below"]), tk.StringVar(value=p["cooldown"]))
    ttk.Label(pot, text=txt, style="Card.TLabel", width=16).grid(row=r, column=0, sticky="w")
    for c_, (lab, var) in enumerate(zip(("tecla", "usar si < %", "enfr. s"), pv[k])):
        ttk.Label(pot, text=lab, style="Muted.TLabel").grid(row=r, column=1 + c_ * 2, padx=(10, 2))
        ttk.Entry(pot, textvariable=var, width=6).grid(row=r, column=2 + c_ * 2)
ttk.Label(pot, text="Con equipo fuerte el bot baja solo el umbral de la poción de vida (−10 % por nivel de poder).",
          style="Muted.TLabel").grid(row=2, column=0, columnspan=8, sticky="w", pady=(6, 0))

# ===========================================================================
# Pestaña Calibración
# ===========================================================================
tab_cal = ttk.Frame(nb)
nb.add(tab_cal, text="◎  Calibración")
cc = card(tab_cal, fill="x", padx=6, pady=6)
ttk.Label(cc, text="Para que el bot 'vea' el juego, marca cada barra. Pulsa el botón, y en 3 s coloca el ratón sobre la "
                   "esquina SUPERIOR IZQUIERDA de la barra; después otros 3 s sobre la INFERIOR DERECHA. "
                   "La barra debe estar llena (para el objetivo, tenlo seleccionado con vida completa).",
          style="Muted.TLabel", wraplength=780).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
cal_lbl = {}


def capture(key, label):
    import pyautogui
    pts = []

    def step(n):
        if n == 0:
            p = pyautogui.position(); pts.append((p.x, p.y))
            if len(pts) == 1:
                cal_lbl[key].config(text="Ahora la esquina INFERIOR DERECHA (3 s)…"); step(3)
            else:
                x1, y1 = pts[0]; x2, y2 = pts[1]
                reg = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
                if key in ("level_region", "target_name_region", "minimap_region"):
                    cfg["bars"][key] = reg
                elif key == "hotbar":
                    cfg["hotbar"]["region"] = reg
                else:
                    row = pyautogui.screenshot(region=(reg[0], (reg[1] + reg[3]) // 2, max(1, reg[2] - reg[0]), 1))
                    # color de relleno = el píxel más saturado de la fila (vale aunque la barra no esté llena)
                    px = max((row.getpixel((i, 0)) for i in range(row.width)), key=lambda p: max(p[:3]) - min(p[:3]))
                    cfg["bars"][key]["region"] = reg; cfg["bars"][key]["color"] = list(px[:3])
                refresh_cal()
            return
        cal_lbl[key].config(text=f"Colócate… {n}")
        root.after(1000, lambda: step(n - 1))

    cal_lbl[key].config(text="Esquina SUPERIOR IZQUIERDA (3 s)…")
    step(3)


for i, (k, txt) in enumerate((("hp", "Mi vida"), ("mp", "Mi maná"), ("target", "Vida del objetivo"),
                       ("xp", "Experiencia (barra)"), ("target_name_region", "Nombre del objetivo (OCR)"),
                       ("minimap_region", "Minimapa (opcional)"),
                       ("level_region", "Nivel (opcional, OCR)"))):
    ttk.Label(cc, text=txt, style="Card.TLabel", width=22).grid(row=i + 1, column=0, sticky="w", pady=4)
    ttk.Button(cc, text="Marcar", command=lambda k=k, t=txt: capture(k, t)).grid(row=i + 1, column=1, padx=8)
    cal_lbl[k] = ttk.Label(cc, text="", style="Muted.TLabel")
    cal_lbl[k].grid(row=i + 1, column=2, sticky="w")


def refresh_cal():
    for k, lab in cal_lbl.items():
        if k == "hotbar":
            lab.config(text=f"✔ {cfg['hotbar']['region']}" if cfg["hotbar"].get("region") else "sin marcar")
        elif k in ("level_region", "target_name_region", "minimap_region"):
            lab.config(text="✔ marcado" if cfg["bars"].get(k) else "sin marcar (necesita Tesseract OCR)")
        else:
            b = cfg["bars"][k]
            lab.config(text=f"✔ {b['region']} color {tuple(b['color'])}" if b.get("region") else "sin marcar")


def live_test():
    from engine import ScreenPerception
    perc = ScreenPerception(cfg)

    def go(n):
        s = perc.read()
        msg = lambda v: "—" if v is None else f"{v:.0%}"
        log(f"Lectura: vida {msg(s.hp)} · maná {msg(s.mp)} · objetivo {msg(s.thp)} · nivel {s.level or '—'} · xp {msg(s.xp)} · nombre {perc.read_name() or '—'}")
        if n > 0:
            root.after(700, lambda: go(n - 1))
    go(6)


ttk.Button(cc, text="Probar lectura (6 s, mira la pestaña Batalla)", command=live_test).grid(row=8, column=0, columnspan=3, sticky="w", pady=(14, 0))

# ===========================================================================
# Pestaña Auto-habilidades
# ===========================================================================
book = SkillBook.load(engine.LEARNED_PATH, log=log)
MODES = {"Solo mi rotación manual": "manual", "Mixto: mi rotación + habilidades aprendidas": "hybrid",
         "Totalmente automático (solo aprendidas)": "auto"}
tab_au = ttk.Frame(nb)
nb.add(tab_au, text="✦  Auto-habilidades")
hb_cfg, ac_cfg = cfg["hotbar"], cfg["auto_skills"]
v_auto_on = tk.BooleanVar(value=ac_cfg.get("enabled", True))
v_mode = tk.StringVar(value=[k for k, v in MODES.items() if v == ac_cfg.get("mode", "hybrid")][0])
v_cols, v_rows = tk.IntVar(value=hb_cfg["cols"]), tk.IntVar(value=hb_cfg["rows"])
INPUTS = {"Clic del ratón en cada hueco (no necesita saber las teclas)": "click",
          "Teclas (tengo que indicarlas abajo)": "keys"}
v_input = tk.StringVar(value=[k for k, v in INPUTS.items() if v == hb_cfg.get("input", "click")][0])
v_skip = tk.StringVar(value=",".join(str(i + 1) for i in hb_cfg.get("ignore_rows", [])))
v_keys, v_mods = tk.StringVar(value=",".join(hb_cfg["keys"])), tk.StringVar(value=",".join(hb_cfg.get("row_mods", [""])))
ac_ = card(tab_au, fill="x", padx=6, pady=6)
ttk.Checkbutton(ac_, text="Escanear mi barra de habilidades y usar las que aprenda (incluidas las nuevas)",
                variable=v_auto_on).grid(row=0, column=0, columnspan=4, sticky="w")
ttk.Combobox(ac_, textvariable=v_mode, values=list(MODES), width=48, state="readonly").grid(row=1, column=0, columnspan=4, sticky="w", pady=6)
ttk.Combobox(ac_, textvariable=v_input, values=list(INPUTS), width=48, state="readonly").grid(row=8, column=0, columnspan=4, sticky="w", pady=(10, 0))
ttk.Button(ac_, text="Marcar mi barra", command=lambda: capture("hotbar", "Barra")).grid(row=2, column=0, sticky="w")
cal_lbl["hotbar"] = ttk.Label(ac_, text="", style="Muted.TLabel")
cal_lbl["hotbar"].grid(row=2, column=1, columnspan=3, sticky="w", padx=8)
ttk.Label(ac_, text="Columnas", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=(8, 0))
ttk.Spinbox(ac_, from_=1, to=12, textvariable=v_cols, width=5).grid(row=3, column=1, sticky="w", pady=(8, 0))
ttk.Label(ac_, text="Filas", style="Card.TLabel").grid(row=3, column=2, sticky="e", pady=(8, 0))
ttk.Spinbox(ac_, from_=1, to=4, textvariable=v_rows, width=5).grid(row=3, column=3, sticky="w", pady=(8, 0))
ttk.Label(ac_, text="Teclas por columna", style="Card.TLabel").grid(row=4, column=0, sticky="w")
ttk.Entry(ac_, textvariable=v_keys, width=34).grid(row=4, column=1, columnspan=3, sticky="w")
ttk.Label(ac_, text="Modificador por fila (ej: ,shift)", style="Card.TLabel").grid(row=5, column=0, sticky="w")
ttk.Entry(ac_, textvariable=v_mods, width=34).grid(row=5, column=1, columnspan=3, sticky="w")
ttk.Label(ac_, text="Filas a ignorar (1 = arriba)", style="Card.TLabel").grid(row=6, column=0, sticky="w")
ttk.Entry(ac_, textvariable=v_skip, width=34).grid(row=6, column=1, columnspan=3, sticky="w")
ttk.Label(ac_, text="Pon aquí la fila de pergaminos/consumibles para que el bot no la use como habilidades.",
          style="Muted.TLabel").grid(row=7, column=0, columnspan=4, sticky="w")

lt = ttk.Treeview(tab_au, columns=("name", "key", "role", "dmg", "heal", "cd", "n", "st"), show="headings", height=8)
for col, txt, w in (("name", "Habilidad", 190), ("key", "Tecla", 70), ("role", "Rol", 90), ("dmg", "Daño %", 70),
                    ("heal", "Cura %", 70), ("cd", "Enfr. s", 70), ("n", "Pruebas", 70), ("st", "Estado", 110)):
    lt.heading(col, text=txt); lt.column(col, width=w, anchor="w" if col == "name" else "center")
lt.pack(fill="x", padx=6, pady=4)
ROLE_TXT = {"unknown": "por probar", "damage": "daño", "heal": "curación", "buff": "buff",
            "utility": "utilidad (no se usa)", "ignore": "ignorar"}


def refresh_learned():
    sel = lt.selection()
    lt.delete(*lt.get_children())
    for e in book.entries.values():
        live = book.live.get(e["id"])
        st_ = "no está en la barra" if live is None else ("lista" if live["ready"] else "enfriando")
        lt.insert("", "end", iid=e["id"], values=(e["name"], e["key"], ROLE_TXT.get(book.role(e), book.role(e)),
                  f"{e['avg_drop']:.1f}", f"{e['avg_heal']:.1f}", e["cooldown"] or "—", e["n"], st_))
    if sel and lt.exists(sel[0]):
        lt.selection_set(sel[0])


def set_role(r):
    for iid in lt.selection():
        book.entries[iid]["role_user"] = r
    book.dirty = True; refresh_learned()


rb = ttk.Frame(tab_au); rb.pack(fill="x", padx=6)
ttk.Label(rb, text="Forzar rol:", foreground=MUTED).pack(side="left", padx=(0, 6))
for txt, r in (("Daño", "damage"), ("Curación", "heal"), ("Buff", "buff"), ("Ignorar", "ignore"), ("Automático", "auto")):
    ttk.Button(rb, text=txt, command=lambda r=r: set_role(r)).pack(side="left", padx=(0, 6))
v_name = tk.StringVar()
ttk.Entry(rb, textvariable=v_name, width=20).pack(side="left", padx=(14, 4))


def rename():
    for iid in lt.selection():
        if v_name.get():
            book.entries[iid]["name"] = v_name.get()
    book.dirty = True; refresh_learned()


ttk.Button(rb, text="Renombrar", command=rename).pack(side="left")


def scan_now():
    try:
        collect()
        from engine import ScreenPerception
        slots = ScreenPerception(cfg)._slots()
    except Exception as ex:  # noqa: BLE001
        log(f"No se pudo escanear: {ex}"); return
    if slots is None:
        log("Primero marca tu barra de habilidades."); return
    book.excluded = engine.excluded_keys(cfg)
    new = book.update(slots, time.time())
    log(f"Escaneo: {sum(s.occupied for s in slots)} huecos con habilidad, {len(new)} nuevas")
    book.save(engine.LEARNED_PATH); refresh_learned()


def forget():
    if messagebox.askyesno("Olvidar", "¿Borrar todo lo aprendido de tus habilidades?"):
        book.forget(); refresh_learned()


bb = ttk.Frame(tab_au); bb.pack(fill="x", padx=6, pady=8)
ttk.Button(bb, text="Escanear ahora", style="Accent.TButton", command=scan_now).pack(side="left", padx=(0, 8))
ttk.Button(bb, text="Olvidar lo aprendido", command=forget).pack(side="left")
ttk.Label(tab_au, wraplength=820, foreground=MUTED, text=(
    "Cómo funciona: el bot reconoce cada icono de tu barra, y cuando una habilidad está lista la prueba en combate "
    "(solo con tu vida ≥ 60 % y el objetivo con vida). Mide cuánto baja la vida del enemigo respecto al ataque básico "
    "(→ daño), si te cura (→ curación) o nada (→ utilidad: no se usa sola). Las habilidades nuevas que pongas en la "
    "barra se detectan y se prueban solas. Corrige a mano con 'Forzar rol' si se equivoca (p. ej. un buff o un DoT). "
    "No toca las teclas de pociones ni de tu rotación manual (salvo en modo automático).")).pack(anchor="w", padx=8)

# ===========================================================================
# Pestaña Monstruos
# ===========================================================================
tab_mo = ttk.Frame(nb)
nb.add(tab_mo, text="🐺  Monstruos")
mc_ = card(tab_mo, fill="x", padx=6, pady=6)
v_mon_on = tk.BooleanVar(value=cfg["monsters"].get("enabled", True))
v_autospot = tk.BooleanVar(value=cfg["monsters"].get("auto_spot", True))
v_keep = tk.IntVar(value=int(cfg["monsters"].get("keep_ratio", 0.6) * 100))
v_danger = tk.IntVar(value=int(cfg["monsters"].get("max_danger", 80)))
ttk.Checkbutton(mc_, text="Analizar monstruos y descartar los poco rentables o peligrosos", variable=v_mon_on).grid(row=0, column=0, columnspan=4, sticky="w")
ttk.Checkbutton(mc_, text="Elegir solo el mejor punto de farmeo de la zona (por XP/min)", variable=v_autospot).grid(row=1, column=0, columnspan=4, sticky="w")
ttk.Label(mc_, text="Descartar si rinde menos del", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=4)
ttk.Spinbox(mc_, from_=10, to=100, textvariable=v_keep, width=5).grid(row=2, column=1)
ttk.Label(mc_, text="% del mejor      Descartar si me quita más del", style="Card.TLabel").grid(row=2, column=2)
ttk.Spinbox(mc_, from_=20, to=100, textvariable=v_danger, width=5).grid(row=2, column=3)
ttk.Label(mc_, text="% de vida", style="Card.TLabel").grid(row=2, column=4, padx=4)
mv = ttk.Treeview(tab_mo, columns=("name", "n", "xp", "ttk", "hp", "score", "st", "pref"), show="headings", height=9)
for col, txt, w in (("name", "Monstruo", 170), ("n", "Muertes", 70), ("xp", "XP % / muerte", 100), ("ttk", "Tiempo (s)", 80),
                    ("hp", "Vida perdida %", 100), ("score", "XP % / min", 90), ("st", "Decisión", 90), ("pref", "Tu regla", 80)):
    mv.heading(col, text=txt); mv.column(col, width=w, anchor="w" if col == "name" else "center")
mv.pack(fill="x", padx=6, pady=4)
ST_TXT = {"learn": "aprendiendo", "farm": "farmear", "avoid": "evitar"}


def refresh_monsters():
    sel = mv.selection()
    mv.delete(*mv.get_children())
    mcfg = cfg["monsters"]
    rows = sorted(db.monsters.items(), key=lambda kv: -db.score(kv[1]))
    for name, m in rows:
        st_ = db.status(name, mcfg.get("min_samples", 3), mcfg.get("keep_ratio", 0.6), mcfg.get("max_danger", 80))
        mv.insert("", "end", iid=name, values=(name, m["n"], f"{m['xp']:.2f}", f"{m['ttk']:.0f}", f"{m['hp_lost']:.0f}",
                  f"{db.score(m):.2f}", ST_TXT[st_], {"auto": "auto", "farm": "farmear", "avoid": "evitar"}[m["pref"]]))
    if sel and mv.exists(sel[0]):
        mv.selection_set(sel[0])


def set_pref(p):
    for iid in mv.selection():
        db.monsters[iid]["pref"] = p
    db.dirty = True; refresh_monsters()


def forget_monsters():
    if messagebox.askyesno("Olvidar", "¿Borrar todo lo aprendido de monstruos y puntos de farmeo?"):
        db.forget(); refresh_monsters(); refresh_spots()


mb = ttk.Frame(tab_mo); mb.pack(fill="x", padx=6)
for txt, p in (("Farmear siempre", "farm"), ("Evitar siempre", "avoid"), ("Automático", "auto")):
    ttk.Button(mb, text=txt, command=lambda p=p: set_pref(p)).pack(side="left", padx=(0, 6))
ttk.Button(mb, text="Olvidar todo", command=forget_monsters).pack(side="left", padx=(14, 0))
ttk.Label(tab_mo, wraplength=820, foreground=MUTED, text=(
    "Cómo funciona: tras cada muerte el bot mide cuánta barra de experiencia has ganado, cuánto tardó y cuánta vida te costó. "
    "Con eso calcula la rentabilidad (XP por minuto) de cada monstruo. Los primeros 3 de cada tipo los pelea para aprender; "
    "después evita los que rinden menos del porcentaje que indiques respecto al mejor, o te quitan demasiada vida. "
    "Necesita calibrar la barra de experiencia y la región del nombre del objetivo (lectura por OCR: instala Tesseract). "
    "Sin el nombre no puede distinguir monstruos, pero sí mide los puntos de farmeo.")).pack(anchor="w", padx=8, pady=6)

# ===========================================================================
# Pestaña Rutas
# ===========================================================================
tab_rt = ttk.Frame(nb)
nb.add(tab_rt, text="🗺  Zonas y rutas")
rc = card(tab_rt, fill="x", padx=6, pady=6)
ttk.Label(rc, text="Graba cómo ir de una zona a otra (teclas de movimiento) y el bot la repetirá cuando toque cambiar de zona. "
                   "Para grabar: pulsa 'Grabar', ve al juego, haz el recorrido y pulsa F9 para terminar.",
          style="Muted.TLabel", wraplength=780).pack(anchor="w")
zn = [z["name"] for z in kn["zones"]]
rf, rt_ = tk.StringVar(value=zn[0]), tk.StringVar(value=zn[1])
row = ttk.Frame(rc, style="Card.TFrame"); row.pack(anchor="w", pady=10)
cb_from = ttk.Combobox(row, textvariable=rf, values=zn, width=18)
cb_from.pack(side="left")
ttk.Label(row, text="  →  ", style="Card.TLabel").pack(side="left")
cb_to = ttk.Combobox(row, textvariable=rt_, values=zn, width=18)
cb_to.pack(side="left")


def do_record():
    name = f"{rf.get()}->{rt_.get()}"
    log(f"Grabando ruta {name}… pulsa F9 para terminar")

    def work():
        steps = engine.record_route()
        routes = load_json(engine.ROUTES_PATH, {}); routes[name] = steps
        save_json(engine.ROUTES_PATH, routes)
        log(f"Ruta {name} guardada ({len(steps)} pulsaciones)")
    threading.Thread(target=work, daemon=True).start()


def do_play():
    name = f"{rf.get()}->{rt_.get()}"
    steps = load_json(engine.ROUTES_PATH, {}).get(name)
    if not steps:
        messagebox.showinfo("Ruta", "No hay ruta grabada para ese trayecto."); return
    log(f"Reproduciendo {name} en 5 s…")
    threading.Thread(target=lambda: (time.sleep(5), engine.play_route(steps, engine.Actuator())), daemon=True).start()


ttk.Button(row, text="● Grabar", command=do_record).pack(side="left", padx=(14, 6))
ttk.Button(row, text="▶ Probar", command=do_play).pack(side="left")

# ---- Puntos de farmeo y plan (en la misma pestaña) ---------------------------
sp_card = card(tab_rt, fill="x", padx=6, pady=6)
ttk.Label(sp_card, text="Puntos de farmeo: sitios concretos de una zona (un claro con monstruos). Graba una PATRULLA para cada uno "
                        "(un recorrido corto que se repite cuando no hay enemigos) y rutas entre ellos arriba (origen → destino). "
                        "El bot mide la XP/min de cada punto y se queda en el mejor.",
          style="Muted.TLabel", wraplength=780).pack(anchor="w")
spv = ttk.Treeview(sp_card, columns=("name", "zone", "rate", "min", "kills", "here"), show="headings", height=4)
for col, txt, w in (("name", "Punto", 180), ("zone", "Zona", 110), ("rate", "XP % / min", 90), ("min", "Minutos", 70),
                    ("kills", "Muertes", 70), ("here", "Estoy aquí", 80)):
    spv.heading(col, text=txt); spv.column(col, width=w, anchor="w" if col == "name" else "center")
spv.pack(fill="x", pady=6)
v_sp_name, v_sp_zone = tk.StringVar(), tk.StringVar(value=zn[0])
spr = ttk.Frame(sp_card, style="Card.TFrame"); spr.pack(anchor="w")
ttk.Entry(spr, textvariable=v_sp_name, width=22).pack(side="left")
cb_spzone = ttk.Combobox(spr, textvariable=v_sp_zone, values=zn, width=16)
cb_spzone.pack(side="left", padx=6)


def route_values():
    vals = zn + [sp["name"] for sp in cfg["spots"]]
    cb_from.config(values=vals); cb_to.config(values=vals)


def refresh_spots():
    sel = spv.selection()
    spv.delete(*spv.get_children())
    for sp in cfg["spots"]:
        st_ = db.spots.get(sp["name"], {})
        rate = db.spot_rate(sp["name"])
        spv.insert("", "end", iid=sp["name"], values=(sp["name"], sp["zone"], f"{rate:.2f}" if rate else "—",
                   f"{st_.get('seconds', 0) / 60:.0f}", st_.get("kills", 0), "●" if cfg["character"].get("spot") == sp["name"] else ""))
    if sel and spv.exists(sel[0]):
        spv.selection_set(sel[0])
    route_values()


def add_spot():
    n = v_sp_name.get().strip()
    if n and not any(sp["name"] == n for sp in cfg["spots"]):
        cfg["spots"].append({"name": n, "zone": v_sp_zone.get()}); refresh_spots()


def del_spot():
    for iid in spv.selection():
        cfg["spots"][:] = [sp for sp in cfg["spots"] if sp["name"] != iid]
    refresh_spots()


def here_spot():
    for iid in spv.selection():
        cfg["character"]["spot"] = iid
        sp = next(sp for sp in cfg["spots"] if sp["name"] == iid)
        cfg["character"]["zone"] = sp["zone"]; v_zone.set(sp["zone"])
    refresh_spots()


def record_patrol():
    for iid in spv.selection():
        rf.set("patrol:" + iid); rt_.set("")
        name = "patrol:" + iid
        log(f"Grabando patrulla {iid}… pulsa F9 para terminar")

        def work(name=name):
            steps = engine.record_route()
            routes = load_json(engine.ROUTES_PATH, {}); routes[name] = steps
            save_json(engine.ROUTES_PATH, routes)
            log(f"Patrulla {name} guardada ({len(steps)} pulsaciones)")
        threading.Thread(target=work, daemon=True).start()


ttk.Button(spr, text="Añadir", command=add_spot).pack(side="left")
ttk.Button(spr, text="Borrar", command=del_spot).pack(side="left", padx=6)
ttk.Button(spr, text="Estoy aquí", command=here_spot).pack(side="left")
ttk.Button(spr, text="● Grabar patrulla", command=record_patrol).pack(side="left", padx=6)

pl_card = card(tab_rt, fill="x", padx=6, pady=6)
ttk.Label(pl_card, text="Plan de farmeo (opcional): a partir de qué nivel (contando el bonus de equipo) debe ir a cada zona. "
                        "Vacío = usa la tabla de la pestaña Conocimiento.", style="Muted.TLabel", wraplength=780).pack(anchor="w")
plv = ttk.Treeview(pl_card, columns=("lv", "zone"), show="headings", height=3)
plv.heading("lv", text="Desde nivel"); plv.heading("zone", text="Zona")
plv.column("lv", width=100, anchor="center"); plv.column("zone", width=160, anchor="w")
plv.pack(anchor="w", pady=6)
v_pl_lv, v_pl_zone = tk.IntVar(value=10), tk.StringVar(value=zn[1])
plr = ttk.Frame(pl_card, style="Card.TFrame"); plr.pack(anchor="w")
ttk.Spinbox(plr, from_=1, to=65, textvariable=v_pl_lv, width=5).pack(side="left")
cb_plzone = ttk.Combobox(plr, textvariable=v_pl_zone, values=zn, width=16)
cb_plzone.pack(side="left", padx=6)


def refresh_plan():
    plv.delete(*plv.get_children())
    for i, p in enumerate(sorted(cfg["farm_plan"], key=lambda p: p["from_level"])):
        plv.insert("", "end", iid=str(i), values=(p["from_level"], p["zone"]))


def add_plan():
    try:
        cfg["farm_plan"].append({"from_level": int(v_pl_lv.get()), "zone": v_pl_zone.get()})
    except tk.TclError:
        return
    refresh_plan()


def del_plan():
    srt = sorted(cfg["farm_plan"], key=lambda p: p["from_level"])
    for iid in plv.selection():
        srt[int(iid)] = None
    cfg["farm_plan"][:] = [p for p in srt if p]
    refresh_plan()


ttk.Button(plr, text="Añadir", command=add_plan).pack(side="left")
ttk.Button(plr, text="Borrar", command=del_plan).pack(side="left", padx=6)

# ===========================================================================
# Pestaña Archivos del juego
# ===========================================================================
tab_fi = ttk.Frame(nb)
nb.add(tab_fi, text="📂  Archivos del juego")
fc = card(tab_fi, fill="x", padx=6, pady=6)
v_gdir = tk.StringVar(value=cfg.get("game_dir", ""))
ttk.Label(fc, text="Lee los ARCHIVOS de tu carpeta de Aion (solo lectura): nombres y niveles de monstruos, habilidades y textos. "
                   "No lee la memoria del juego ni la red (eso lo detecta el anti-trampas). Con los niveles, el bot descarta monstruos "
                   "muy por debajo o por encima de tu nivel.", style="Muted.TLabel", wraplength=800).grid(row=0, column=0, columnspan=5, sticky="w")
ttk.Entry(fc, textvariable=v_gdir, width=70).grid(row=1, column=0, columnspan=4, sticky="we", pady=8)
ftext = tk.Text(tab_fi, bg=PANEL2, fg=TEXT, relief="flat", height=16, font=("Segoe UI", 9), state="disabled",
                highlightthickness=1, highlightbackground=LINE, wrap="word")
for _t, _c in (("ok", OK), ("warn", "#ffd166"), ("bad", DANGER)):
    ftext.tag_configure(_t, foreground=_c)
last_inv = [None]
last_lines = [[]]


def show_files(lines, extra=None):
    if extra and extra[0] == "set":
        v_gdir.set(extra[1]); cfg["game_dir"] = extra[1]
    if extra and extra[0] == "inv":
        last_inv[0] = extra[1]
    last_lines[0] = lines
    ftext.config(state="normal"); ftext.delete("1.0", "end")
    for lvl, txt in lines:
        ftext.insert("end", ("✔ " if lvl == "ok" else "⚠ " if lvl == "warn" else "✖ ") + txt + "\n\n", lvl)
    ftext.config(state="disabled")


def _run(fn):
    def work():
        try:
            fn()
        except Exception as ex:  # noqa: BLE001
            events.put(("files", [("bad", f"Error: {ex}")], None))
    threading.Thread(target=work, daemon=True).start()


def do_find():
    events.put(("files", [("ok", "Buscando Aion en tus discos (puede tardar hasta 30 s)…")], None))

    def fn():
        running = gamescan.running_install()
        found = [running] if running else gamescan.find_install()
        if not found:
            events.put(("files", [("warn", "No lo encuentro automáticamente: pulsa 'Elegir carpeta…' y selecciona la carpeta de Aion "
                                           "(la que contiene bin32 o bin64).")], None)); return
        events.put(("files", [("ok", f"Encontrado: {gamescan.anon(p)}") for p in found], ("set", str(found[0]))))
    _run(fn)


def do_choose():
    d = filedialog.askdirectory(title="Carpeta de instalación de Aion")
    if d:
        v_gdir.set(d); cfg["game_dir"] = d


def do_scan():
    d = v_gdir.get().strip()
    if not d or not Path(d).exists():
        messagebox.showinfo("Archivos", "Primero busca o elige la carpeta de Aion."); return
    events.put(("files", [("ok", "Escaneando… (puede tardar un minuto)")], None))

    def fn():
        inv = gamescan.inventory(d, log=lambda m: None)
        lines = gamescan.report_lines(inv)
        (engine.BASE / "gamescan_report.json").write_text(json.dumps(inv, indent=1, ensure_ascii=False), encoding="utf-8")
        lines.append(("ok", "Informe guardado en gamescan_report.json (sin tu nombre de usuario). Si algo no se lee, "
                            "pulsa 'Copiar informe' y pégalo en el chat para que se ajuste el lector."))
        events.put(("files", lines, ("inv", inv)))
    _run(fn)


def do_extract():
    d = v_gdir.get().strip()
    if not d or not Path(d).exists():
        messagebox.showinfo("Archivos", "Primero busca o elige la carpeta de Aion."); return
    events.put(("files", [("ok", "Extrayendo XML de los .pak legibles…")], None))

    def fn():
        out = engine.BASE / "game_extract"
        n = gamescan.extract_paks(d, out, log=lambda m: None)
        if not n:
            events.put(("files", [("warn", "Ningún .pak se pudo abrir como ZIP (están cifrados). Extráelos con una herramienta de la "
                                           "comunidad (p. ej. AION-Encdec), y usa 'Importar carpeta de XML extraídos'.")], None)); return
        data = gamescan.import_dir(out, log=lambda m: None)
        events.put(("files", [("ok", f"{n} XML extraídos."), ("ok" if data["monsters"] else "warn",
                    f"Importados {len(data['monsters'])} monstruos y {len(data['skills'])} habilidades "
                    f"(se usarán al iniciar el bot).")] + [("ok", f"{f['file']}: {f['records']} registros") for f in data["files"]], None))
    _run(fn)


def do_stage():
    d = v_gdir.get().strip()
    if not d or not Path(d).exists():
        messagebox.showinfo("Archivos", "Primero busca o elige la carpeta de Aion."); return
    events.put(("files", [("ok", "Copiando los .pak importantes (npcs, skills, world, textos)…")], None))

    def fn():
        work = engine.BASE / "game_work"
        names = gamescan.stage_paks(d, work, log=lambda m: None)
        if not names:
            events.put(("files", [("warn", "No encontré .pak de npcs/skills/world/textos en esa carpeta.")], None)); return
        events.put(("files", [("ok", f"{len(names)} archivos COPIADOS (el juego no se toca) a {gamescan.anon(work / 'PAK')}:")] +
                    [("ok", n) for n in names[:12]] +
                    [("ok", "Siguiente paso: abre esa carpeta con AION-Encdec (Descomprimir y Decodificar) y luego pulsa "
                            "'Importar XML ya extraídos…' eligiendo la carpeta game_work\\PAK. Instrucciones en el README.")], None))
    _run(fn)


def do_import():
    d = filedialog.askdirectory(title="Carpeta con los XML ya extraídos")
    if not d:
        return

    def fn():
        data = gamescan.import_dir(d, log=lambda m: None)
        events.put(("files", [("ok" if data["monsters"] else "warn",
                    f"Importados {len(data['monsters'])} monstruos y {len(data['skills'])} habilidades.")] +
                    [("ok", f"{f['file']}: {f['records']} registros") for f in data["files"]] +
                    ([] if data["files"] else [("warn", "No encontré XML de NPC o habilidades legibles en esa carpeta.")]), None))
    _run(fn)


def do_copy():
    txt = "\n".join(t for _, t in last_lines[0])
    if last_inv[0]:
        txt += "\n\n" + json.dumps(last_inv[0], ensure_ascii=False)[:6000]
    root.clipboard_clear(); root.clipboard_append(txt)
    lbl_vs.config(text="Informe copiado al portapapeles")


fbar = ttk.Frame(fc, style="Card.TFrame")
fbar.grid(row=2, column=0, columnspan=5, sticky="w")
for _txt, _fn in (("Buscar Aion en mi PC", do_find), ("Elegir carpeta…", do_choose), ("Escanear", do_scan),
                  ("Extraer .pak legibles e importar", do_extract), ("Copiar .pak importantes a una carpeta de trabajo", do_stage),
                  ("Importar XML ya extraídos…", do_import), ("Copiar informe", do_copy)):
    ttk.Button(fbar, text=_txt, command=_fn).pack(side="left", padx=(0, 6), pady=(0, 4))
ftext.pack(fill="both", expand=True, padx=6, pady=6)

# ===========================================================================
# Pestaña Diagnóstico
# ===========================================================================
tab_dg = ttk.Frame(nb)
nb.add(tab_dg, text="🔧  Diagnóstico")
dc = card(tab_dg, fill="x", padx=6, pady=6)
v_dsecs = tk.IntVar(value=6)
ttk.Label(dc, text="Prueba si el personaje se mueve cuando el bot pulsa teclas. Ponte en un sitio SEGURO (sin enemigos), con Aion en "
                   "primer plano. El bot mantendrá 'W' un segundo y medio con dos métodos distintos, comprueba si la imagen cambia y "
                   "vuelve atrás con 'S'. Si solo funciona uno, lo deja activado solo.",
          style="Muted.TLabel", wraplength=800).grid(row=0, column=0, columnspan=5, sticky="w")
b_diag = ttk.Button(dc, text="▶  Probar movimiento en", style="Accent.TButton")
b_diag.grid(row=1, column=0, pady=8, sticky="w")
ttk.Spinbox(dc, from_=3, to=20, textvariable=v_dsecs, width=4).grid(row=1, column=1, padx=4)
ttk.Label(dc, text="segundos", style="Card.TLabel").grid(row=1, column=2)
lbl_dg = ttk.Label(dc, text="", style="Muted.TLabel")
lbl_dg.grid(row=2, column=0, columnspan=5, sticky="w")
v_explore = tk.BooleanVar(value=cfg["explore"].get("enabled", True))
v_turn = tk.DoubleVar(value=cfg["explore"].get("turn_seconds", 0.45))
ec = card(tab_dg, fill="x", padx=6, pady=4)
ttk.Checkbutton(ec, text="Explorar solo cuando no veo monstruos: girar buscando (Tab), caminar y salir si se atasca",
                variable=v_explore).grid(row=0, column=0, columnspan=4, sticky="w")
ttk.Label(ec, text="Segundos por giro de 45°", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=6)
ttk.Spinbox(ec, from_=0.1, to=2.0, increment=0.05, textvariable=v_turn, width=6).grid(row=1, column=1, padx=8)
b_turn = ttk.Button(ec, text="Probar vuelta completa")
b_turn.grid(row=1, column=2, padx=6)
ttk.Label(ec, text="Ajusta los segundos hasta que 8 giros den una vuelta entera (empieza en un sitio seguro).",
          style="Muted.TLabel").grid(row=2, column=0, columnspan=4, sticky="w")


def turn_worker():
    try:
        act = engine.Actuator(cfg["behavior"].get("input_mode", "pyautogui"))
        n, secs = int(cfg["explore"].get("sweeps_per_circle", 8)), float(cfg["explore"]["turn_seconds"])
        for _ in range(n):
            act.down(cfg["explore"]["turn_keys"][0]); time.sleep(secs); act.up(cfg["explore"]["turn_keys"][0])
            time.sleep(0.8)
        events.put(("diag", [("ok", f"Hice {n} giros de {secs} s. ¿Diste una vuelta completa? Si te pasaste, baja los segundos; "
                                    "si te quedaste corto, sube.")], None))
    except Exception as ex:  # noqa: BLE001
        events.put(("diag", [("bad", f"Error: {ex}")], None))


def turn_test(n=None):
    n = 5 if n is None else n
    if n > 0:
        lbl_dg.config(text=f"Pon Aion en primer plano, en un sitio seguro… giro en {n}")
        root.after(1000, lambda: turn_test(n - 1))
        return
    collect_safe()
    root.withdraw(); root.update()
    threading.Thread(target=turn_worker, daemon=True).start()


b_turn.config(command=turn_test)
dtext = tk.Text(tab_dg, bg=PANEL2, fg=TEXT, relief="flat", height=14, font=("Segoe UI", 10), state="disabled",
                highlightthickness=1, highlightbackground=LINE, wrap="word")
dtext.pack(fill="both", expand=True, padx=6, pady=6)
dtext.tag_configure("ok", foreground=OK)
dtext.tag_configure("warn", foreground="#ffd166")
dtext.tag_configure("bad", foreground=DANGER)


def diag_worker(title):
    try:
        import pyautogui
        w, h = pyautogui.size()
        reg = (int(w * .25), int(h * .2), int(w * .5), int(h * .5))

        def hold(mode, key, secs):
            if mode == "scancode":
                inputs.key_down(key); time.sleep(secs); inputs.key_up(key)
            else:
                pyautogui.keyDown(key); time.sleep(secs); pyautogui.keyUp(key)
        res = diagnostics.movement_test(lambda: pyautogui.screenshot(region=reg), hold)
        admin = diagnostics.is_admin()
        mode, adv = diagnostics.advice(res, title, admin)
        lines = [("ok" if admin else "warn", "El bot se ejecuta como administrador." if admin else
                  ("El bot NO se ejecuta como administrador." if admin is False else "No puedo saber si es administrador.")),
                 ("ok" if title else "warn", f"Ventana activa: «{title}»" if title else "No puedo saber la ventana activa."),
                 ("ok", f"Ruido de la imagen sin pulsar nada: {res['noise']:.1f}"),
                 ("ok" if res["pyautogui"] else "warn", "Método normal: " + ("el personaje SE MOVIÓ" if res["pyautogui"] else "no se movió")),
                 ("ok" if res["scancode"] else "warn", "Método scancode: " + ("sin soporte (solo Windows)" if res["scancode"] is None else
                                                                          "el personaje SE MOVIÓ" if res["scancode"] else "no se movió"))]
        events.put(("diag", lines + adv, mode))
    except Exception as ex:  # noqa: BLE001
        events.put(("diag", [("bad", f"Error en la prueba: {ex}")], None))


def diag(n=None):
    n = int(v_dsecs.get()) if n is None else n
    if n > 0:
        lbl_dg.config(text=f"Pon Aion en primer plano, en un sitio seguro… empiezo en {n}")
        root.after(1000, lambda: diag(n - 1))
        return
    title = vision.foreground_title()
    root.withdraw(); root.update()
    threading.Thread(target=diag_worker, args=(title,), daemon=True).start()


def show_diag(lines, mode):
    root.deiconify()
    dtext.config(state="normal"); dtext.delete("1.0", "end")
    for lvl, txt in lines:
        dtext.insert("end", ("✔ " if lvl == "ok" else "⚠ " if lvl == "warn" else "✖ ") + txt + "\n\n", lvl)
    dtext.config(state="disabled")
    if mode:
        cfg["behavior"]["input_mode"] = mode
        collect_safe(); save_cfg()
    lbl_dg.config(text=f"Prueba hecha a las {time.strftime('%H:%M:%S')}")


b_diag.config(command=diag)

# ===========================================================================
# Pestaña Vista (lo que ve el bot)
# ===========================================================================
tab_vi = ttk.Frame(nb)
nb.add(tab_vi, text="👁  Vista")
vc = card(tab_vi, fill="x", padx=6, pady=6)
v_secs = tk.IntVar(value=5)
last_title = [None]
ttk.Label(vc, text="El bot NO se conecta al juego: mira la pantalla y pulsa teclas en la ventana activa. Pulsa 'Capturar', pon Aion en "
                   "primer plano (esta ventana se oculta sola) y verás tu pantalla con lo que el bot detecta dibujado encima.",
          style="Muted.TLabel", wraplength=800).grid(row=0, column=0, columnspan=6, sticky="w")
b_snap = ttk.Button(vc, text="📸  Capturar en", style="Accent.TButton")
b_snap.grid(row=1, column=0, pady=8, sticky="w")
ttk.Spinbox(vc, from_=2, to=15, textvariable=v_secs, width=4).grid(row=1, column=1, padx=4)
ttk.Label(vc, text="segundos", style="Card.TLabel").grid(row=1, column=2)
b_win = ttk.Button(vc, text="Usar esta ventana como la del juego")
b_win.grid(row=1, column=3, padx=14)
b_auto = ttk.Button(vc, text="✨  Configurar automáticamente", command=lambda: auto_config())
b_auto.grid(row=1, column=4, padx=6)
lbl_vs = ttk.Label(vc, text="", style="Muted.TLabel")
lbl_vs.grid(row=2, column=0, columnspan=6, sticky="w")
vimg = tk.Label(tab_vi, bg=BG)
vimg.pack(padx=6, pady=4)
vrep = tk.Text(tab_vi, bg=PANEL2, fg=TEXT, relief="flat", height=9, font=("Segoe UI", 9), state="disabled",
               highlightthickness=1, highlightbackground=LINE)
vrep.pack(fill="x", padx=6, pady=(0, 6))
vrep.tag_configure("ok", foreground=OK)
vrep.tag_configure("warn", foreground="#ffd166")
vrep.tag_configure("bad", foreground=DANGER)
vphoto = [None]


def show_report(lines):
    vrep.config(state="normal"); vrep.delete("1.0", "end")
    for lvl, txt in lines:
        vrep.insert("end", ("✔ " if lvl == "ok" else "⚠ " if lvl == "warn" else "✖ ") + txt + "\n", lvl)
    vrep.config(state="disabled")


last_shot = [None]


def render_shot(shot, title, pre=()):
    from PIL import ImageTk
    collect_safe()
    img, rep = vision.render_overlay(shot, cfg, book)
    rep = list(pre) + rep
    try:
        import pyautogui
        if pyautogui.size() != shot.size:
            rep.append(("warn", f"La captura ({shot.width}x{shot.height}) no coincide con la pantalla {tuple(pyautogui.size())}: "
                                "pon la escala de Windows al 100 % o las coordenadas saldrán desplazadas."))
    except Exception:  # noqa: BLE001
        pass
    gw = cfg["behavior"].get("game_window", "")
    rep.append(("ok" if title else "warn", f"Ventana activa al capturar: «{title}»" if title else "No puedo saber la ventana activa (solo Windows)."))
    rep.append(("ok" if gw else "warn", f"Vigilancia de ventana: «{gw}»" if gw else
                "Vigilancia de ventana desactivada: si Aion no está en primer plano, el bot escribirá en otra aplicación. "
                "Pon Aion delante, captura y pulsa 'Usar esta ventana como la del juego'."))
    last_title[0] = title
    w = 880
    vphoto[0] = ImageTk.PhotoImage(img.resize((w, max(1, int(img.height * w / img.width)))))
    vimg.config(image=vphoto[0])
    show_report(rep)
    lbl_vs.config(text=f"Captura hecha a las {time.strftime('%H:%M:%S')}")


def finish_snap(title):
    try:
        import pyautogui
        shot = pyautogui.screenshot()
    except Exception as ex:  # noqa: BLE001
        root.deiconify(); lbl_vs.config(text=f"No se pudo capturar: {ex}"); return
    root.deiconify()
    last_shot[0] = shot
    render_shot(shot, title)


def auto_config():
    shot = last_shot[0]
    if shot is None:
        messagebox.showinfo("Autoconfiguración", "Primero pulsa 'Capturar' con Aion en primer plano, con vida y maná llenos, "
                                                 "un enemigo seleccionado con vida llena y la barra de habilidades visible.")
        return
    res = autoconfig.detect(shot)
    autoconfig.apply(cfg, res)
    if res["hotbar"]:
        v_cols.set(res["hotbar"]["cols"]); v_rows.set(res["hotbar"]["rows"])
    save_cfg(); refresh_cal()
    render_shot(shot, last_title[0], pre=res["notes"])


def collect_safe():
    try:
        collect()
    except (ValueError, tk.TclError):
        pass


def snap(n=None):
    n = int(v_secs.get()) if n is None else n
    if n > 0:
        lbl_vs.config(text=f"Pon Aion en primer plano… capturo en {n}")
        root.after(1000, lambda: snap(n - 1))
        return
    title = vision.foreground_title()
    root.withdraw(); root.update()
    root.after(500, lambda: finish_snap(title))


def use_window():
    t = last_title[0]
    if not t or t == root.title():
        messagebox.showinfo("Ventana", "Primero captura con Aion en primer plano (la ventana activa tiene que ser la del juego).")
        return
    cfg["behavior"]["game_window"] = t
    save_cfg()
    lbl_vs.config(text=f"Vigilancia activada: el bot solo pulsará teclas si la ventana activa contiene «{t}».")


b_snap.config(command=snap); b_win.config(command=use_window)

# ===========================================================================
# Pestaña Guía
# ===========================================================================
POLICIES = {"Avisarme y pausar en los tramos que el bot no puede hacer (misiones, instancias)": "avisar",
            "Seguir farmeando la zona de la tabla de Conocimiento en esos tramos": "farmear"}
tab_gu = ttk.Frame(nb)
nb.add(tab_gu, text="📖  Guía")
gc = card(tab_gu, fill="x", padx=6, pady=6)
v_guide_on = tk.BooleanVar(value=cfg["guide"].get("enabled", True))
v_pol = tk.StringVar(value=[k for k, v in POLICIES.items() if v == cfg["guide"].get("manual_policy", "avisar")][0])
v_gbonus = tk.IntVar(value=cfg["guide"].get("level_bonus", 0))
ttk.Checkbutton(gc, text=f"Seguir la guía: {(guide or {}).get('nombre', 'sin guía (falta guide.json)')}", variable=v_guide_on).grid(row=0, column=0, columnspan=3, sticky="w")
ttk.Combobox(gc, textvariable=v_pol, values=list(POLICIES), width=78, state="readonly").grid(row=1, column=0, columnspan=3, sticky="w", pady=6)
ttk.Label(gc, text="Adelantar tramos (niveles extra por equipo fuerte)", style="Card.TLabel").grid(row=2, column=0, sticky="w")
ttk.Spinbox(gc, from_=0, to=10, textvariable=v_gbonus, width=5).grid(row=2, column=1, sticky="w", padx=8)
gv = ttk.Treeview(tab_gu, columns=("lv", "type", "where", "what"), show="headings", height=11)
for col, txt, w in (("lv", "Niveles", 70), ("type", "Quién", 90), ("where", "Dónde", 170), ("what", "Qué hacer", 480)):
    gv.heading(col, text=txt); gv.column(col, width=w, anchor="center" if col in ("lv", "type") else "w")
gv.tag_configure("now", background=ACCENT, foreground="#0b0614")
gv.pack(fill="x", padx=6, pady=4)


def refresh_guide():
    gv.delete(*gv.get_children())
    cur = step_for(guide, cfg["character"]["level"] + int(cfg["guide"].get("level_bonus", 0))) if guide else None
    for i, st_ in enumerate((guide or {}).get("steps", [])):
        lv = f"{st_['from']}" if st_["from"] == st_["to"] else f"{st_['from']}-{st_['to']}"
        gv.insert("", "end", iid=str(i), tags=("now",) if st_ is cur else (),
                  values=(lv, "🤖 bot" if st_["mode"] == "grind" else "🧍 tú", st_["zone"], f"{st_['title']}. {st_['detalle']}"))


ttk.Label(tab_gu, wraplength=820, foreground=MUTED, text=(
    "La fila resaltada es tu tramo actual. En los tramos 🤖 el bot farmea la zona indicada. Los tramos 🧍 son misiones o instancias que el bot "
    "no sabe hacer: te avisa con un sonido y se pausa para que las hagas tú (o puedes elegir que siga farmeando). "
    "La ruta viene de guías de la comunidad (foro de EuroAion 4.6) y puede estar desactualizada: edita guide.json si algo no coincide.")).pack(anchor="w", padx=8, pady=6)

# ===========================================================================
# Pestaña Conocimiento
# ===========================================================================
tab_kn = ttk.Frame(nb)
nb.add(tab_kn, text="📜  Conocimiento")
kv = ttk.Treeview(tab_kn, columns=("zone", "lv", "notes"), show="headings", height=10)
for col, txt, w in (("zone", "Zona", 140), ("lv", "Nivel", 80), ("notes", "Notas", 560)):
    kv.heading(col, text=txt); kv.column(col, width=w, anchor="w")


def refresh_kn():
    kv.delete(*kv.get_children())
    for i, z in enumerate(sorted(kn["zones"], key=lambda z: z["min"])):
        kv.insert("", "end", iid=str(i), values=(z["name"], f"{z['min']}-{z['max']}", z.get("notas", "")))


kv.pack(fill="x", padx=6, pady=6)
kf = card(tab_kn, fill="x", padx=6, pady=4)
k_name, k_min, k_max, k_note = tk.StringVar(), tk.IntVar(value=1), tk.IntVar(value=10), tk.StringVar()
for c_, (lab, var, w) in enumerate((("Zona", k_name, 16), ("Nivel mín.", k_min, 6), ("Nivel máx.", k_max, 6), ("Notas", k_note, 30))):
    ttk.Label(kf, text=lab, style="Card.TLabel").grid(row=0, column=c_, sticky="w", padx=4)
    ttk.Entry(kf, textvariable=var, width=w).grid(row=1, column=c_, sticky="w", padx=4)


def kn_select(_e=None):
    sel = kv.selection()
    if sel:
        z = sorted(kn["zones"], key=lambda z: z["min"])[int(sel[0])]
        k_name.set(z["name"]); k_min.set(z["min"]); k_max.set(z["max"]); k_note.set(z.get("notas", ""))


kv.bind("<<TreeviewSelect>>", kn_select)


def refresh_zone_lists():
    names = [z["name"] for z in sorted(kn["zones"], key=lambda z: z["min"])]
    zn[:] = names
    for cb in (cb_zone, cb_spzone, cb_plzone):
        cb.config(values=names)
    route_values()


def kn_save_all():
    kn["zones"].sort(key=lambda z: z["min"])
    refresh_zone_lists()
    planner.zones = sorted(kn["zones"], key=lambda z: z["min"])
    save_json(engine.KNOWLEDGE_PATH, kn)
    refresh_kn(); refresh_rec()


def kn_apply():
    try:
        z = {"name": k_name.get().strip(), "min": int(k_min.get()), "max": int(k_max.get()), "notas": k_note.get()}
    except tk.TclError:
        return
    if not z["name"]:
        return
    old = next((x for x in kn["zones"] if x["name"].lower() == z["name"].lower()), None)
    if old:
        old.update(z)
    else:
        kn["zones"].append({**z, "mobs": []})
    kn_save_all()


def kn_delete():
    sel = kv.selection()
    if sel:
        z = sorted(kn["zones"], key=lambda z: z["min"])[int(sel[0])]
        kn["zones"].remove(z)
        kn_save_all()


ttk.Button(kf, text="Guardar / añadir", style="Accent.TButton", command=kn_apply).grid(row=1, column=4, padx=8)
ttk.Button(kf, text="Borrar", command=kn_delete).grid(row=1, column=5)
ttk.Label(tab_kn, wraplength=820, foreground=MUTED, text=(
    "Las zonas y niveles de aquí mandan: el bot elige la zona según tu nivel (+ bonus de equipo). Ajústalas a lo que veas en EUROaion 4.6 "
    "(selecciona una fila para editarla). Las zonas nuevas aparecen al momento en los desplegables (también puedes escribir el nombre a mano en 'Zona actual')."
)).pack(anchor="w", padx=8, pady=6)
refresh_kn()

# ===========================================================================
# Lógica de la ventana
# ===========================================================================


def collect():
    ch.update(level=int(v_level.get()), zone=v_zone.get(), gear_power=int(v_power.get()),
              auto_zone_check=v_auto.get(), pause_on_zone_change=v_pausez.get(), auto_route=v_route.get())
    cfg["explore"].update(enabled=v_explore.get(), turn_seconds=round(float(v_turn.get()), 2))
    cfg["guide"].update(enabled=v_guide_on.get(), manual_policy=POLICIES[v_pol.get()], level_bonus=int(v_gbonus.get()))
    mc = cfg["monsters"]
    mc.update(enabled=v_mon_on.get(), keep_ratio=int(v_keep.get()) / 100, max_danger=int(v_danger.get()),
              auto_spot=v_autospot.get())
    hb, ac = cfg["hotbar"], cfg["auto_skills"]
    hb.update(cols=int(v_cols.get()), rows=int(v_rows.get()),
              keys=[k.strip() for k in v_keys.get().split(",")],
              row_mods=[m.strip() for m in v_mods.get().split(",")],
              input=INPUTS[v_input.get()],
              ignore_rows=[int(x) - 1 for x in v_skip.get().split(",") if x.strip().isdigit()])
    ac.update(enabled=v_auto_on.get(), mode=MODES[v_mode.get()])
    for k, (key, below, cd) in pv.items():
        cfg["potions"][k] = {"key": key.get(), "below": float(below.get() or 0), "cooldown": float(cd.get() or 10)}


def save_cfg():
    collect(); save_json(engine.CONFIG_PATH, cfg)


def start():
    global runner
    if runner and not runner.stopped.is_set():
        return
    try:
        save_cfg()
    except (ValueError, tk.TclError):
        messagebox.showerror("Error", "Revisa el nivel y los números de las pociones."); return
    miss = [k for k in ("hp", "target") if not cfg["bars"][k].get("region")]
    if miss and not messagebox.askyesno("Sin calibrar", "Faltan barras por calibrar (vida / objetivo). Sin ellas el bot "
                                        "funciona a ciegas y es mucho menos fiable. ¿Continuar?"):
        return
    runner = BotRunner(cfg, kn, log=log, on_status=on_status, alert=alert, book=book, db=db)
    runner.start()
    start_hotkeys()


def pause():
    if runner:
        runner.toggle_pause()


def stop():
    if runner:
        runner.stop()


hk_started = False


def start_hotkeys():
    global hk_started
    if hk_started:
        return
    hk_started = True
    from pynput import keyboard

    def on_press(k):
        n = getattr(k, "name", None)
        if n == "f10": pause()
        elif n == "f12": stop()
    keyboard.Listener(on_press=on_press, daemon=True).start()


b_start.config(command=start); b_pause.config(command=pause); b_stop.config(command=stop)


def pump():
    try:
        while True:
            kind, a, b = events.get_nowait()
            if kind == "log":
                log_box.config(state="normal"); log_box.insert("end", a, b or ()); log_box.see("end")
                log_box.config(state="disabled")
            elif kind == "files":
                show_files(a, b)
            elif kind == "diag":
                show_diag(a, b)
            elif kind == "beep":
                try:
                    import winsound; winsound.Beep(880, 300)
                except Exception:
                    root.bell()
            elif kind == "status":
                s = a.last_status
                for k, v in (("hp", s.hp), ("mp", s.mp), ("tg", s.thp)):
                    pb, lab = bars[k]
                    pb["value"] = (v or 0) * 100; lab.config(text="—" if v is None else f"{v:.0%}")
                fs = getattr(a, "focus_state", None)
                set_lamp("win", fs, "Ventana del juego: activa" if fs else "Ventana del juego: NO activa" if fs is False
                         else "Ventana: sin vigilancia")
                set_lamp("hp", None if s.hp is None else s.hp > 0,
                         "Vida: sin calibrar" if s.hp is None else f"Vida: la leo ({s.hp:.0%})" if s.hp > 0 else "Vida: NO la veo")
                set_lamp("tg", None if s.thp is None else True, "Objetivo: sin calibrar" if s.thp is None else "Objetivo: leído")
                set_lamp("bar", None if s.slots is None else True, "Habilidades: sin marcar" if s.slots is None
                         else f"Habilidades: {sum(1 for x in s.slots if x.occupied)} detectadas")
                lbl_kills.config(text=f"{a.kills} kills"); lbl_kph.config(text=f"{a.kills_per_hour():.0f} / hora")
                lbl_zone.config(text=f"Zona: {cfg['character']['zone']}  ·  Punto: {cfg['character'].get('spot') or '—'}  ·  Nivel {cfg['character']['level']}")
                try:
                    if cfg["character"]["level"] != v_level.get():
                        v_level.set(cfg["character"]["level"])
                except tk.TclError:
                    pass
    except queue.Empty:
        pass
    root.after(250, pump)


_tick = [0]


def periodic():
    _tick[0] += 1
    if _tick[0] % 8 == 0:
        refresh_learned(); refresh_monsters(); refresh_spots(); refresh_guide()
    root.after(250, periodic)


refresh_skills(); refresh_cal(); refresh_learned(); refresh_monsters(); refresh_spots(); refresh_plan(); refresh_guide(); pump(); periodic()
root.protocol("WM_DELETE_WINDOW", lambda: (stop(), root.destroy()))
root.mainloop()
