import json
import os
import re
import ssl
import sys
import urllib.request
from pathlib import Path

import certifi


APP_VERSION = "2.1.3"
REPOSITORIES = {
    "stable": "GD-fandev/godinavi",
    "test": "GD-fandev/godinavi_dev",
}
USER_AGENT = "GodiNavi-VersionChecker/1.0"
EXE_ASSET_NAME = "GodiNavi.exe"
CHECKSUM_ASSET_NAME = "GodiNavi.exe.sha256"
V2_SOURCE_CHANNEL = os.environ.get("GODINAVI_V2_SOURCE_CHANNEL", "stable").strip().lower()


def v2_history_text(history, code):
    lines = []
    for entry in history["entries"]:
        change = entry["changes"][code]
        lines.append(f"[{entry['version']}] {change['summary']}")
        for detail in change["details"]:
            lines.append(detail if "\n" in detail else f"  • {detail}")
        lines.append("")
    return "\n".join(lines).rstrip()


def v2_history_release_body(history):
    return "\n\n".join(
        f"<!-- {code} -->\n{v2_history_text(history, code)}"
        for code in ("KR", "JP", "EN")
    )


def _install_dir():
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        if executable_dir.name.lower() == "data":
            return executable_dir.parent
        if executable_dir.name.lower() == "app" and executable_dir.parent.name.lower() == "data":
            return executable_dir.parents[1]
        return executable_dir
    return Path(__file__).resolve().parent.parent


def load_update_channel(path=None):
    config_path = Path(path) if path else _install_dir() / "update-channel.json"
    if not config_path.is_file():
        return "stable"
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "stable"
    channel = str(payload.get("channel", "")).strip().lower() if isinstance(payload, dict) else ""
    return channel if channel in REPOSITORIES else "stable"


def version_tuple(value):
    numbers = re.findall(r"\d+", str(value))
    return tuple(int(number) for number in numbers[:3]) + (0,) * max(0, 3 - len(numbers))


def load_source_v2_release(root=None):
    """Use the checked-out V2 channel files for the development runner."""
    if getattr(sys, "frozen", False):
        return None
    root = Path(root) if root else _install_dir()
    channel = V2_SOURCE_CHANNEL if V2_SOURCE_CHANNEL in REPOSITORIES else "stable"
    manifest_path = root / "update" / "v2" / channel / "manifest.json"
    history_path = root / "update" / "v2" / channel / "history.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        history = json.loads(history_path.read_text(encoding="utf-8-sig"))
        from v2_contracts import validate_history, validate_manifest
        manifest = validate_manifest(manifest)
        history = validate_history(history)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return None
    update_available = is_newer_version(manifest["clientVersion"], APP_VERSION)
    return {
        "version": manifest["clientVersion"],
        "current_version": APP_VERSION,
        "url": "",
        "body": v2_history_release_body(history),
        "exe_url": "v2-unified-updater",
        "checksum_url": "v2-unified-updater",
        "size": sum(component["size"] for component in manifest["components"].values()) if update_available else 0,
        "v2": True,
        "update_available": update_available,
    }


def fetch_latest_release(timeout=15):
    source_release = load_source_v2_release()
    if source_release:
        return source_release
    if os.environ.get("GODINAVI_V2_SOURCE_CHANNEL"):
        raise RuntimeError(f"V2 source runner requires valid update/v2/{V2_SOURCE_CHANNEL} manifest.json and history.json")
    config_path = _install_dir() / "update-channel.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        config = None
    if isinstance(config, dict) and config.get("schemaVersion") == 2 and config.get("manifestUrl"):
        from v2_contracts import validate_channel, validate_history, validate_manifest
        from v2_network import fetch_json
        from v2_updater_engine import load_installation, required_components
        channel = validate_channel(config)
        manifest = validate_manifest(fetch_json(channel["manifestUrl"], timeout=timeout))
        history = validate_history(fetch_json(manifest["historyUrl"], timeout=timeout))
        installation = load_installation(_install_dir())
        names = required_components(manifest, installation)
        return {
            "version": manifest["clientVersion"],
            "current_version": installation.get("clientVersion", APP_VERSION) if installation else APP_VERSION,
            "url": "",
            "body": v2_history_release_body(history),
            "exe_url": "v2-unified-updater",
            "checksum_url": "v2-unified-updater",
            "size": sum(manifest["components"][name]["size"] for name in names),
            "v2": True,
            "update_available": bool(names),
        }
    repository = REPOSITORIES[load_update_channel()]
    latest_release_api = f"https://api.github.com/repos/{repository}/releases/latest"
    release_page_prefix = f"https://github.com/{repository}/releases/"
    release_download_prefix = f"https://github.com/{repository}/releases/download/"
    request = urllib.request.Request(
        latest_release_api,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        payload = response.read(1024 * 1024 + 1)
    if len(payload) > 1024 * 1024:
        raise ValueError("Release information is too large.")
    data = json.loads(payload.decode("utf-8"))
    tag = str(data.get("tag_name", ""))
    url = str(data.get("html_url", ""))
    if not re.fullmatch(r"v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", tag):
        raise ValueError("Invalid release version.")
    if not url.startswith(release_page_prefix):
        raise ValueError("Invalid release URL.")
    assets = {str(item.get("name", "")): item for item in data.get("assets", []) if isinstance(item, dict)}
    exe = assets.get(EXE_ASSET_NAME, {})
    checksum = assets.get(CHECKSUM_ASSET_NAME, {})
    exe_url = str(exe.get("browser_download_url", ""))
    checksum_url = str(checksum.get("browser_download_url", ""))
    if exe_url and not exe_url.startswith(release_download_prefix):
        raise ValueError("Invalid executable download URL.")
    if checksum_url and not checksum_url.startswith(release_download_prefix):
        raise ValueError("Invalid checksum download URL.")
    return {
        "version": tag.lstrip("v"),
        "url": url,
        "body": str(data.get("body", "")),
        "exe_url": exe_url,
        "checksum_url": checksum_url,
        "size": int(exe.get("size", 0) or 0),
    }


def is_newer_version(latest, current=APP_VERSION):
    return version_tuple(latest) > version_tuple(current)


def extract_patch_notes(body, language):
    text = str(body or "").replace("\r\n", "\n")
    code = language if language in ("KR", "JP", "EN") else "EN"
    sections = {}
    marker = re.compile(r"<!--\s*(KR|JP|EN)\s*-->", re.IGNORECASE)
    matches = list(marker.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).upper()] = text[match.end():end].strip()
    if sections:
        return sections.get(code) or sections.get("EN") or next(iter(sections.values()))
    return text.strip()
