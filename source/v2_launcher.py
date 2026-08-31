"""Universal launcher for V1 migration, V2 repair, and normal V2 startup."""

from __future__ import annotations

import os
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from v2_contracts import validate_channel, validate_manifest
from v2_network import download, fetch_json
from v2_process import launch_core
from v2_updater_engine import UpdateError, load_installation


LEGACY_BACKUP_DIR = ".godinavi-v1-backup"


def _cleanup_updater_stage(wait=False):
    stage_root = Path(os.environ.get("LOCALAPPDATA", "")) / "GodiNavi" / "updater-stage"
    attempts = 50 if wait else 1
    for _attempt in range(attempts):
        if not stage_root.exists():
            return True
        shutil.rmtree(stage_root, ignore_errors=True)
        if not stage_root.exists():
            return True
        if wait:
            time.sleep(0.1)
    return False


def bundled_channel():
    bundle = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return bundle / "update-channel.json"


def ensure_channel(root):
    """Materialize the immutable build channel beside the installed launcher."""
    source = bundled_channel()
    target = root / "update-channel.json"
    if not source.is_file():
        if target.is_file():
            return target
        raise FileNotFoundError("The launcher build has no update channel configuration.")
    # Parse before copying so a corrupt build cannot poison an installation.
    json.loads(source.read_text(encoding="utf-8-sig"))
    if not target.is_file() or target.read_bytes() != source.read_bytes():
        temporary = target.with_suffix(".json.tmp")
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    return target


def install_root():
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path.cwd()


def installation_mode(root):
    state_path = Path(root) / "data" / "installation.json"
    if not state_path.is_file():
        return "legacy"
    try:
        return "v2" if load_installation(root) is not None else "legacy"
    except UpdateError:
        return "repair"


def preserve_legacy_launcher(root):
    """Rescue the V1 executable before the legacy patcher deletes .old."""
    root = Path(root).resolve()
    preserved = root / LEGACY_BACKUP_DIR / "GodiNavi.exe"
    if preserved.is_file() and preserved.stat().st_size > 0:
        return preserved
    legacy_old = root / "GodiNavi.exe.old"
    if not legacy_old.is_file() or legacy_old.stat().st_size <= 0:
        return None
    preserved.parent.mkdir(parents=True, exist_ok=True)
    os.replace(legacy_old, preserved)
    return preserved


def _load_channel_and_manifest(channel_path):
    channel = validate_channel(json.loads(Path(channel_path).read_text(encoding="utf-8-sig")))
    manifest = validate_manifest(fetch_json(channel["manifestUrl"]))
    if manifest["channel"] != channel["channel"]:
        raise ValueError("Channel and manifest do not match.")
    return channel, manifest


def _stage_updater(root, manifest):
    item = manifest["components"]["updater"]
    stage_root = Path(os.environ.get("LOCALAPPDATA", root)) / "GodiNavi" / "updater-stage"
    if stage_root.is_dir():
        for previous in stage_root.iterdir():
            if previous.is_dir():
                shutil.rmtree(previous, ignore_errors=True)
            else:
                try:
                    previous.unlink()
                except OSError:
                    pass
    stage = stage_root / str(int(time.time() * 1000))
    stage.mkdir(parents=True, exist_ok=True)
    staged_updater = stage / "GodiNaviUpdater.exe"
    installed = root / "GodiNaviUpdater.exe"
    if installed.is_file() and installed.stat().st_size == item["size"] and hashlib.sha256(installed.read_bytes()).hexdigest() == item["sha256"]:
        shutil.copy2(installed, staged_updater)
    else:
        download(item["url"], staged_updater, item["size"])
        if hashlib.sha256(staged_updater.read_bytes()).hexdigest() != item["sha256"]:
            staged_updater.unlink(missing_ok=True)
            raise ValueError("Updater v2 checksum mismatch.")
    return staged_updater


def _quarantine_invalid_state(root):
    state = root / "data" / "installation.json"
    if not state.is_file():
        return None
    backup = state.with_name(f"installation.invalid-{int(time.time())}.json")
    os.replace(state, backup)
    return backup


def start_update(root, *, mode=None):
    root = Path(root)
    mode = mode or installation_mode(root)
    channel_path = ensure_channel(root)
    _channel, manifest = _load_channel_and_manifest(channel_path)
    staged_updater = _stage_updater(root, manifest)
    invalid_backup = _quarantine_invalid_state(root) if mode == "repair" else None
    command = [
        str(staged_updater), "--channel-file", str(channel_path),
        "--install-root", str(root), "--wait-pid", str(os.getpid()),
    ]
    if mode == "legacy":
        command.extend(("--legacy-install", str(root)))
    try:
        return subprocess.Popen(command, cwd=str(root), close_fds=True)
    except Exception:
        if invalid_backup and invalid_backup.is_file():
            os.replace(invalid_backup, root / "data" / "installation.json")
        raise


def main():
    root = install_root()
    arguments = sys.argv[1:]
    cleanup_index = arguments.index("--cleanup-updater-stage") if "--cleanup-updater-stage" in arguments else -1
    if cleanup_index >= 0:
        del arguments[cleanup_index:cleanup_index + 2]
        _cleanup_updater_stage(wait=True)
    else:
        _cleanup_updater_stage()
    mode = installation_mode(root)
    if mode == "legacy":
        preserve_legacy_launcher(root)
    ensure_channel(root)
    if "--update" in arguments or mode in {"legacy", "repair"}:
        start_update(root, mode=mode)
        return 0
    launch_core(root, arguments)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
