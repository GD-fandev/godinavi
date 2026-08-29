import hashlib
import json
import os
import re
import shutil
import ssl
import tempfile
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path, PurePosixPath

import certifi

from monster_pak import PakReader, build_pak


MANIFEST_URL = (
    "https://raw.githubusercontent.com/GD-fandev/godinavi/"
    "main/update/manifest.json"
)
RELEASE_URL_PREFIX = "https://github.com/GD-fandev/godinavi/releases/download/"
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_EXTRACTED_BYTES = 1024 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 20000
USER_AGENT = "GodiNavi-MapUpdater/1.0"
REQUEST_TIMEOUT_SECONDS = 60
DOWNLOAD_ATTEMPTS = 3


class UpdateError(RuntimeError):
    pass


def _tls_context():
    # Frozen builds must not depend on the target PC's Python/OpenSSL CA path.
    # PyInstaller bundles certifi's CA file with GodiNavi.
    return ssl.create_default_context(cafile=certifi.where())


def _open_url(request, timeout):
    return urllib.request.urlopen(request, timeout=timeout, context=_tls_context())


def version_key(value):
    text = str(value or "").strip()
    numbers = re.findall(r"\d+", text)
    return tuple(int(number) for number in numbers) if numbers else (0,)


def load_local_version(app_dir):
    path = Path(app_dir) / "map-version.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return str(payload.get("version", "0"))
    except Exception:
        return "0"


def validate_manifest(payload):
    if not isinstance(payload, dict):
        raise UpdateError("The update manifest is not a JSON object.")
    version = str(payload.get("version", "")).strip()
    asset_url = str(payload.get("asset_url", "")).strip()
    checksum = str(payload.get("sha256", "")).strip().lower()
    size = payload.get("size")
    if not version or version_key(version) == (0,):
        raise UpdateError("The manifest version is invalid.")
    if not asset_url.startswith(RELEASE_URL_PREFIX):
        raise UpdateError("The update URL is not an allowed GodiNavi release URL.")
    if not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise UpdateError("The update checksum is invalid.")
    if not isinstance(size, int) or size <= 0 or size > MAX_ARCHIVE_BYTES:
        raise UpdateError("The update size is invalid.")
    return {
        "schema": int(payload.get("schema", 1)),
        "version": version,
        "asset_url": asset_url,
        "sha256": checksum,
        "size": size,
    }


def fetch_manifest(timeout=15):
    request = urllib.request.Request(
        MANIFEST_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with _open_url(request, timeout=timeout) as response:
        raw = response.read(131073)
    if len(raw) > 131072:
        raise UpdateError("The update manifest is too large.")
    return validate_manifest(json.loads(raw.decode("utf-8-sig")))


def update_is_available(local_version, manifest):
    return version_key(manifest["version"]) > version_key(local_version)


def _download_once(manifest, destination, progress_callback=None):
    request = urllib.request.Request(
        manifest["asset_url"],
        headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream"},
    )
    digest = hashlib.sha256()
    downloaded = 0
    with _open_url(request, timeout=REQUEST_TIMEOUT_SECONDS) as response, Path(destination).open("wb") as output:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_ARCHIVE_BYTES:
            raise UpdateError("The update archive is too large.")
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            downloaded += len(chunk)
            if downloaded > MAX_ARCHIVE_BYTES:
                raise UpdateError("The update archive exceeded the size limit.")
            output.write(chunk)
            digest.update(chunk)
            if progress_callback:
                progress_callback(downloaded, manifest["size"])
    if downloaded != manifest["size"]:
        raise UpdateError("The downloaded file size does not match the manifest.")
    if digest.hexdigest().lower() != manifest["sha256"]:
        raise UpdateError("The downloaded file checksum does not match the manifest.")


def _download(manifest, destination, progress_callback=None):
    destination = Path(destination)
    last_error = None
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            _download_once(manifest, destination, progress_callback)
            return
        except Exception as exc:
            last_error = exc
            try:
                destination.unlink(missing_ok=True)
            except Exception:
                pass
            if attempt < DOWNLOAD_ATTEMPTS:
                time.sleep(1.5)
    raise UpdateError(
        f"Map ZIP download failed after {DOWNLOAD_ATTEMPTS} attempts: "
        f"{type(last_error).__name__}: {last_error}"
    ) from last_error


def _safe_member_path(name):
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise UpdateError(f"Unsafe archive path: {name}")
    if path.parts[0] not in {"maps", "mapdata"}:
        raise UpdateError(f"Unexpected top-level archive path: {name}")
    return path


def _extract_and_validate(archive_path, content_dir):
    total_size = 0
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        if not entries or len(entries) > MAX_ARCHIVE_ENTRIES:
            raise UpdateError("The update archive has an invalid number of files.")
        for entry in entries:
            path = _safe_member_path(entry.filename)
            unix_type = (entry.external_attr >> 16) & 0o170000
            if unix_type == 0o120000:
                raise UpdateError("Symbolic links are not allowed in an update archive.")
            total_size += entry.file_size
            if total_size > MAX_EXTRACTED_BYTES:
                raise UpdateError("The extracted update would be too large.")
            target = Path(content_dir).joinpath(*path.parts)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)

    maps_dir = Path(content_dir) / "maps"
    mapdata_dir = Path(content_dir) / "mapdata"
    if not maps_dir.is_dir() or not mapdata_dir.is_dir():
        raise UpdateError("The update archive must contain maps and mapdata folders.")

    records = []
    seen_ids = set()
    for json_path in mapdata_dir.rglob("*.json"):
        try:
            record = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise UpdateError(f"Invalid map JSON: {json_path.name}: {exc}") from exc
        if not isinstance(record, dict) or not record.get("id"):
            raise UpdateError(f"Invalid map record: {json_path.name}")
        map_id = str(record["id"])
        if map_id in seen_ids:
            raise UpdateError(f"Duplicate map ID: {map_id}")
        seen_ids.add(map_id)
        image_value = str(record.get("image", "")).replace("\\", "/")
        image_path = PurePosixPath(image_value)
        if image_path.is_absolute() or not image_path.parts or image_path.parts[0] != "maps":
            raise UpdateError(f"Invalid image path for map {map_id}")
        if any(part in ("", ".", "..") for part in image_path.parts):
            raise UpdateError(f"Unsafe image path for map {map_id}")
        image_on_disk = Path(content_dir).joinpath(*image_path.parts)
        if not image_on_disk.is_file():
            raise UpdateError(f"Missing image for map {map_id}: {image_value}")
        records.append(record)
    if not records:
        raise UpdateError("The update contains no map records.")
    return len(records)


