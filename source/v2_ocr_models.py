"""Materialize verified OCR models only for the lifetime of the process."""

from __future__ import annotations

import atexit
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

from v2_pak import PakReader

_MATERIALIZED_MODELS = None


def _remove_tree(path):
    shutil.rmtree(path, ignore_errors=True)


def _remove_legacy_cache():
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    _remove_tree(local / "GodiNavi" / "cache" / "ocr-models")


def _installed_pak(model_root):
    requested = Path(model_root)
    if requested.is_file():
        return requested
    candidates = [requested.parent / "content" / "ocr_models.pak"]
    executable = Path(sys.executable).resolve()
    if executable.parent.name.lower() == "app" and executable.parent.parent.name.lower() == "data":
        candidates.append(executable.parent.parent / "content" / "ocr_models.pak")
    return next((path for path in candidates if path.is_file()), None)


def materialize_ocr_models(model_root, cache_root=None):
    global _MATERIALIZED_MODELS
    requested = Path(model_root)
    if requested.is_dir():
        return requested.resolve()
    pak = _installed_pak(requested)
    if pak is None:
        return requested.resolve()
    if cache_root is None:
        _remove_legacy_cache()
    if _MATERIALIZED_MODELS is not None and _MATERIALIZED_MODELS.is_dir():
        return _MATERIALIZED_MODELS
    if cache_root is None:
        temporary = Path(tempfile.mkdtemp(prefix=".godinavi-ocr-"))
    else:
        temporary = Path(cache_root) / uuid.uuid4().hex
        temporary.mkdir(parents=True, exist_ok=False)
    atexit.register(_remove_tree, temporary)
    try:
        with PakReader(pak, "ocr_models") as reader:
            for name in reader.names():
                destination = temporary / Path(name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(reader.read(name))
        _MATERIALIZED_MODELS = temporary
        return temporary
    except Exception:
        _remove_tree(temporary)
        raise
