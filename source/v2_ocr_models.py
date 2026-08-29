"""Materialize verified OCR model PAKs for libraries that require file paths."""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import uuid
from pathlib import Path

from v2_pak import PakReader


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
    requested = Path(model_root)
    if requested.is_dir():
        return requested.resolve()
    pak = _installed_pak(requested)
    if pak is None:
        return requested.resolve()
    digest = hashlib.sha256(pak.read_bytes()).hexdigest()
    cache = Path(cache_root or Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "GodiNavi" / "cache" / "ocr-models")
    target = cache / digest
    ready = target / ".ready"
    if ready.is_file():
        return target
    temporary = cache / f".{digest}.{uuid.uuid4().hex}.tmp"
    temporary.mkdir(parents=True, exist_ok=False)
    try:
        with PakReader(pak, "ocr_models") as reader:
            for name in reader.names():
                destination = temporary / Path(name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(reader.read(name))
        (temporary / ".ready").write_text(digest + "\n", encoding="ascii")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(temporary, target)
        except FileExistsError:
            shutil.rmtree(temporary)
        return target
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
