"""Deterministic verified packages for the V1.4 monster database."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path, PurePosixPath

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


PAK_SCHEMA_VERSION = 1
PAK_MANIFEST_NAME = "pak-manifest.json"
MAX_ENTRY_COUNT = 20_000
MAX_ENTRY_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ENCRYPTED_MAGIC = b"GDNPAK2\0"
PAK_PASSWORD = b"Godius_is_god_game"
DEVELOPER_NOTE = (
    "Dear developer! Since this project is open source, you do not need to unpack the PAK. "
    "If you want cleaner data, please visit the godinavi repository!!"
)


class PakError(ValueError):
    pass


def _safe_name(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise PakError("PAK paths must be non-empty forward-slash paths.")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts or value.endswith("/"):
        raise PakError(f"Unsafe PAK path: {value}")
    normalized = path.as_posix()
    if normalized == PAK_MANIFEST_NAME:
        raise PakError(f"Reserved PAK path: {value}")
    return normalized


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _zip_info(name):
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    info.create_system = 3
    return info


def _derive_key(salt):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000).derive(PAK_PASSWORD)


def build_pak(destination, package_name, entries, *, encrypted=False):
    """Build a deterministic package from ``{archive_path: source_path}``."""
    destination = Path(destination)
    if not isinstance(package_name, str) or not package_name.strip():
        raise PakError("PAK packageName must be a non-empty string.")
    if not isinstance(entries, dict) or not entries:
        raise PakError("PAK entries must be a non-empty mapping.")
    if len(entries) > MAX_ENTRY_COUNT:
        raise PakError("PAK contains too many entries.")

    prepared = []
    names = set()
    total = 0
    for archive_name, source in entries.items():
        name = _safe_name(archive_name)
        folded = name.casefold()
        if folded in names:
            raise PakError(f"Duplicate PAK path: {name}")
        names.add(folded)
        source = Path(source)
        if not source.is_file():
            raise PakError(f"PAK source is not a file: {source}")
        data = source.read_bytes()
        if len(data) > MAX_ENTRY_BYTES:
            raise PakError(f"PAK entry is too large: {name}")
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise PakError("PAK expands beyond the allowed size.")
        prepared.append((name, data))

    prepared.sort(key=lambda item: item[0])
    manifest = {
        "schemaVersion": PAK_SCHEMA_VERSION,
        "packageName": package_name,
        **({"developerNote": DEVELOPER_NOTE} if encrypted else {}),
        "entries": {
            name: {"size": len(data), "sha256": _sha256_bytes(data)}
            for name, data in prepared
        },
    }
    manifest_data = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", allowZip64=True) as bundle:
        bundle.writestr(_zip_info(PAK_MANIFEST_NAME), manifest_data, compresslevel=9)
        for name, data in prepared:
            bundle.writestr(_zip_info(name), data, compresslevel=9)
    payload = stream.getvalue()
    if encrypted:
        salt = hashlib.sha256(b"GodiNavi PAK salt\0" + package_name.encode("utf-8")).digest()[:16]
        nonce = hashlib.sha256(b"GodiNavi PAK nonce\0" + package_name.encode("utf-8") + payload).digest()[:12]
        header = ENCRYPTED_MAGIC + salt + nonce
        payload = header + AESGCM(_derive_key(salt)).encrypt(nonce, payload, header)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".new")
    try:
        temporary.write_bytes(payload)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return manifest


class PakReader:
    """Validate a PAK eagerly and expose verified in-memory asset reads."""

    def __init__(self, path, expected_package=None):
        self.path = Path(path)
        self._stream = None
        raw = self.path.read_bytes()
        self.encrypted = raw.startswith(ENCRYPTED_MAGIC)
        if self.encrypted:
            minimum = len(ENCRYPTED_MAGIC) + 16 + 12 + 16
            if len(raw) < minimum:
                raise PakError("Encrypted PAK is truncated.")
            offset = len(ENCRYPTED_MAGIC)
            salt, nonce = raw[offset:offset + 16], raw[offset + 16:offset + 28]
            header, ciphertext = raw[:offset + 28], raw[offset + 28:]
            try:
                plaintext = AESGCM(_derive_key(salt)).decrypt(nonce, ciphertext, header)
            except Exception as exc:
                raise PakError("Encrypted PAK authentication failed.") from exc
            self._stream = io.BytesIO(plaintext)
            self._bundle = zipfile.ZipFile(self._stream, "r")
        else:
            self._bundle = zipfile.ZipFile(self.path, "r")
        try:
            self.manifest = self._validate(expected_package)
        except Exception:
            self._bundle.close()
            raise

    def _validate(self, expected_package):
        infos = self._bundle.infolist()
        if len(infos) > MAX_ENTRY_COUNT + 1:
            raise PakError("PAK contains too many entries.")
        names = set()
        by_name = {}
        total = 0
        for info in infos:
            name = info.filename if info.filename == PAK_MANIFEST_NAME else _safe_name(info.filename)
            folded = name.casefold()
            if folded in names:
                raise PakError(f"Duplicate PAK path: {name}")
            names.add(folded)
            if info.is_dir() or info.file_size < 0 or info.file_size > MAX_ENTRY_BYTES:
                raise PakError(f"Invalid PAK entry: {name}")
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                raise PakError("PAK expands beyond the allowed size.")
            by_name[name] = info
        if PAK_MANIFEST_NAME not in by_name:
            raise PakError("PAK manifest is missing.")
        try:
            manifest = json.loads(self._bundle.read(PAK_MANIFEST_NAME).decode("utf-8"))
        except (KeyError, UnicodeError, json.JSONDecodeError) as exc:
            raise PakError("PAK manifest is invalid.") from exc
        required = {"schemaVersion", "packageName", "entries"}
        if not isinstance(manifest, dict) or not required.issubset(manifest) or set(manifest) - required - {"developerNote"}:
            raise PakError("PAK manifest has an invalid structure.")
        if self.encrypted and manifest.get("developerNote") != DEVELOPER_NOTE:
            raise PakError("Encrypted PAK developer note is invalid.")
        if manifest["schemaVersion"] != PAK_SCHEMA_VERSION:
            raise PakError("Unsupported PAK schema.")
        if not isinstance(manifest["packageName"], str) or not manifest["packageName"]:
            raise PakError("PAK packageName is invalid.")
        if expected_package is not None and manifest["packageName"] != expected_package:
            raise PakError("PAK packageName does not match the expected component.")
        entries = manifest["entries"]
        if not isinstance(entries, dict) or not entries:
            raise PakError("PAK manifest entries are invalid.")
        if set(entries) != set(by_name) - {PAK_MANIFEST_NAME}:
            raise PakError("PAK files do not match the manifest.")
        for name, record in entries.items():
            _safe_name(name)
            if not isinstance(record, dict) or set(record) != {"size", "sha256"}:
                raise PakError(f"Invalid PAK record: {name}")
            data = self._bundle.read(name)
            if record["size"] != len(data):
                raise PakError(f"PAK size mismatch: {name}")
            if not isinstance(record["sha256"], str) or record["sha256"] != _sha256_bytes(data):
                raise PakError(f"PAK checksum mismatch: {name}")
        return manifest

    def names(self):
        return tuple(self.manifest["entries"])

    def read(self, name):
        name = _safe_name(name)
        if name not in self.manifest["entries"]:
            raise KeyError(name)
        return self._bundle.read(name)

    def close(self):
        self._bundle.close()
        if self._stream is not None:
            self._stream.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
