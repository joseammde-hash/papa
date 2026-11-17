#!/usr/bin/env python3
"""Ventana del bot con tema asmodiano (violeta oscuro y plata).

pip install pyautogui pynput pillow   (opcional para leer el nivel: pytesseract)
python app.py
"""
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import engine
from engine import BotRunner, load_json, save_json
from skillbook import SkillBook

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
    hdr.create_text(w // 2, 58, text="EUROaion  ·  Ranger  ·  Daeva de Pandaemonium",
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
ttk.Combobox(c, textvariable=v_zone, values=[z["name"] for z in kn["zones"]], width=16,
             state="readonly").grid(row=1, column=1, sticky="w", padx=8)
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
                if key == "level_region":
                    cfg["bars"]["level_region"] = reg
                elif key == "hotbar":
                    cfg["hotbar"]["region"] = reg
                else:
                    px = pyautogui.screenshot(region=(reg[0] + 2, (reg[1] + reg[3]) // 2, 1, 1)).getpixel((0, 0))
                    cfg["bars"][key]["region"] = reg; cfg["bars"][key]["color"] = list(px[:3])
                refresh_cal()
            return
        cal_lbl[key].config(text=f"Colócate… {n}")
        root.after(1000, lambda: step(n - 1))

    cal_lbl[key].config(text="Esquina SUPERIOR IZQUIERDA (3 s)…")
    step(3)


for i, (k, txt) in enumerate((("hp", "Mi vida"), ("mp", "Mi maná"), ("target", "Vida del objetivo"), ("level_region", "Nivel (opcional, OCR)"))):
    ttk.Label(cc, text=txt, style="Card.TLabel", width=22).grid(row=i + 1, column=0, sticky="w", pady=4)
    ttk.Button(cc, text="Marcar", command=lambda k=k, t=txt: capture(k, t)).grid(row=i + 1, column=1, padx=8)
    cal_lbl[k] = ttk.Label(cc, text="", style="Muted.TLabel")
    cal_lbl[k].grid(row=i + 1, column=2, sticky="w")


def refresh_cal():
    for k, lab in cal_lbl.items():
        if k == "hotbar":
            lab.config(text=f"✔ {cfg['hotbar']['region']}" if cfg["hotbar"].get("region") else "sin marcar")
        elif k == "level_region":
            lab.config(text="✔ marcado" if cfg["bars"].get("level_region") else "sin marcar (usa el nivel manual)")
        else:
            b = cfg["bars"][k]
            lab.config(text=f"✔ {b['region']} color {tuple(b['color'])}" if b.get("region") else "sin marcar")


def live_test():
    from engine import ScreenPerception
    perc = ScreenPerception(cfg)

    def go(n):
        s = perc.read()
        msg = lambda v: "—" if v is None else f"{v:.0%}"
        log(f"Lectura: vida {msg(s.hp)} · maná {msg(s.mp)} · objetivo {msg(s.thp)} · nivel {s.level or '—'}")
        if n > 0:
            root.after(700, lambda: go(n - 1))
    go(6)


ttk.Button(cc, text="Probar lectura (6 s, mira la pestaña Batalla)", command=live_test).grid(row=6, column=0, columnspan=3, sticky="w", pady=(14, 0))

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
# Pestaña Rutas
# ===========================================================================
tab_rt = ttk.Frame(nb)
nb.add(tab_rt, text="🗺  Rutas")
rc = card(tab_rt, fill="x", padx=6, pady=6)
ttk.Label(rc, text="Graba cómo ir de una zona a otra (teclas de movimiento) y el bot la repetirá cuando toque cambiar de zona. "
                   "Para grabar: pulsa 'Grabar', ve al juego, haz el recorrido y pulsa F9 para terminar.",
          style="Muted.TLabel", wraplength=780).pack(anchor="w")
zn = [z["name"] for z in kn["zones"]]
rf, rt_ = tk.StringVar(value=zn[0]), tk.StringVar(value=zn[1])
row = ttk.Frame(rc, style="Card.TFrame"); row.pack(anchor="w", pady=10)
ttk.Combobox(row, textvariable=rf, values=zn, width=12, state="readonly").pack(side="left")
ttk.Label(row, text="  →  ", style="Card.TLabel").pack(side="left")
ttk.Combobox(row, textvariable=rt_, values=zn, width=12, state="readonly").pack(side="left")


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

# ===========================================================================
# Pestaña Conocimiento
# ===========================================================================
tab_kn = ttk.Frame(nb)
nb.add(tab_kn, text="📜  Conocimiento")
kv = ttk.Treeview(tab_kn, columns=("zone", "lv", "notes"), show="headings", height=10)
for col, txt, w in (("zone", "Zona", 140), ("lv", "Nivel", 80), ("notes", "Notas", 560)):
    kv.heading(col, text=txt); kv.column(col, width=w, anchor="w")
for z in kn["zones"]:
    kv.insert("", "end", values=(z["name"], f"{z['min']}-{z['max']}", z.get("notas", "")))
kv.pack(fill="x", padx=6, pady=6)
ttk.Label(tab_kn, text="Los rangos están escritos de memoria. Si EUROaion usa otros, edita knowledge.json (carpeta aion-bot).",
          foreground=MUTED).pack(anchor="w", padx=8)

# ===========================================================================
# Lógica de la ventana
# ===========================================================================


def collect():
    ch.update(level=int(v_level.get()), zone=v_zone.get(), gear_power=int(v_power.get()),
              auto_zone_check=v_auto.get(), pause_on_zone_change=v_pausez.get(), auto_route=v_route.get())
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
    runner = BotRunner(cfg, kn, log=log, on_status=on_status, alert=alert, book=book)
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
                lbl_kills.config(text=f"{a.kills} kills"); lbl_kph.config(text=f"{a.kills_per_hour():.0f} / hora")
                lbl_zone.config(text=f"Zona: {cfg['character']['zone']}  ·  Nivel {cfg['character']['level']}")
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
        refresh_learned()
    root.after(250, periodic)


refresh_skills(); refresh_cal(); refresh_learned(); pump(); periodic()
root.protocol("WM_DELETE_WINDOW", lambda: (stop(), root.destroy()))
root.mainloop()