def _write_version(app_dir, version):
    path = Path(app_dir) / "map-version.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps({"version": version}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def download_and_install(manifest, app_dir, progress_callback=None):
    app_dir = Path(app_dir).resolve()
    if not app_dir.is_dir():
        raise UpdateError("The GodiNavi application folder does not exist.")
    operation_id = uuid.uuid4().hex
    stage_dir = app_dir / f".godinavi-update-stage-{operation_id}"
    backup_dir = app_dir / f".godinavi-update-backup-{operation_id}"
    archive_path = stage_dir / "update.zip"
    content_dir = stage_dir / "content"
    moved_old = []
    installed_new = []
    old_version = load_local_version(app_dir)
    success = False
    try:
        stage_dir.mkdir()
        content_dir.mkdir()
        _download(manifest, archive_path, progress_callback)
        map_count = _extract_and_validate(archive_path, content_dir)
        backup_dir.mkdir()
        incoming_folders = ["maps", "mapdata"]
        for folder_name in incoming_folders:
            current = app_dir / folder_name
            backup = backup_dir / folder_name
            if current.exists():
                current.replace(backup)
                moved_old.append(folder_name)
        for folder_name in incoming_folders:
            incoming = content_dir / folder_name
            target = app_dir / folder_name
            incoming.replace(target)
            installed_new.append(folder_name)
        _write_version(app_dir, manifest["version"])
        success = True
        return {"version": manifest["version"], "map_count": map_count}
    except Exception:
        failed_dir = stage_dir / "failed-install"
        failed_dir.mkdir(parents=True, exist_ok=True)
        for folder_name in reversed(installed_new):
            target = app_dir / folder_name
            if target.exists():
                target.replace(failed_dir / folder_name)
        for folder_name in reversed(moved_old):
            backup = backup_dir / folder_name
            target = app_dir / folder_name
            if backup.exists() and not target.exists():
                backup.replace(target)
        try:
            _write_version(app_dir, old_version)
        except Exception:
            pass
        raise
    finally:
        if success:
            shutil.rmtree(backup_dir, ignore_errors=True)
        shutil.rmtree(stage_dir, ignore_errors=True)
        if backup_dir.exists() and not any(backup_dir.iterdir()):
            backup_dir.rmdir()


def build_update_archive(project_dir, output_path, version):
    project_dir = Path(project_dir).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip", dir=output_path.parent) as temporary:
        temporary_path = Path(temporary.name)
    try:
        monster_source = project_dir / "monsterdata"
        entries = {
            path.relative_to(monster_source).as_posix(): path
            for path in monster_source.rglob("*") if path.is_file()
        }
        if not entries:
            raise UpdateError("Monster source data is missing: monsterdata")
        monster_pak = project_dir / "mapdata" / "monsterdata.pak"
        build_pak(monster_pak, "monsterdata", entries)
        with PakReader(monster_pak, "monsterdata") as reader:
            if set(reader.names()) != set(entries):
                raise UpdateError("Monster PAK verification failed.")
        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for folder_name in ("maps", "mapdata"):
                folder = project_dir / folder_name
                if not folder.is_dir():
                    raise UpdateError(f"Missing source folder: {folder_name}")
                for path in sorted(folder.rglob("*")):
                    if path.is_file():
                        archive.write(path, path.relative_to(project_dir).as_posix())
        temporary_path.replace(output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    digest_builder = hashlib.sha256()
    with output_path.open("rb") as archive_file:
        while True:
            chunk = archive_file.read(1024 * 1024)
            if not chunk:
                break
            digest_builder.update(chunk)
    digest = digest_builder.hexdigest()
    tag = f"maps-{version}"
    return {
        "schema": 1,
        "version": version,
        "asset_url": f"{RELEASE_URL_PREFIX}{tag}/godinavi-mapdata.zip",
        "sha256": digest,
        "size": output_path.stat().st_size,
    }
