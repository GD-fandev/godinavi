"""Versioned data contracts for the GodiNavi 2.x installer.

This module intentionally has no third-party dependency so the launcher,
updater, publishing tools, and tests can all enforce the same rules.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from urllib.parse import urlparse


SCHEMA_VERSION = 2
LANGUAGES = ("KR", "JP", "EN")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?")
SNAPSHOT_VERSION_PATTERN = re.compile(r"\d{4}\.\d{2}\.\d{2}\.\d+")
CONTENT_VERSION_PATTERN = SNAPSHOT_VERSION_PATTERN

COMPONENT_PATHS = {
    "launcher": "GodiNavi.exe",
    "updater": "GodiNaviUpdater.exe",
    "core": "data/GodiNaviCore.exe",
    "runtime": "data/runtime",
    "ocr_models": "data/content/ocr_models.pak",
    "ui_assets": "data/assets/ui.pak",
    "audio_assets": "data/assets/audio.pak",
    "maps": "data/content/maps.pak",
    "monsters": "data/content/monsters.pak",
    "equipment": "data/content/equipment.pak",
}

COMPONENT_FORMATS = {
    "launcher": "file",
    "updater": "file",
    "core": "file",
    "runtime": "zip",
    "ocr_models": "pak",
    "ui_assets": "pak",
    "audio_assets": "pak",
    "maps": "pak",
    "monsters": "pak",
    "equipment": "pak",
}

CONTENT_COMPONENTS = {"maps", "monsters", "equipment"}

CHANNEL_REPOSITORIES = {
    "stable": "GD-fandev/godinavi",
    "test": "GD-fandev/godinavi_dev",
}


class ContractError(ValueError):
    """Raised when v2 update data violates its published contract."""


def _object(value, label):
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object.")
    return value


def _exact_keys(value, required, optional, label):
    missing = set(required) - set(value)
    unknown = set(value) - set(required) - set(optional)
    if missing:
        raise ContractError(f"{label} is missing: {', '.join(sorted(missing))}.")
    if unknown:
        raise ContractError(f"{label} has unknown fields: {', '.join(sorted(unknown))}.")


def _https_url(value, label):
    if not isinstance(value, str):
        raise ContractError(f"{label} must be an HTTPS URL.")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ContractError(f"{label} must be an HTTPS URL.")
    return value


def _version(value, label, pattern=VERSION_PATTERN):
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ContractError(f"{label} has an invalid version.")
    return value


def validate_channel(payload):
    payload = _object(payload, "channel config")
    _exact_keys(payload, {"schemaVersion", "channel", "manifestUrl"}, set(), "channel config")
    if payload["schemaVersion"] != SCHEMA_VERSION:
        raise ContractError("Unsupported channel schema.")
    if payload["channel"] not in {"stable", "test"}:
        raise ContractError("Unsupported update channel.")
    _https_url(payload["manifestUrl"], "manifestUrl")
    if "/releases/latest" in payload["manifestUrl"].lower():
        raise ContractError("V2 channels must not use GitHub releases/latest.")
    parsed = urlparse(payload["manifestUrl"])
    expected_path = f"/repos/{CHANNEL_REPOSITORIES[payload['channel']]}/contents/"
    if parsed.netloc.lower() != "api.github.com" or not parsed.path.startswith(expected_path):
        raise ContractError(
            f"{payload['channel']} channel must use the {CHANNEL_REPOSITORIES[payload['channel']]} Contents API."
        )
    return payload


def validate_manifest(payload):
    payload = _object(payload, "manifest")
    _exact_keys(
        payload,
        {"schemaVersion", "channel", "clientVersion", "snapshotVersion", "historyUrl", "components"},
        set(),
        "manifest",
    )
    if payload["schemaVersion"] != SCHEMA_VERSION:
        raise ContractError("Unsupported manifest schema.")
    if payload["channel"] not in {"stable", "test"}:
        raise ContractError("Unsupported manifest channel.")
    _version(payload["clientVersion"], "clientVersion")
    _version(payload["snapshotVersion"], "snapshotVersion", SNAPSHOT_VERSION_PATTERN)
    _https_url(payload["historyUrl"], "historyUrl")
    components = _object(payload["components"], "components")
    if set(components) != set(COMPONENT_PATHS):
        missing = set(COMPONENT_PATHS) - set(components)
        unknown = set(components) - set(COMPONENT_PATHS)
        detail = []
        if missing:
            detail.append(f"missing {', '.join(sorted(missing))}")
        if unknown:
            detail.append(f"unknown {', '.join(sorted(unknown))}")
        raise ContractError(f"Invalid component set: {'; '.join(detail)}.")
    for name, item in components.items():
        item = _object(item, f"component {name}")
        _exact_keys(item, {"version", "path", "url", "size", "sha256", "format"}, set(), f"component {name}")
        _version(item["version"], f"component {name} version", CONTENT_VERSION_PATTERN if name in CONTENT_COMPONENTS else VERSION_PATTERN)
        if item["path"] != COMPONENT_PATHS[name]:
            raise ContractError(f"Component {name} has an invalid installation path.")
        path = PurePosixPath(item["path"])
        if path.is_absolute() or ".." in path.parts or "\\" in item["path"]:
            raise ContractError(f"Component {name} has an unsafe installation path.")
        _https_url(item["url"], f"component {name} URL")
        if not isinstance(item["size"], int) or isinstance(item["size"], bool) or item["size"] <= 0:
            raise ContractError(f"Component {name} has an invalid size.")
        if not isinstance(item["sha256"], str) or not SHA256_PATTERN.fullmatch(item["sha256"]):
            raise ContractError(f"Component {name} has an invalid SHA-256.")
        if item["format"] != COMPONENT_FORMATS[name]:
            raise ContractError(f"Component {name} has an invalid format.")
    return payload


def validate_installation(payload):
    payload = _object(payload, "installation state")
    _exact_keys(
        payload,
        {"schemaVersion", "clientVersion", "snapshotVersion", "components"},
        {"installedAt", "manifestUrl"},
        "installation state",
    )
    if payload["schemaVersion"] != SCHEMA_VERSION:
        raise ContractError("Unsupported installation schema.")
    _version(payload["clientVersion"], "clientVersion")
    _version(payload["snapshotVersion"], "snapshotVersion", SNAPSHOT_VERSION_PATTERN)
    components = _object(payload["components"], "installation components")
    if set(components) != set(COMPONENT_PATHS):
        raise ContractError("Installation state must contain every v2 component.")
    for name, version in components.items():
        _version(version, f"installed component {name}", CONTENT_VERSION_PATTERN if name in CONTENT_COMPONENTS else VERSION_PATTERN)
    if "manifestUrl" in payload:
        _https_url(payload["manifestUrl"], "manifestUrl")
    if "installedAt" in payload and (not isinstance(payload["installedAt"], str) or not payload["installedAt"]):
        raise ContractError("installedAt must be a non-empty string.")
    return payload


def validate_history(payload):
    payload = _object(payload, "change history")
    _exact_keys(payload, {"schemaVersion", "entries"}, set(), "change history")
    if payload["schemaVersion"] != SCHEMA_VERSION:
        raise ContractError("Unsupported change-history schema.")
    if not isinstance(payload["entries"], list):
        raise ContractError("Change-history entries must be an array.")
    seen = set()
    for index, entry in enumerate(payload["entries"]):
        label = f"change-history entry {index}"
        entry = _object(entry, label)
        _exact_keys(entry, {"id", "kind", "version", "components", "publishedAt", "changes"}, set(), label)
        if not isinstance(entry["id"], str) or not entry["id"] or entry["id"] in seen:
            raise ContractError(f"{label} has an invalid or duplicate id.")
        seen.add(entry["id"])
        if entry["kind"] not in {"client", "content"}:
            raise ContractError(f"{label} has an invalid kind.")
        _version(entry["version"], f"{label} version", CONTENT_VERSION_PATTERN if entry["kind"] == "content" else VERSION_PATTERN)
        components = entry["components"]
        if (
            not isinstance(components, list) or not components
            or any(name not in COMPONENT_PATHS for name in components)
            or len(set(components)) != len(components)
        ):
            raise ContractError(f"{label} has invalid components.")
        if not isinstance(entry["publishedAt"], str) or not entry["publishedAt"]:
            raise ContractError(f"{label} has an invalid publishedAt value.")
        changes = _object(entry["changes"], f"{label} changes")
        if set(changes) != set(LANGUAGES):
            raise ContractError(f"{label} must provide KR, JP, and EN changes.")
        for language, text in changes.items():
            text = _object(text, f"{label} {language}")
            _exact_keys(text, {"summary", "details"}, set(), f"{label} {language}")
            if not isinstance(text["summary"], str) or not text["summary"].strip():
                raise ContractError(f"{label} {language} summary is empty.")
            if not isinstance(text["details"], list) or not text["details"] or any(not isinstance(item, str) or not item.strip() for item in text["details"]):
                raise ContractError(f"{label} {language} details must be non-empty strings.")
    return payload
