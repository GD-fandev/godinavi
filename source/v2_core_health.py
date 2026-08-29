"""Core-side health protocol used before an update transaction is committed."""

from __future__ import annotations

import json
import os
from pathlib import Path

from v2_contracts import COMPONENT_PATHS, validate_installation


class CoreHealthError(RuntimeError):
    pass


def validate_installed_layout(install_root, proposed_state, core_version):
    install_root = Path(install_root).resolve()
    state = validate_installation(proposed_state)
    if state["clientVersion"] != core_version:
        raise CoreHealthError(
            f"Core version {core_version} does not match proposed client {state['clientVersion']}."
        )
    missing = [name for name, relative in COMPONENT_PATHS.items() if not (install_root / relative).exists()]
    if missing:
        raise CoreHealthError("Installed components are missing: " + ", ".join(missing))
    return state


def write_health_token(token_path, install_root, proposed_state, core_version):
    state = validate_installed_layout(install_root, proposed_state, core_version)
    token = {
        "schemaVersion": state["schemaVersion"],
        "status": "ready",
        "pid": os.getpid(),
        "clientVersion": state["clientVersion"],
        "snapshotVersion": state["snapshotVersion"],
    }
    path = Path(token_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(token, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return token
