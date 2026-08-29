"""Transactional component installer used by the single GodiNavi Updater v2."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import time
import uuid
import zipfile
from pathlib import Path

from v2_contracts import COMPONENT_PATHS, validate_installation, validate_manifest
from v2_pak import PakReader


MAX_ARCHIVE_ENTRIES = 100_000
MAX_EXPANDED_BYTES = 4 * 1024 * 1024 * 1024
LEGACY_V2_PATHS = (
    # V1 root layout. Legal notices are intentionally retained.
    "maps",
    "mapdata",
    "monsterdata",
    "ocr_models",
    "armor_catalog",
    "assets",
    ".godinavi-v1-backup",
    "GodiNavi.exe.sha256",
    "map-version.json",
    # Earlier V2 test layouts.
    "data/maps",
    "data/mapdata",
    "data/monsterdata",
    "data/armor_catalog",
    "data/assets/monsters.pak",
)
LEGACY_CONTENT_VERSION = "1970.01.01.1"


class UpdateError(RuntimeError):
    pass


class UpdateCancelled(UpdateError):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def required_components(manifest, installation):
    validate_manifest(manifest)
    if installation is None:
        return list(manifest["components"])
    validate_installation(installation)
    installed = installation["components"]
    return [name for name, item in manifest["components"].items() if installed[name] != item["version"]]


def installation_from_manifest(manifest, *, installed_at=None, manifest_url=None):
    state = {
        "schemaVersion": manifest["schemaVersion"],
        "clientVersion": manifest["clientVersion"],
        "snapshotVersion": manifest["snapshotVersion"],
        "components": {name: item["version"] for name, item in manifest["components"].items()},
        "installedAt": installed_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if manifest_url:
        state["manifestUrl"] = manifest_url
    validate_installation(state)
    return state


def _write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_installation(install_root):
    path = Path(install_root) / "data" / "installation.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if payload.get("schemaVersion") == 1:
            payload = _migrate_schema1_installation(payload)
        return validate_installation(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise UpdateError(f"Installed component state is invalid: {exc}") from exc


def _migrate_schema1_installation(payload):
    """Normalize both released schema-1 layouts without trusting obsolete paths."""
    components = payload.get("components")
    if not isinstance(components, dict):
        raise ValueError("Legacy installation components must be an object.")
    migrated = {
        "schemaVersion": 2,
        "clientVersion": payload.get("clientVersion"),
        "snapshotVersion": payload.get("contentVersion"),
        "components": {},
    }
    for optional in ("installedAt", "manifestUrl"):
        if optional in payload:
            migrated[optional] = payload[optional]
    current_layout = set(components) == set(COMPONENT_PATHS)
    for name in COMPONENT_PATHS:
        if name in components and (current_layout or name not in {"maps", "monsters", "equipment"}):
            migrated["components"][name] = components[name]
        else:
            migrated["components"][name] = LEGACY_CONTENT_VERSION if name in {"maps", "monsters", "equipment"} else "0.0.0"
    return migrated


def _safe_archive_name(name):
    if not name or "\\" in name:
        raise UpdateError(f"Unsafe archive path: {name}")
    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        raise UpdateError(f"Unsafe archive path: {name}")
    return path


def _extract_zip(package, destination):
    destination.mkdir(parents=True, exist_ok=True)
    seen = set()
    total = 0
    with zipfile.ZipFile(package) as bundle:
        infos = bundle.infolist()
        if not infos or len(infos) > MAX_ARCHIVE_ENTRIES:
            raise UpdateError("ZIP has an invalid number of entries.")
        for info in infos:
            relative = _safe_archive_name(info.filename)
            folded = relative.as_posix().casefold()
            if folded in seen:
                raise UpdateError(f"ZIP contains a duplicate path: {info.filename}")
            seen.add(folded)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise UpdateError(f"ZIP contains a symbolic link: {info.filename}")
            total += info.file_size
            if info.file_size < 0 or total > MAX_EXPANDED_BYTES:
                raise UpdateError("ZIP expands beyond the allowed size.")
            target = destination / relative
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)


def _remove_path(path):
    path = Path(path)
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def _prepare_component(name, item, package, prepared_root):
    target = prepared_root / name
    if item["format"] == "zip":
        _extract_zip(package, target)
        if not any(target.rglob("*")):
            raise UpdateError(f"Component {name} is empty.")
        return target
    if item["format"] == "pak":
        expected = {
            "ui_assets": "ui", "audio_assets": "audio", "maps": "maps",
            "monsters": "monsters", "equipment": "equipment", "ocr_models": "ocr_models",
        }[name]
        try:
            with PakReader(package, expected) as reader:
                if not reader.encrypted:
                    raise UpdateError(f"Component {name} must use encrypted V2 PAK format.")
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            raise UpdateError(f"Component {name} is not a valid PAK: {exc}") from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(package, target)
    return target


def _verify_download(name, item, package):
    size = package.stat().st_size
    if size != item["size"]:
        raise UpdateError(f"Component {name} size mismatch: expected {item['size']}, received {size}.")
    actual = sha256_file(package)
    if actual != item["sha256"]:
        raise UpdateError(f"Component {name} checksum mismatch.")


def _journal_path(transaction):
    return transaction / "journal.json"


def _save_journal(transaction, journal):
    _write_json_atomic(_journal_path(transaction), journal)


def _rollback(transaction, journal):
    errors = []
    for operation in reversed(journal.get("operations", [])):
        target = Path(operation["target"])
        backup = transaction / operation["backup"]
        try:
            if backup.exists():
                _remove_path(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(backup, target)
            elif operation.get("status") in {"target_moved", "installed"} and not operation.get("existed"):
                _remove_path(target)
        except OSError as exc:
            errors.append(f"{operation.get('name')}: {exc}")
    previous_state = transaction / "previous-installation.json"
    state_path = Path(journal["installRoot"]) / "data" / "installation.json"
    try:
        if previous_state.exists():
            state_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(previous_state, state_path)
        elif not journal.get("hadInstallation"):
            state_path.unlink(missing_ok=True)
    except OSError as exc:
        errors.append(f"installation.json: {exc}")
    journal["phase"] = "rollback_failed" if errors else "rolled_back"
    journal["rollbackErrors"] = errors
    _save_journal(transaction, journal)
    if errors:
        raise UpdateError("Rollback was incomplete: " + "; ".join(errors))


def recover_interrupted_updates(install_root):
    root = Path(install_root).resolve()
    transactions = root / "data" / ".update" / "transactions"
    recovered = []
    if not transactions.is_dir():
        return recovered
    for transaction in sorted(transactions.iterdir()):
        journal_path = _journal_path(transaction)
        if not journal_path.is_file():
            continue
        try:
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise UpdateError(f"Unreadable update journal: {journal_path}: {exc}") from exc
        if Path(journal.get("installRoot", "")).resolve() != root:
            raise UpdateError(f"Update journal belongs to another installation: {journal_path}")
        if journal.get("phase") not in {"committed", "rolled_back"}:
            _rollback(transaction, journal)
            recovered.append(transaction.name)
        if journal.get("phase") in {"committed", "rolled_back"}:
            shutil.rmtree(transaction, ignore_errors=True)
    return recovered


class TransactionalInstaller:
    """Install one complete manifest snapshot with rollback on any failure."""

    def __init__(self, install_root, downloader, progress=None, cancelled=None):
        self.install_root = Path(install_root).resolve()
        self.downloader = downloader
        self.progress = progress or (lambda event, **detail: None)
        self.cancelled = cancelled or (lambda: False)

    def _check_cancelled(self):
        if self.cancelled():
            raise UpdateCancelled("The update was cancelled.")

    def install(self, manifest, *, manifest_url=None, health_check=None, before_apply=None):
        manifest = validate_manifest(manifest)
        self.install_root.mkdir(parents=True, exist_ok=True)
        recover_interrupted_updates(self.install_root)
        previous = load_installation(self.install_root)
        names = required_components(manifest, previous)
        if not names:
            self.progress("up_to_date", clientVersion=manifest["clientVersion"])
            return previous

        transaction = self.install_root / "data" / ".update" / "transactions" / uuid.uuid4().hex
        downloads = transaction / "downloads"
        prepared_root = transaction / "prepared"
        backup_root = transaction / "backup"
        for path in (downloads, prepared_root, backup_root):
            path.mkdir(parents=True, exist_ok=True)
        state_path = self.install_root / "data" / "installation.json"
        if state_path.is_file():
            shutil.copy2(state_path, transaction / "previous-installation.json")

        operations = []
        for name in names:
            operations.append({
                "name": name,
                "target": str((self.install_root / COMPONENT_PATHS[name]).resolve()),
                "backup": f"backup/{name}",
                "existed": False,
                "status": "pending",
            })
        journal = {
            "schemaVersion": manifest["schemaVersion"],
            "installRoot": str(self.install_root),
            "phase": "downloading",
            "hadInstallation": previous is not None,
            "operations": operations,
        }
        _save_journal(transaction, journal)

        try:
            for index, name in enumerate(names, start=1):
                self._check_cancelled()
                item = manifest["components"][name]
                package = downloads / f"{name}.package"
                self.progress("download", name=name, index=index, total=len(names), size=item["size"])
                self.downloader(item["url"], package, item["size"])
                self._check_cancelled()
                if not package.is_file():
                    raise UpdateError(f"Downloader did not create component {name}.")
                _verify_download(name, item, package)
                self.progress("prepare", name=name, index=index, total=len(names))
                _prepare_component(name, item, package, prepared_root)
                self._check_cancelled()

            journal["phase"] = "prepared"
            _save_journal(transaction, journal)
            if before_apply:
                before_apply(manifest, previous, transaction)
            self._check_cancelled()

            journal["phase"] = "applying"
            _save_journal(transaction, journal)
            for operation in operations:
                self._check_cancelled()
                name = operation["name"]
                target = Path(operation["target"])
                prepared = prepared_root / name
                backup = transaction / operation["backup"]
                target.parent.mkdir(parents=True, exist_ok=True)
                operation["existed"] = target.exists()
                _save_journal(transaction, journal)
                if operation["existed"]:
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(target, backup)
                operation["status"] = "target_moved"
                _save_journal(transaction, journal)
                os.replace(prepared, target)
                operation["status"] = "installed"
                _save_journal(transaction, journal)
                self.progress("applied", name=name)
                self._check_cancelled()

            state = installation_from_manifest(manifest, manifest_url=manifest_url)
            journal["phase"] = "health_check"
            _save_journal(transaction, journal)
            if health_check and not health_check(state, transaction):
                raise UpdateError("GodiNavi Core health check failed.")
            self._check_cancelled()
            for index, relative in enumerate(LEGACY_V2_PATHS):
                self._check_cancelled()
                target = self.install_root / relative
                if not target.exists():
                    continue
                operation = {
                    "name": f"legacy_cleanup_{index}",
                    "target": str(target.resolve()),
                    "backup": f"backup/legacy_cleanup_{index}",
                    "existed": True,
                    "status": "pending",
                }
                operations.append(operation)
                backup = transaction / operation["backup"]
                backup.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target, backup)
                operation["status"] = "target_moved"
                _save_journal(transaction, journal)
            self._check_cancelled()
            _write_json_atomic(state_path, state)
            journal["phase"] = "committed"
            _save_journal(transaction, journal)
            self.progress("complete", clientVersion=state["clientVersion"], snapshotVersion=state["snapshotVersion"])
            shutil.rmtree(transaction, ignore_errors=True)
            return state
        except Exception:
            _rollback(transaction, journal)
            if journal.get("phase") == "rolled_back":
                shutil.rmtree(transaction, ignore_errors=True)
            raise
