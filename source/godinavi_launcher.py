"""GodiNavi Core entry point."""

import argparse
import json
import sys
from pathlib import Path

from godinavi import __version__
from godinavi.main import main
from v2_core_health import write_health_token


def run():
    if "--v2-health-check" not in sys.argv[1:]:
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
