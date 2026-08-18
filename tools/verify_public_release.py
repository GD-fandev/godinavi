import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
PRIVATE_ENDPOINT = PROJECT_DIR / "private" / "party-endpoint.json"
SOURCE_DIR = PROJECT_DIR / "source"
FORBIDDEN_PUBLIC_MARKERS = (
    "dudals64",
    "/volume2/",
    "CLOUDFLARE_TUNNEL_TOKEN",
)


def main():
    try:
        endpoint = str(json.loads(PRIVATE_ENDPOINT.read_text(encoding="utf-8"))["server_url"]).strip().rstrip("/")
    except (OSError, KeyError, TypeError, ValueError) as error:
        print(f"Invalid private party endpoint configuration: {error}")
        return 1
    if not endpoint.startswith("https://"):
        print("The private party endpoint must use HTTPS.")
        return 1
    forbidden = (endpoint, *FORBIDDEN_PUBLIC_MARKERS)
    exposures = []
    for path in SOURCE_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker and marker in text:
                exposures.append(f"{path.relative_to(PROJECT_DIR)}: {marker}")
    if exposures:
        print("Private server information was found in public Python sources:")
        for exposure in exposures:
            print(f"  {exposure}")
        return 1
    print("Public source privacy check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
