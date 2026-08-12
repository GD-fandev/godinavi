import json
import shutil
from pathlib import Path


def _safe_id(value):
    text = str(value or "").strip()
    if not text or not all(ch.isascii() and (ch.isalnum() or ch in "_-") for ch in text):
        raise ValueError(f"Invalid map id: {text!r}")
    return text


class MapStore:
    """Store map JSON beside the matching area folder under maps/."""

    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.data_dir = self.project_dir / "mapdata"
        # Kept as the public attribute used by the calibrator UI. JSON files
        # now live recursively below mapdata/, not in mapdata/maps/.
        self.maps_dir = self.data_dir
        self.old_maps_dir = self.data_dir / "maps"
        self.legacy_path = self.data_dir / "maps.json"
        self.backup_path = self.data_dir / "maps.legacy-backup.json"

    def iter_map_paths(self):
        if not self.data_dir.exists():
            return []
        return sorted(
            path for path in self.data_dir.rglob("*.json")
            if path.name not in {self.legacy_path.name, self.backup_path.name}
        )

    def _record_path(self, record):
        map_id = _safe_id(record.get("id"))
        image_path = Path(str(record.get("image", "")).replace("\\", "/"))
        parts = list(image_path.parts)
        area_parts = []
        for index, part in enumerate(parts):
            if part.casefold() == "maps":
                area_parts = parts[index + 1:-1]
                break
        safe_parts = [part for part in area_parts if part not in ("", ".", "..")]
        return self.data_dir.joinpath(*safe_parts, f"{map_id}.json")

    @staticmethod
    def _records_from_path(path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("maps"), list):
            return payload["maps"]
        return [payload]

    def migrate_legacy(self):
        migrated = False

        # Old single-file database support.
        if self.legacy_path.exists():
            try:
                records = self._records_from_path(self.legacy_path)
            except Exception:
                records = []
            if records:
                if not self.backup_path.exists():
                    shutil.copy2(self.legacy_path, self.backup_path)
                for record in records:
                    if isinstance(record, dict) and record.get("id"):
                        destination = self._record_path(record)
                        if not destination.exists():
                            self._write_record(destination, record)
                migrated = True

        # Previous per-map layout: mapdata/maps/<id>.json. Move each record to
        # mapdata/<area>/<id>.json using its maps/<area>/image path.
        if self.old_maps_dir.exists():
            for source in sorted(self.old_maps_dir.rglob("*.json")):
                try:
                    records = self._records_from_path(source)
                except Exception:
                    continue
                for record in records:
                    if not isinstance(record, dict) or not record.get("id"):
                        continue
                    destination = self._record_path(record)
                    if destination.resolve() == source.resolve():
                        continue
                    if not destination.exists():
                        self._write_record(destination, record)
                    source.unlink()
                    migrated = True
            for directory in sorted(self.old_maps_dir.rglob("*"), key=lambda value: len(value.parts), reverse=True):
                if directory.is_dir() and not any(directory.iterdir()):
                    directory.rmdir()
            if self.old_maps_dir.exists() and not any(self.old_maps_dir.iterdir()):
                self.old_maps_dir.rmdir()
        return migrated

    def load_maps(self):
        self.migrate_legacy()
        records = {}
        for path in self.iter_map_paths():
            try:
                for record in self._records_from_path(path):
                    if isinstance(record, dict) and record.get("id"):
                        records[str(record["id"])] = record
            except Exception:
                continue
        return list(records.values())

    def save_map(self, record):
        destination = self._record_path(record)
        self._write_record(destination, record)

        # If the image/area changed, remove another JSON carrying the same ID.
        map_id = str(record.get("id"))
        for path in self.iter_map_paths():
            if path.resolve() == destination.resolve():
                continue
            try:
                if any(str(item.get("id")) == map_id for item in self._records_from_path(path) if isinstance(item, dict)):
                    path.unlink()
            except Exception:
                continue

    def record_path(self, record):
        return self._record_path(record)

    def replace_all(self, records, old_ids=None):
        new_ids = set()
        destinations = set()
        for record in records:
            map_id = _safe_id(record.get("id"))
            if map_id in new_ids:
                raise ValueError(f"Duplicate map id: {map_id}")
            new_ids.add(map_id)
            destination = self._record_path(record)
            self._write_record(destination, record)
            destinations.add(destination.resolve())

        removable_ids = {str(value) for value in (old_ids or []) if value}
        for path in self.iter_map_paths():
            if path.resolve() in destinations:
                continue
            try:
                path_ids = {
                    str(item.get("id")) for item in self._records_from_path(path)
                    if isinstance(item, dict) and item.get("id")
                }
            except Exception:
                continue
            if path_ids & removable_ids:
                path.unlink()

    def delete_map(self, map_id):
        map_id = _safe_id(map_id)
        for path in self.iter_map_paths():
            try:
                if any(str(item.get("id")) == map_id for item in self._records_from_path(path) if isinstance(item, dict)):
                    path.unlink()
            except Exception:
                continue

    def read_import_file(self, path):
        records = self._records_from_path(path)
        for record in records:
            _safe_id(record.get("id"))
        return records

    @staticmethod
    def _write_record(path, record):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp_path.replace(path)
