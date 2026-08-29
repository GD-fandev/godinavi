import json
import re
from pathlib import Path

from monster_pak import PakReader


SUPPORTED_LOCALES = ("ko", "ja", "en")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _safe_id(value, label="id"):
    text = str(value or "").strip()
    if not ID_PATTERN.fullmatch(text):
        raise ValueError(f"Invalid {label}: {text!r}")
    return text


def _unique_ids(values, label):
    result = []
    for value in values or []:
        item_id = _safe_id(value, label)
        if item_id not in result:
            result.append(item_id)
    return result


class MonsterStore:
    """JSON monster database with synchronized map/monster references."""

    def __init__(self, project_dir, prefer_pak=False):
        self.project_dir = Path(project_dir)
        self.prefer_pak = bool(prefer_pak)
        source_data = self.project_dir / "content-source" / "monsters"
        self.data_dir = source_data if source_data.exists() else self.project_dir / "monsterdata"
        self.monsters_dir = self.data_dir / "monsters"
        self.catalogs_dir = self.data_dir / "catalogs"
        source_maps = self.project_dir / "content-source" / "maps"
        self.mapdata_dir = source_maps if source_maps.exists() else self.project_dir / "mapdata"
        managed_pak = self.project_dir / "data" / "content" / "monsters.pak"
        direct_pak = self.project_dir / "content" / "monsters.pak"
        v2_pak = managed_pak if managed_pak.is_file() else direct_pak
        legacy_pak = self.project_dir / "mapdata" / "monsterdata.pak"
        self.pak_path = v2_pak if v2_pak.is_file() else legacy_pak
        self._pak = None

    def _pak_reader(self):
        if self._pak is None:
            expected = "monsters" if self.pak_path.parent.name == "content" else "monsterdata"
            self._pak = PakReader(self.pak_path, expected)
        return self._pak

    def _read_packaged_json(self, relative):
        return json.loads(self._pak_reader().read(relative).decode("utf-8"))

    def _use_packaged_data(self):
        return self.prefer_pak or (not self.monsters_dir.exists() and self.pak_path.is_file())

    @staticmethod
    def _read(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    @staticmethod
    def _write(path, payload):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    def iter_monster_paths(self):
        return sorted(self.monsters_dir.glob("*.json")) if self.monsters_dir.exists() else []

    def load_monsters(self):
        if self._use_packaged_data():
            records = []
            for name in self._pak_reader().names():
                if name.startswith("monsters/") and name.endswith(".json"):
                    payload = self._read_packaged_json(name)
                    self.validate_monster(payload)
                    records.append(payload)
            return records
        records = []
        for path in self.iter_monster_paths():
            payload = self._read(path)
            self.validate_monster(payload)
            records.append(payload)
        return records

    def get_monster(self, monster_id):
        monster_id = _safe_id(monster_id, "monster id")
        if self._use_packaged_data():
            try:
                return self._read_packaged_json(f"monsters/{monster_id}.json")
            except KeyError as exc:
                raise KeyError(f"Unknown monster: {monster_id}") from exc
        path = self.monsters_dir / f"{monster_id}.json"
        if not path.exists():
            raise KeyError(f"Unknown monster: {monster_id}")
        return self._read(path)

    def save_monster(self, record):
        normalized = self.validate_monster(record)
        monster_id = normalized["id"]
        previous = None
        try:
            previous = self.get_monster(monster_id)
        except KeyError:
            pass
        old_maps = set((previous or {}).get("mapIds", []))
        new_maps = set(normalized.get("mapIds", []))
        # Resolve every newly linked map before changing either side. This avoids
        # leaving a new monster record behind when a map ID was mistyped.
        for map_id in sorted(new_maps - old_maps):
            self._find_map_path(map_id)
        self._write(self.monsters_dir / f"{monster_id}.json", normalized)
        for map_id in sorted(old_maps - new_maps):
            self._set_map_reference(map_id, monster_id, False)
        for map_id in sorted(new_maps - old_maps):
            self._set_map_reference(map_id, monster_id, True)
        return normalized

    def link(self, monster_id, map_id):
        monster = self.get_monster(monster_id)
        map_id = _safe_id(map_id, "map id")
        self._find_map_path(map_id)
        monster["mapIds"] = _unique_ids(monster.get("mapIds", []) + [map_id], "map id")
        self.save_monster(monster)

    def unlink(self, monster_id, map_id):
        monster = self.get_monster(monster_id)
        map_id = _safe_id(map_id, "map id")
        monster["mapIds"] = [value for value in monster.get("mapIds", []) if value != map_id]
        self.save_monster(monster)

    def delete_monster(self, monster_id):
        monster = self.get_monster(monster_id)
        for map_id in list(monster.get("mapIds", [])):
            self._set_map_reference(map_id, monster["id"], False)
        (self.monsters_dir / f"{monster['id']}.json").unlink()

    def rename_monster(self, old_id, new_id):
        old_id = _safe_id(old_id, "monster id")
        new_id = _safe_id(new_id, "monster id")
        if old_id == new_id:
            return self.get_monster(old_id)
        record = self.get_monster(old_id)
        destination = self.monsters_dir / f"{new_id}.json"
        if destination.exists():
            raise ValueError(f"Monster id already exists: {new_id}")
        map_paths = [self._find_map_path(map_id) for map_id in record.get("mapIds", [])]
        renamed = dict(record)
        renamed["id"] = new_id
        # Keep the old file recoverable until all map references are updated.
        self._write(destination, renamed)
        try:
            for path in map_paths:
                map_record = self._read(path)
                map_record["monsterIds"] = _unique_ids(
                    [new_id if value == old_id else value for value in map_record.get("monsterIds", [])],
                    "monster id",
                )
                self._write(path, map_record)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        (self.monsters_dir / f"{old_id}.json").unlink()
        return renamed

    def load_catalog(self, filename):
        if filename not in {"attributes.json", "items.json", "magic_attacks.json"}:
            raise ValueError(f"Unknown catalog: {filename}")
        if self.prefer_pak or (not self.catalogs_dir.exists() and self.pak_path.is_file()):
            return self._read_packaged_json(f"catalogs/{filename}").get("items", [])
        return self._read(self.catalogs_dir / filename).get("items", [])

    def close(self):
        if self._pak is not None:
            self._pak.close()
            self._pak = None

    def save_catalog_item(self, filename, item, old_id=None):
        item_id = _safe_id(item.get("id"), "catalog item id")
        names = item.get("names", {})
        normalized = {
            "id": item_id,
            "names": {locale: str(names.get(locale, "")).strip() for locale in SUPPORTED_LOCALES},
        }
        items = self.load_catalog(filename)
        old_id = _safe_id(old_id, "catalog item id") if old_id else None
        if old_id and old_id != item_id:
            if any(existing.get("id") == item_id for existing in items):
                raise ValueError(f"Catalog id already exists: {item_id}")
            self._rename_catalog_references(filename, old_id, item_id)
        replaced = False
        result = []
        for existing in items:
            if existing.get("id") in {item_id, old_id}:
                if not replaced:
                    result.append(normalized)
                    replaced = True
            else:
                result.append(existing)
        if not replaced:
            result.append(normalized)
        self._write(self.catalogs_dir / filename, {"schemaVersion": 1, "items": result})
        return normalized

    def delete_catalog_item(self, filename, item_id):
        item_id = _safe_id(item_id, "catalog item id")
        fields = self._catalog_reference_fields(filename)
        users = [
            record["id"] for record in self.load_monsters()
            if any(item_id in record.get(field, []) for field in fields)
        ]
        if users:
            raise ValueError(f"{item_id} is used by {len(users)} monster(s): {', '.join(users[:8])}")
        items = [item for item in self.load_catalog(filename) if item.get("id") != item_id]
        self._write(self.catalogs_dir / filename, {"schemaVersion": 1, "items": items})

    @staticmethod
    def _catalog_reference_fields(filename):
        return {
            "attributes.json": ("attackAttributeIds", "weaknessAttributeIds"),
            "items.json": ("dropItemIds",),
            "magic_attacks.json": ("magicAttackIds",),
        }[filename]

    def _rename_catalog_references(self, filename, old_id, new_id):
        for record in self.load_monsters():
            changed = False
            for field in self._catalog_reference_fields(filename):
                values = record.get(field, [])
                replaced = [new_id if value == old_id else value for value in values]
                if replaced != values:
                    record[field] = _unique_ids(replaced, "catalog item id")
                    changed = True
            if changed:
                self._write(self.monsters_dir / f"{record['id']}.json", record)

    def validate_monster(self, record):
        if not isinstance(record, dict):
            raise ValueError("Monster record must be an object")
        result = dict(record)
        result["schemaVersion"] = 1
        result["id"] = _safe_id(result.get("id"), "monster id")
        names = result.get("names") or {}
        if not isinstance(names, dict):
            raise ValueError("names must be an object")
        result["names"] = {locale: str(names.get(locale, "")).strip() for locale in SUPPORTED_LOCALES}
        number = result.get("no")
        if number in (None, ""):
            result["no"] = None
        else:
            if isinstance(number, bool) or not re.fullmatch(r"[+-]?\d+", str(number).strip()):
                raise ValueError("monster no must be an integer")
            result["no"] = int(number)
        result["aliases"] = {
            locale: [str(value).strip() for value in (result.get("aliases", {}).get(locale, []) or []) if str(value).strip()]
            for locale in SUPPORTED_LOCALES
        }
        result["mapIds"] = _unique_ids(result.get("mapIds", []), "map id")
        result["attackAttributeIds"] = _unique_ids(result.get("attackAttributeIds", []), "attribute id")
        result["weaknessAttributeIds"] = _unique_ids(result.get("weaknessAttributeIds", []), "attribute id")
        result["dropItemIds"] = _unique_ids(result.get("dropItemIds", []), "item id")
        result["magicAttackIds"] = _unique_ids(result.get("magicAttackIds", []), "magic attack id")
        result.setdefault("magicAttack", None)
        result.setdefault("image", "")
        result.setdefault("notes", {locale: "" for locale in SUPPORTED_LOCALES})
        result.setdefault("research", {"status": "draft", "contributors": [], "sources": []})
        return result

    def _find_map_path(self, map_id):
        map_id = _safe_id(map_id, "map id")
        matches = []
        for path in self.mapdata_dir.rglob("*.json"):
            try:
                if str(self._read(path).get("id")) == map_id:
                    matches.append(path)
            except (ValueError, OSError, AttributeError):
                continue
        if len(matches) != 1:
            raise KeyError(f"Expected one map for {map_id!r}, found {len(matches)}")
        return matches[0]

    def _set_map_reference(self, map_id, monster_id, enabled):
        path = self._find_map_path(map_id)
        record = self._read(path)
        monster_ids = _unique_ids(record.get("monsterIds", []), "monster id")
        if enabled and monster_id not in monster_ids:
            monster_ids.append(monster_id)
        if not enabled:
            monster_ids = [value for value in monster_ids if value != monster_id]
        record["monsterIds"] = monster_ids
        self._write(path, record)

    def audit(self):
        errors = []
        monsters = {record["id"]: record for record in self.load_monsters()}
        maps = {}
        for path in self.mapdata_dir.rglob("*.json"):
            try:
                record = self._read(path)
                if isinstance(record, dict) and record.get("id"):
                    maps[str(record["id"])] = record
            except (ValueError, OSError):
                continue
        for monster_id, monster in monsters.items():
            for map_id in monster.get("mapIds", []):
                if map_id not in maps:
                    errors.append(f"{monster_id}: unknown map {map_id}")
                elif monster_id not in maps[map_id].get("monsterIds", []):
                    errors.append(f"{monster_id} -> {map_id}: missing reverse reference")
        for map_id, record in maps.items():
            for monster_id in record.get("monsterIds", []):
                if monster_id not in monsters:
                    errors.append(f"{map_id}: unknown monster {monster_id}")
                elif map_id not in monsters[monster_id].get("mapIds", []):
                    errors.append(f"{map_id} -> {monster_id}: missing reverse reference")
        return errors
