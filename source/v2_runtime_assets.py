"""Materialize V2 UI/audio PAKs for libraries that require filesystem paths."""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import uuid
from pathlib import Path

from v2_pak import PakReader


def installed_data_root(executable=None):
    executable = Path(executable or sys.executable).resolve()
    parent = executable.parent
    if parent.name.lower() == "data" and (parent / "installation.json").is_file():
        return parent
    if parent.name.lower() == "app" and parent.parent.name.lower() == "data":
        return parent.parent
    return None


def materialize_runtime_assets(data_root=None, cache_root=None):
    data_root = Path(data_root) if data_root else installed_data_root()
    if data_root is None:
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    packages = (
        (data_root / "assets" / "ui.pak", "ui"),
        (data_root / "assets" / "audio.pak", "audio"),
    )
    if any(not path.is_file() for path, _name in packages):
        return Path(getattr(sys, "_MEIPASS", data_root))
    digest = hashlib.sha256()
    for path, _name in packages:
        digest.update(path.read_bytes())
    cache = Path(cache_root or Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "GodiNavi" / "cache" / "runtime-assets")
    target = cache / digest.hexdigest()
    if (target / ".ready").is_file():
        return target
    temporary = cache / f".{target.name}.{uuid.uuid4().hex}.tmp"
    temporary.mkdir(parents=True, exist_ok=False)
    try:
        assets = temporary / "assets"
        for pak, package_name in packages:
            with PakReader(pak, package_name) as reader:
                for name in reader.names():
                    destination = assets / Path(name)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(reader.read(name))
        (temporary / ".ready").write_text(target.name + "\n", encoding="ascii")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(temporary, target)
        except FileExistsError:
            shutil.rmtree(temporary)
        return target
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
