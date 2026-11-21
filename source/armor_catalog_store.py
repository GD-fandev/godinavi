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

    def item_color_labels(self, item, locale):
        labels = dict(self.color_labels(item.get("category"), locale))
        overrides = item.get("color_labels", {})
        mapping = item.get("set_dye_colors") or {"0": 0, "1": 1, "2": 2, "3": 6, "4": 5}
        if item.get("category") != "shoes" or not self.uses_clothing_dyes(item):
            labels.update(overrides.get(locale) or overrides.get("ko") or {})
            return labels
        clothing = self.color_labels("armor", locale)
        for dye_id, sprite_color_id in mapping.items():
            dye, color = clothing.get(str(dye_id)), labels.get(str(sprite_color_id))
            if dye and color:
                labels[str(sprite_color_id)] = dye
        labels.update(overrides.get(locale) or overrides.get("ko") or {})
        return labels

    @staticmethod
    def uses_clothing_dyes(item):
        return (item.get("category") in {"armor", "clothes"}
                or (item.get("category") == "shoes" and bool(item.get("set_effect"))
                    and item.get("id") not in {"S0-000-19", "S1-000-19"}))

    def display_color_id(self, item, selected):
        if item.get("category") == "shoes" and self.uses_clothing_dyes(item):
            color = self.matching_shoe_color(item, selected)
            return str(color['id']) if color else None
        return selected

    def matching_set_shoes(self, item):
        if item.get("category") not in {"armor", "clothes"}:
            return []
        return [shoe for shoe in self.items() if shoe.get("category") == "shoes"
                and shoe.get("gender") == item.get("gender")
                and (shoe.get("set_effect") or {}).get("required_item", {}).get("id") == item.get("id")]

    def matching_shoe_color(self, shoe, clothing_color_id):
        mapping = shoe.get("set_dye_colors") or {"0": 0, "1": 1, "2": 2, "3": 6, "4": 5}
        color_id = mapping.get(str(clothing_color_id))
        return next((color for color in shoe.get("colors", []) if color.get("id") == color_id), None)

    def image(self, relative):
        raw = self.backend.read_bytes(relative)
        with Image.open(io.BytesIO(raw)) as source:
            return source.convert("RGBA")

    def equipped_variant_image(self, item, color):
        body = self.image(color.get("image"))
        combined = Image.new("RGBA", body.size)
        for shoe in self.matching_set_shoes(item):
            shoe_color = self.matching_shoe_color(shoe, color.get("id"))
            if shoe_color is None:
                continue
            feet = self.image(shoe_color.get("image"))
            if feet.size != body.size:
                raise ValueError("Equipment sprites must share the same coordinate canvas")
            combined.alpha_composite(feet)
        combined.alpha_composite(body)
        return combined

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
    enhancement = steps[level - 1] if level else {}
    result = {
        "ac": stats.get("ac", 0) + enhancement.get("ac", 0),
        "dc": stats.get("dc", 0) + enhancement.get("dc", 0),
        "weight": stats.get("weight", 0),
    }
    bonuses = set_effect.get("bonuses", {}) if isinstance(set_effect, dict) else {}
    for key, value in bonuses.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            result[key] = result.get(key, 0) + value
    return result
