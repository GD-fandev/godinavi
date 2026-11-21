"""GodiNavi Core entry point."""

import argparse
import json
import sys
from pathlib import Path

from godinavi import __version__
from v2_core_health import write_health_token


def run():
    if "--equipment-catalog" in sys.argv[1:]:
        parser = argparse.ArgumentParser()
        parser.add_argument("--equipment-catalog", action="store_true")
        parser.add_argument("--project-dir", required=True)
        parser.add_argument("--language", choices=("KR", "JP", "EN"), default="KR")
        args = parser.parse_args()
        from godinavi.armor_catalog_host import ensure_catalog_stdio, run_catalog_process
        ensure_catalog_stdio()
        try:
            run_catalog_process(args.project_dir, args.language)
        except Exception as exc:
            print(json.dumps({'action': 'error', 'message': str(exc)}), flush=True)
            return 1
        return 0
    if "--v2-health-check" not in sys.argv[1:]:
        from godinavi.main import main
        main()
        return 0
    parser = argparse.ArgumentParser()
    parser.add_argument("--v2-health-check", action="store_true")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--health-token", required=True)
    args = parser.parse_args()
    state = json.loads(Path(args.state_file).read_text(encoding="utf-8-sig"))
    executable = Path(sys.executable).resolve()
    install_root = executable.parents[2] if executable.parent.name.lower() == "app" else Path.cwd()
    write_health_token(args.health_token, install_root, state, __version__)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
