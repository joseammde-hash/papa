"""Lector de los ARCHIVOS del juego (solo lectura de la carpeta de instalación).

No lee la memoria del juego ni el tráfico de red: solo abre ficheros que ya están en tu disco.

  - find_install():  busca la carpeta de Aion.
  - inventory():     cuenta qué hay (extensiones, tamaños, .pak, ficheros de datos) y prueba si son legibles.
  - extract_paks():  extrae de los .pak legibles (formato ZIP) los XML/textos de datos.
  - import_dir():    lee XML ya extraídos (NPC/monstruos, habilidades, textos) y crea game_data.json.
  - GameData:        consulta rápida (nivel de un monstruo por su nombre).
"""
import difflib
import json
import math
import os
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

BASE = Path(__file__).parent
GAMEDATA_PATH = BASE / "game_data.json"
KEYWORDS = ("npc", "mob", "monster", "skill", "world", "map", "quest", "string", "item", "level", "zone", "exp")
TEXT_EXT = {".xml", ".txt", ".ini", ".cfg", ".csv", ".json", ".lua", ".html"}
NAME_KEYS = ("name", "desc", "nameid", "name_id", "string")
LEVEL_KEYS = ("level", "lv", "npc_level", "lvl")
HP_KEYS = ("hp", "max_hp", "maxhp", "hp_max")


def anon(p):
    """Quita el nombre de usuario de Windows de las rutas del informe."""
    s = str(p)
    home = str(Path.home())
    return s.replace(home, "~") if home and home != "/" else s


# -- localizar la instalación -------------------------------------------------
def find_install(roots=None, max_depth=4, time_limit=25):
    """Busca carpetas que contengan bin32/bin64/aion.bin. Devuelve una lista de rutas."""
    if roots is None:
        roots = []
        for d in "CDEFGH":
            for sub in ("Program Files (x86)", "Program Files", "Games", "Juegos", ""):
                p = Path(f"{d}:\\{sub}")
                if p.exists():
                    roots.append(p)
    found, t0 = [], time.time()
    for root in roots:
        base_depth = len(Path(root).parts)
        for dirpath, dirs, files in os.walk(root):
            if time.time() - t0 > time_limit:
                return found
            if len(Path(dirpath).parts) - base_depth >= max_depth:
                dirs[:] = []
            dirs[:] = [d for d in dirs if d.lower() not in ("windows", "$recycle.bin", "system volume information")]
            low = {f.lower() for f in files}
            if "aion.bin" in low or ("system.cfg" in low and "aion" in dirpath.lower()):
                parent = Path(dirpath)
                if parent.name.lower() in ("bin32", "bin64"):
                    parent = parent.parent
                if parent not in found:
                    found.append(parent)
    return found


# -- sondeo de ficheros ---------------------------------------------------------
def entropy(data):
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    n = len(data)
    return -sum(c / n * math.log2(c / n) for c in counts if c)


def probe_pak(path):
    """Clasifica un .pak: zip legible, o cifrado/comprimido."""
    info = {"file": path.name, "size": path.stat().st_size}
    try:
        with open(path, "rb") as f:
            head = f.read(65536)
        info["magic"] = head[:8].hex()
        info["entropy"] = round(entropy(head), 2)
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
            info["kind"] = "zip"
            info["entries"] = len(names)
            info["sample"] = names[:12]
        elif info["entropy"] > 7.5:
            info["kind"] = "cifrado_o_comprimido"
        else:
            info["kind"] = "desconocido"
    except (OSError, zipfile.BadZipFile) as e:
        info["kind"] = f"error: {e}"
    return info


def probe_xml(path, max_bytes=2_000_000):
    """Describe un XML legible (etiqueta raíz y atributos) o avisa de que está codificado."""
    try:
        raw = path.read_bytes()[:max_bytes]
    except OSError as e:
        return {"file": path.name, "kind": f"error: {e}"}
    if not raw.lstrip()[:1] == b"<":
        return {"file": path.name, "kind": "codificado", "entropy": round(entropy(raw[:65536]), 2)}
    try:
        it = ET.iterparse(__import__("io").BytesIO(raw), events=("start",))
        tags, attrs, n = {}, {}, 0
        for _, el in it:
            tags[el.tag] = tags.get(el.tag, 0) + 1
            for k in el.attrib:
                attrs[k] = attrs.get(k, 0) + 1
            n += 1
            if n > 4000:
                break
        top = sorted(tags, key=tags.get, reverse=True)[:6]
        return {"file": path.name, "kind": "xml", "tags": top, "attrs": sorted(attrs, key=attrs.get, reverse=True)[:12]}
    except ET.ParseError:
        return {"file": path.name, "kind": "xml_truncado_o_invalido"}


