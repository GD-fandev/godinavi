import io
import json
from pathlib import Path, PurePosixPath

from PIL import Image
from v2_pak import PakReader


class DirectoryCatalogBackend:
    """Development backend. A future PAK backend only needs read_json/read_bytes."""

    def __init__(self, root):
        self.root = Path(root)

    def _path(self, relative):
        relative = PurePosixPath(str(relative))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe catalog path: {relative}")
        return self.root.joinpath(*relative.parts)

    def read_json(self, relative):
        return json.loads(self._path(relative).read_text(encoding="utf-8"))

    def read_bytes(self, relative):
        return self._path(relative).read_bytes()

    def close(self):
        pass


class PakCatalogBackend:
    def __init__(self, path):
        self.reader = PakReader(path, "equipment")

    def read_json(self, relative):
        return json.loads(self.reader.read(str(relative).replace("\\", "/")).decode("utf-8"))

    def read_bytes(self, relative):
        return self.reader.read(str(relative).replace("\\", "/"))

    def close(self):
        self.reader.close()


class ArmorCatalogStore:
    def __init__(self, project_dir=None, backend=None):
        if backend is None:
            if project_dir is None:
                raise ValueError("project_dir or backend is required")
            project_dir = Path(project_dir)
            pak_path = project_dir / "content" / "equipment.pak"
            backend = PakCatalogBackend(pak_path) if pak_path.is_file() else DirectoryCatalogBackend(project_dir / "private" / "content-source" / "equipment")
        self.backend = backend
        self.data = None

    def reload(self):
        self.data = self.backend.read_json("armor_catalog.json")
        return self.data

    def catalog(self):
        return self.data if self.data is not None else self.reload()

    def items(self):
        return list(self.catalog().get("items", []))

    def color_labels(self, category, locale):
        data = self.catalog()
        category_values = data.get("category_color_labels", {}).get(category, {})
        labels = category_values.get(locale) or category_values.get("ko")
        if not isinstance(labels, dict):
            base_values = data.get("color_labels", {})
            labels = base_values.get(locale) or base_values.get("ko", {})
        return labels if isinstance(labels, dict) else {}

    def enhancement_steps(self, category):
        profile = category if category in {"armor", "shoes"} else "clothes"
        return list(self.catalog().get("enhancement", {}).get("profiles", {}).get(profile, {}).get("steps", []))

    def image(self, relative):
        raw = self.backend.read_bytes(relative)
        with Image.open(io.BytesIO(raw)) as source:
            return source.convert("RGBA")

    def close(self):
        self.backend.close()


def localized_name(record, locale):
    names = record.get("name", {})
    return names.get(locale) or names.get("ko") or names.get("ja") or record.get("id", "")


def catalog_sort_level(item):
    if item.get("category") in {"shoes", "outfit"}:
        value = item.get("catalog_order", 0)
    else:
        value = item.get("required_level", 0)
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def filtered_items(items, query="", gender="all", category="all", locale="ko", sort_by="level_asc"):
    query = str(query).strip().casefold()
    result = []
    for item in items:
        if gender != "all" and item.get("gender") != gender:
            continue
        if category != "all" and item.get("category") != category:
            continue
        names = item.get("name", {})
        haystack = " ".join((str(item.get("id", "")), *(str(value) for value in names.values()))).casefold()
        if query and query not in haystack:
            continue
        result.append(item)
    name_key = lambda item: localized_name(item, locale).casefold()
    if sort_by == "name":
        key = lambda item: (name_key(item), catalog_sort_level(item), item.get("sprite_id", 0))
        reverse = False
    elif sort_by == "level_desc":
        key = lambda item: (catalog_sort_level(item), name_key(item), item.get("sprite_id", 0))
        reverse = True
    elif sort_by == "category":
        order = {"armor": 0, "clothes": 1, "shoes": 2, "outfit": 3}
        key = lambda item: (order.get(item.get("category"), 9), catalog_sort_level(item), name_key(item))
        reverse = False
    else:
        key = lambda item: (catalog_sort_level(item), name_key(item), item.get("sprite_id", 0))
        reverse = False
    return sorted(result, key=key, reverse=reverse)


def enhanced_stats(item, level, steps, set_effect=None):
    stats = item.get("stats")
    if not isinstance(stats, dict):
        return None
    level = max(0, min(int(level), len(steps)))
    result = {
        "ac": stats.get("ac", 0) + sum(step.get("ac", 0) for step in steps[:level]),
        "dc": stats.get("dc", 0) + sum(step.get("dc", 0) for step in steps[:level]),
        "weight": stats.get("weight", 0),
    }
    bonuses = set_effect.get("bonuses", {}) if isinstance(set_effect, dict) else {}
    for key, value in bonuses.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            result[key] = result.get(key, 0) + value
    return result
