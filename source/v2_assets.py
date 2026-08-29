"""Read installed V2 assets from verified PAK components with source-tree fallback."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path, PurePosixPath

from v2_pak import PakReader


PAK_ROUTES = (
    ("assets/monsters/", "content/monsters.pak", "monsters", "images/"),
    ("maps/monsters/", "content/monsters.pak", "monsters", "images/"),
    ("maps/", "content/maps.pak", "maps", "maps/"),
    ("assets/icons/", "assets/ui.pak", "ui", "icons/"),
    ("assets/fonts/", "assets/ui.pak", "ui", "fonts/"),
    ("assets/buff_timer/", "assets/ui.pak", "ui", "buff_timer/"),
    ("assets/durability/", "assets/ui.pak", "ui", "durability/"),
    ("assets/map_ocr/", "assets/ui.pak", "ui", "map_ocr/"),
    ("assets/chat.mp3", "assets/audio.pak", "audio", "chat.mp3"),
    ("assets/warn.mp3", "assets/audio.pak", "audio", "warn.mp3"),
)


def _normalized_relative(value):
    text = str(value).replace("\\", "/").lstrip("/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe asset path: {value}")
    return path.as_posix()


class V2AssetStore:
    def __init__(self, resource_root):
        self.resource_root = Path(resource_root)
        self._readers = {}

    def _route(self, relative):
        for prefix, pak_name, package_name, internal_prefix in PAK_ROUTES:
            if relative == prefix or relative.startswith(prefix):
                suffix = relative[len(prefix):]
                internal = internal_prefix + suffix if prefix.endswith("/") else internal_prefix
                return pak_name, package_name, internal
        return None

    def _source_fallback(self, relative):
        """Resolve editable assets kept outside the public source tree."""
        legacy = self.resource_root / Path(relative)
        if legacy.is_file():
            return legacy
        private = self.resource_root / "private" / "content-source"
        if relative.startswith("maps/monsters/"):
            return private / "monster-images" / relative.removeprefix("maps/monsters/")
        if relative.startswith("assets/monsters/"):
            return private / "monster-images" / relative.removeprefix("assets/monsters/")
        if relative.startswith("maps/"):
            return private / "map-images" / relative.removeprefix("maps/")
        if relative.startswith("assets/"):
            return private / "runtime" / "assets" / relative.removeprefix("assets/")
        return self.resource_root / Path(relative)

    def read(self, relative):
        relative = _normalized_relative(relative)
        route = self._route(relative)
        if route:
            pak_name, package_name, internal = route
            pak_path = self.resource_root / pak_name
            if pak_path.is_file():
                reader = self._readers.get(pak_name)
                if reader is None:
                    reader = PakReader(pak_path, package_name)
                    self._readers[pak_name] = reader
                return reader.read(internal)
        return self._source_fallback(relative).read_bytes()

    def exists(self, relative):
        relative = _normalized_relative(relative)
        route = self._route(relative)
        if route:
            pak_name, package_name, internal = route
            pak_path = self.resource_root / pak_name
            if pak_path.is_file():
                try:
                    reader = self._readers.get(pak_name)
                    if reader is None:
                        reader = PakReader(pak_path, package_name)
                        self._readers[pak_name] = reader
                    return internal in reader.names()
                except (OSError, ValueError):
                    return False
        return self._source_fallback(relative).is_file()

    def open(self, relative):
        return BytesIO(self.read(relative))

    def close(self):
        for reader in self._readers.values():
            reader.close()
        self._readers.clear()