def inventory(root, max_files=300000, log=print):
    root = Path(root)
    by_ext, big, keyfiles, paks, xmls = {}, [], [], [], []
    n = 0
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            n += 1
            if n > max_files:
                break
            p = Path(dirpath) / f
            try:
                size = p.stat().st_size
            except OSError:
                continue
            ext = p.suffix.lower() or "(sin extensión)"
            e = by_ext.setdefault(ext, [0, 0])
            e[0] += 1
            e[1] += size
            big.append((size, p))
            low = f.lower()
            if any(k in low for k in KEYWORDS) and ext in TEXT_EXT | {".pak"}:
                keyfiles.append(p)
            if ext == ".pak":
                paks.append(p)
            elif ext == ".xml" and len(xmls) < 40:
                xmls.append(p)
    big.sort(key=lambda t: -t[0])
    log(f"{n} archivos analizados")
    return {
        "root": anon(root), "files": n,
        "ext": {k: {"n": v[0], "mb": round(v[1] / 1e6, 1)} for k, v in sorted(by_ext.items(), key=lambda kv: -kv[1][1])[:25]},
        "biggest": [{"file": anon(p.relative_to(root)), "mb": round(s / 1e6, 1)} for s, p in big[:12]],
        "key_files": [anon(p.relative_to(root)) for p in keyfiles[:60]],
        "paks": [probe_pak(p) for p in paks[:40]],
        "xml_samples": [probe_xml(p) for p in xmls[:15]],
        "configs": [anon(p.relative_to(root)) for p in root.rglob("*.cfg")][:10] +
                   [anon(p.relative_to(root)) for p in root.rglob("*.ini")][:10],
    }


def report_lines(inv):
    L = [("ok", f"Carpeta: {inv['root']} — {inv['files']} archivos")]
    L.append(("ok", "Tipos de archivo (por tamaño): " + ", ".join(f"{k} ×{v['n']} ({v['mb']} MB)" for k, v in list(inv["ext"].items())[:8])))
    kinds = {}
    for p in inv["paks"]:
        kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
    if inv["paks"]:
        L.append(("ok", f"Archivos .pak: {len(inv['paks'])} → " + ", ".join(f"{k}: {v}" for k, v in kinds.items())))
        if kinds.get("zip"):
            L.append(("ok", f"{kinds['zip']} .pak se pueden abrir como ZIP: se pueden extraer sus datos."))
        if kinds.get("cifrado_o_comprimido"):
            L.append(("warn", f"{kinds['cifrado_o_comprimido']} .pak parecen cifrados/comprimidos (entropía alta): hay que extraerlos antes con una "
                              "herramienta de la comunidad (p. ej. AION-Encdec) y luego importar la carpeta resultante."))
    else:
        L.append(("warn", "No hay archivos .pak en esa carpeta: ¿es la carpeta correcta de Aion?"))
    x_ok = [x for x in inv["xml_samples"] if x["kind"] == "xml"]
    x_bad = [x for x in inv["xml_samples"] if x["kind"] == "codificado"]
    if x_ok:
        L.append(("ok", f"{len(x_ok)} XML legibles: " + "; ".join(f"{x['file']} ({', '.join(x['tags'][:3])})" for x in x_ok[:5])))
    if x_bad:
        L.append(("warn", f"{len(x_bad)} XML están codificados (no son texto): necesitan decodificarse (AION-Encdec)."))
    if inv["key_files"]:
        L.append(("ok", "Ficheros con nombres de interés: " + ", ".join(inv["key_files"][:12])))
    if inv["configs"]:
        L.append(("ok", "Configuración: " + ", ".join(inv["configs"][:8])))
    return L


