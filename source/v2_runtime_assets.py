"""Materialize V2 UI/audio assets only for the lifetime of the process."""

from __future__ import annotations

import atexit
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

from v2_pak import PakReader

_MATERIALIZED_ROOT = None


def _remove_tree(path):
    shutil.rmtree(path, ignore_errors=True)


def _remove_legacy_cache():
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    _remove_tree(local / "GodiNavi" / "cache" / "runtime-assets")


def installed_data_root(executable=None):
    executable = Path(executable or sys.executable).resolve()
    parent = executable.parent
    if parent.name.lower() == "data" and (parent / "installation.json").is_file():
        return parent
    if parent.name.lower() == "app" and parent.parent.name.lower() == "data":
        return parent.parent
    return None


def materialize_runtime_assets(data_root=None, cache_root=None):
    global _MATERIALIZED_ROOT
    data_root = Path(data_root) if data_root else installed_data_root()
    if data_root is None:
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    packages = (
        (data_root / "assets" / "ui.pak", "ui"),
        (data_root / "assets" / "audio.pak", "audio"),
    )
    if any(not path.is_file() for path, _name in packages):
        return Path(getattr(sys, "_MEIPASS", data_root))
    if cache_root is None:
        _remove_legacy_cache()
    if _MATERIALIZED_ROOT is not None and _MATERIALIZED_ROOT.is_dir():
        return _MATERIALIZED_ROOT
    if cache_root is None:
        temporary = Path(tempfile.mkdtemp(prefix=".godinavi-assets-"))
    else:
        temporary = Path(cache_root) / uuid.uuid4().hex
        temporary.mkdir(parents=True, exist_ok=False)
    atexit.register(_remove_tree, temporary)
    try:
        assets = temporary / "assets"
        for pak, package_name in packages:
            with PakReader(pak, package_name) as reader:
                for name in reader.names():
                    destination = assets / Path(name)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(reader.read(name))
        _MATERIALIZED_ROOT = temporary
        return temporary
    except Exception:
        _remove_tree(temporary)
        raise
