"""Process lifecycle helpers shared by Launcher and Updater v2."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path


class ProcessError(RuntimeError):
    pass


def launch_core(install_root, arguments=()):
    root = Path(install_root).resolve()
    core = root / "data" / "GodiNaviCore.exe"
    if not core.is_file():
        raise ProcessError(f"GodiNavi Core is missing: {core}")
    return subprocess.Popen([str(core), *arguments], cwd=str(root), close_fds=True)


def check_core(install_root, proposed_state, transaction_dir, timeout=30):
    transaction = Path(transaction_dir)
    state_path = transaction / "proposed-installation.json"
    token_path = transaction / "core-health.json"
    state_path.write_text(json.dumps(proposed_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    token_path.unlink(missing_ok=True)
    process = launch_core(install_root, (
        "--v2-health-check",
        "--state-file", str(state_path),
        "--health-token", str(token_path),
    ))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if token_path.is_file():
            try:
                token = json.loads(token_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                token = None
            if isinstance(token, dict) and token.get("status") == "ready" and token.get("clientVersion") == proposed_state["clientVersion"]:
                try:
                    return process.wait(timeout=5) == 0
                except subprocess.TimeoutExpired:
                    process.terminate()
                    return False
        # A Windows one-file GUI executable may let its bootloader parent exit
        # before the extracted child writes the health token. Keep waiting for
        # the authenticated token until the deadline instead of treating that
        # normal hand-off as a failed Core launch.
        time.sleep(0.1)
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    return False