# -- extraer .pak legibles ---------------------------------------------------------
def extract_paks(root, out_dir, patterns=("npc", "skill", "string", "world", "item"), log=print, max_mb=300):
    """Extrae de los .pak en formato ZIP los .xml cuyo nombre contenga alguno de los patrones."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    count = 0
    for pak in Path(root).rglob("*.pak"):
        if not zipfile.is_zipfile(pak):
            continue
        try:
            with zipfile.ZipFile(pak) as z:
                for info in z.infolist():
                    low = info.filename.lower()
                    if low.endswith(".xml") and any(p in low for p in patterns) and info.file_size < max_mb * 1e6:
                        name = re.sub(r"[^\w.\-]", "_", Path(info.filename).name)       # nombre plano: sin rutas dentro del zip
                        (out / name).write_bytes(z.read(info))
                        count += 1
        except (OSError, zipfile.BadZipFile, RuntimeError) as e:
            log(f"No pude leer {pak.name}: {e}")
    log(f"{count} XML extraídos a {anon(out)}")
    return count


# -- importar XML extraídos ------------------------------------------------------------
def _first(attrs, keys):
    for k in keys:
        for ak, v in attrs.items():
            if ak.lower() == k:
                return v
    return None


def _strings(folder):
    """Tabla id→texto de los ficheros de cadenas (<string><id>…</id><body>…</body></string>)."""
    table = {}
    for p in Path(folder).glob("*.xml"):
        if "string" not in p.name.lower():
            continue
        try:
            for el in ET.parse(p).getroot().iter():
                kid = el.findtext("id") or el.findtext("name") or el.attrib.get("id")
                body = el.findtext("body") or el.attrib.get("body")
                if kid and body:
                    table[kid.strip().upper()] = body.strip()
        except ET.ParseError:
            continue
    return table


def import_dir(folder, out_path=GAMEDATA_PATH, log=print):
    """Lee los XML de 'folder' y guarda monstruos (nombre → nivel/vida) y habilidades en game_data.json."""
    folder = Path(folder)
    strings = _strings(folder)
    monsters, skills, files_seen = {}, {}, []

    def resolve(v):
        if v is None:
            return None
        return strings.get(v.strip().upper(), v)

    for p in sorted(folder.glob("*.xml")):
        low = p.name.lower()
        kind = "npc" if re.search(r"npc|mob|monster", low) else "skill" if "skill" in low else None
        if not kind:
            continue
        try:
            root = ET.parse(p).getroot()
        except ET.ParseError:
            log(f"{p.name}: XML no legible (¿codificado?)")
            continue
        n = 0
        for el in root.iter():
            at = el.attrib or {k: (v.text or "") for k, v in ((c.tag, c) for c in el if len(c) == 0)}
            name = resolve(_first(at, NAME_KEYS) or el.findtext("name") or el.findtext("desc"))
            if not name or name.upper().startswith("STR_"):
                continue
            if kind == "npc":
                lv = _first(at, LEVEL_KEYS)
                if lv is None and el.findtext("level"):
                    lv = el.findtext("level")
                if lv and str(lv).strip().isdigit():
                    hp = _first(at, HP_KEYS) or el.findtext("hp")
                    monsters[name] = {"level": int(lv), **({"hp": int(hp)} if hp and str(hp).strip().isdigit() else {})}
                    n += 1
            else:
                sid = at.get("id") or el.findtext("id")
                if sid:
                    skills[str(sid)] = name
                    n += 1
        files_seen.append({"file": p.name, "kind": kind, "records": n})
    data = {"monsters": monsters, "skills": skills, "files": files_seen}
    Path(out_path).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    log(f"Importados {len(monsters)} monstruos y {len(skills)} habilidades de {len(files_seen)} ficheros")
    return data


class GameData:
    def __init__(self, data=None):
        self.monsters = (data or {}).get("monsters", {})
        self.skills = (data or {}).get("skills", {})
        self._names = list(self.monsters)
        self._cache = {}

    @classmethod
    def load(cls, path=GAMEDATA_PATH):
        try:
            return cls(json.loads(Path(path).read_text(encoding="utf-8")))
        except (FileNotFoundError, ValueError):
            return cls()

    def level_of(self, name):
        """Nivel del monstruo por su nombre (tolera errores del OCR). None si no se conoce."""
        if not name or not self.monsters:
            return None
        if name in self._cache:
            return self._cache[name]
        hit = name if name in self.monsters else next(iter(difflib.get_close_matches(name, self._names, 1, 0.82)), None)
        lv = self.monsters[hit]["level"] if hit else None
        self._cache[name] = lv
        return lv
