"""Atomic storage for auxiliary state inside godinavi-config.json."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path


ROOT = Path(os.environ.get("LOCALAPPDATA", Path.cwd())) / "GodiNavi"
CONFIG_PATH = ROOT / "godinavi-config.json"
AUXILIARY_KEYS = {
    "armor_catalog_preferences",
    "map_update_reminder",
    "modal_positions",
    "update_reminder",
}
_LOCK = threading.RLock()


def _read(path=CONFIG_PATH):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}


def _write(value, path=CONFIG_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_section(key, default=None, legacy_paths=()):
    with _LOCK:
        config = _read()
        section = config.get(key)
        section = dict(section) if isinstance(section, dict) else dict(default or {})
        migrated = False
        for legacy_path in legacy_paths:
            legacy_path = Path(legacy_path)
            try:
                legacy = json.loads(legacy_path.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if isinstance(legacy, dict):
                section = {**legacy, **section}
                migrated = True
        if migrated or key not in config:
            config[key] = section
            _write(config)
        if migrated:
            for legacy_path in legacy_paths:
                try:
                    Path(legacy_path).unlink()
                except OSError:
                    pass
        return section


def save_section(key, value):
    with _LOCK:
        config = _read()
        config[key] = dict(value)
        _write(config)

