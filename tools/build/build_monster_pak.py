import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "source"))

from monster_pak import PakReader, build_pak


def build(source_root, destination):
    source_root = Path(source_root).resolve()
    destination = Path(destination).resolve()
    entries = {
        path.relative_to(source_root).as_posix(): path
        for path in source_root.rglob("*") if path.is_file()
    }
    manifest = build_pak(destination, "monsterdata", entries)
    with PakReader(destination, "monsterdata") as reader:
        if set(reader.names()) != set(entries):
            raise RuntimeError("Monster PAK verification did not reproduce every source entry.")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Build and verify the GodiNavi monster database PAK.")
    parser.add_argument("--source", default=str(PROJECT_ROOT / "content-source" / "monsters"))
    parser.add_argument("--output", default=str(PROJECT_ROOT / "data" / "content" / "monsters.pak"))
    args = parser.parse_args()
    manifest = build(args.source, args.output)
    print(f"Monster PAK verified: {len(manifest['entries'])} files -> {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
