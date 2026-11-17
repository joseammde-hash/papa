"""Actualizador: descarga la última versión del bot desde GitHub y la aplica con seguridad.

- Solo reemplaza archivos de código (*.py, *.md, *.bat y VERSION) de la carpeta del bot.
- Nunca toca tus datos: update.json, skills_learned.json, monsters.json, routes.json.
- config.json: solo se AÑADEN las claves nuevas; tus valores se conservan.
- knowledge.json: solo se crea si falta.
- Hace copia de seguridad antes de aplicar y revierte si algo falla (sintaxis incluida).
"""
import io
import json
import os
import re
import shutil
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

BASE = Path(__file__).parent
CODE_RE = re.compile(r"^[A-Za-z0-9_\-]+\.(py|md|bat)$")
MAX_BYTES = 5_000_000


# -- versiones --------------------------------------------------------------
def local_version(base=BASE):
    try:
        return (Path(base) / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "0.0.0"


def parse_version(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or ""))[:4] or (0,)


def is_newer(remote, local):
    return parse_version(remote) > parse_version(local)


# -- configuración de actualización ---------------------------------------
def load_update_cfg(base=BASE):
    try:
        return json.loads((Path(base) / "update.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def _token(cfg):
    return cfg.get("token") or os.environ.get(cfg.get("token_env", "GITHUB_TOKEN"), "")


def _open(url, cfg, accept=None):
    req = urllib.request.Request(url, headers={"User-Agent": "aion-bot-updater"})
    if accept:
        req.add_header("Accept", accept)
    t = _token(cfg)
    if t:
        req.add_header("Authorization", f"Bearer {t}")
    return urllib.request.urlopen(req, timeout=12)


def _contents_url(cfg, name):
    path = f"{cfg['subdir']}/{name}" if cfg.get("subdir") else name
    return (f"https://api.github.com/repos/{cfg['repo']}/contents/"
            f"{urllib.parse.quote(path)}?ref={urllib.parse.quote(cfg['branch'], safe='/')}")


def fetch_text(cfg, name):
    with _open(_contents_url(cfg, name), cfg, "application/vnd.github.raw+json") as r:
        return r.read(200_000).decode("utf-8", "replace")


def check(cfg, base=BASE):
    """(hay_nueva, version_remota, version_local). Lanza OSError si no hay conexión/acceso."""
    remote = fetch_text(cfg, "VERSION").strip()
    local = local_version(base)
    return is_newer(remote, local), remote, local


def download(cfg):
    url = f"https://api.github.com/repos/{cfg['repo']}/zipball/{urllib.parse.quote(cfg['branch'], safe='/')}"
    with _open(url, cfg) as r:
        data = r.read(20_000_000)
    return data


# -- aplicar ------------------------------------------------------------------
def merge_missing(remote, local):
    """Añade a 'local' las claves que solo existen en 'remote' (recursivo, sin tocar valores existentes)."""
    for k, v in remote.items():
        if k not in local:
            local[k] = v
        elif isinstance(v, dict) and isinstance(local[k], dict):
            merge_missing(v, local[k])
    return local


def _extract(data, subdir):
    zf = zipfile.ZipFile(io.BytesIO(data))
    names = zf.namelist()
    if not names:
        raise ValueError("paquete vacío")
    prefix = names[0].split("/")[0] + "/"
    base = prefix + (subdir.strip("/") + "/" if subdir else "")
    files = {}
    for info in zf.infolist():
        if info.is_dir() or not info.filename.startswith(base):
            continue
        rel = info.filename[len(base):]
        if "/" in rel or info.file_size > MAX_BYTES:
            continue
        if CODE_RE.match(rel) or rel in ("VERSION", "config.json", "knowledge.json"):
            files[rel] = zf.read(info)
    if "VERSION" not in files or "app.py" not in files:
        raise ValueError("el paquete no contiene la app (falta VERSION o app.py)")
    for rel, content in files.items():
        if rel.endswith(".py"):
            compile(content, rel, "exec")          # rechaza paquetes con errores de sintaxis
    return files


def apply_package(data, target=BASE, subdir="", log=print):
    """Aplica el zip descargado. Devuelve la lista de archivos actualizados."""
    target = Path(target)
    files = _extract(data, subdir)
    old = local_version(target)
    backup = target / "_backup" / f"{old}_{time.strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True)
    written = []
    try:
        for rel in files:
            if (target / rel).exists():
                shutil.copy2(target / rel, backup / rel)
        for rel, content in files.items():
            dst = target / rel
            if rel == "knowledge.json":
                if dst.exists():
                    continue
            elif rel == "config.json":
                if dst.exists():
                    merged = merge_missing(json.loads(content), json.loads(dst.read_text(encoding="utf-8")))
                    content = json.dumps(merged, indent=2, ensure_ascii=False).encode("utf-8")
            tmp = dst.with_name(dst.name + ".tmp")
            tmp.write_bytes(content)
            os.replace(tmp, dst)
            written.append(rel)
        # Guardar qué archivos eran nuevos para poder revertir bien
        (backup / "_new_files.json").write_text(
            json.dumps([r for r in written if not (backup / r).exists()]), encoding="utf-8")
    except Exception:
        log("Error al actualizar: restaurando la copia de seguridad")
        restore(backup, target)
        raise
    return written


def restore(backup, target=BASE):
    backup, target = Path(backup), Path(target)
    for f in backup.iterdir():
        if f.name == "_new_files.json":
            continue
        shutil.copy2(f, target / f.name)
    nf = backup / "_new_files.json"
    if nf.exists():
        for rel in json.loads(nf.read_text(encoding="utf-8")):
            (target / rel).unlink(missing_ok=True)


def last_backup(target=BASE):
    d = Path(target) / "_backup"
    if not d.exists():
        return None
    items = sorted(p for p in d.iterdir() if p.is_dir())
    return items[-1] if items else None


def rollback(target=BASE):
    b = last_backup(target)
    if not b:
        raise FileNotFoundError("no hay copia de seguridad")
    restore(b, target)
    shutil.rmtree(b)
    return b.name
