"""Backup, migrate, validate, and restore GodiNavi user settings."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path


class SettingsError(RuntimeError):
    pass


SETTINGS = {
    "godinavi-config.json": "godinavi-config.json",
    "buff_timer/config.json": "buff_timer/config.json",
}


def prune_settings_backups(local_appdata=None, keep=2):
    root = user_root(local_appdata) / "backups"
    if not root.is_dir():
        return []
    entries = sorted(
        (path for path in root.iterdir() if path.is_dir()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    removed = []
    for path in entries[max(0, int(keep)):]:
        shutil.rmtree(path, ignore_errors=True)
        if not path.exists():
            removed.append(path)
    return removed


def _validate_json(path):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SettingsError(f"Invalid settings file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SettingsError(f"Settings file must contain an object: {path}")
    return payload


def user_root(local_appdata=None):
    base = Path(local_appdata or os.environ.get("LOCALAPPDATA", ""))
    if not str(base):
        raise SettingsError("LOCALAPPDATA is unavailable.")
    return base.resolve() / "GodiNavi"


def backup_settings(local_appdata=None, timestamp=None):
    root = user_root(local_appdata)
    existing = [root / relative for relative in SETTINGS if (root / relative).is_file()]
    if not existing:
        return None
    backup = root / "backups" / (timestamp or time.strftime("%Y%m%d-%H%M%S"))
    suffix = 1
    while backup.exists():
        backup = backup.with_name(f"{backup.name}-{suffix}")
        suffix += 1
    for source in existing:
        _validate_json(source)
        target = backup / source.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return backup


def migrate_legacy_settings(legacy_install, local_appdata=None, roaming_appdata=None):
    root = user_root(local_appdata)
    root.mkdir(parents=True, exist_ok=True)
    legacy = Path(legacy_install).resolve() if legacy_install else None
    roaming = Path(roaming_appdata or os.environ.get("APPDATA", ""))
    candidates = {
        "godinavi-config.json": [legacy / "godinavi-config.json"] if legacy else [],
        "buff_timer/config.json": ([legacy / "config.json"] if legacy else [])
        + ([roaming / "GodiusCrystalBuffTimer" / "config.json"] if str(roaming) else []),
    }
    migrated = []
    for relative, sources in candidates.items():
        target = root / relative
        if target.exists():
            _validate_json(target)
            continue
        source = next((path for path in sources if path.is_file()), None)
        if source is None:
            continue
        _validate_json(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".new")
        shutil.copy2(source, temporary)
        _validate_json(temporary)
        os.replace(temporary, target)
        migrated.append(str(target))
    return migrated


def restore_settings(backup, local_appdata=None):
    if backup is None:
        return []
    backup = Path(backup)
    root = user_root(local_appdata)
    restored = []
    for relative in SETTINGS:
        source = backup / relative
        if not source.is_file():
            continue
        _validate_json(source)
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".restore")
        shutil.copy2(source, temporary)
        _validate_json(temporary)
        os.replace(temporary, target)
        restored.append(str(target))
    return restored
