import json
import re
import ssl
import urllib.request

import certifi


APP_VERSION = "1.1.0"
LATEST_RELEASE_API = "https://api.github.com/repos/GD-fandev/godinavi/releases/latest"
USER_AGENT = "GodiNavi-VersionChecker/1.0"


def version_tuple(value):
    numbers = re.findall(r"\d+", str(value))
    return tuple(int(number) for number in numbers[:3]) + (0,) * max(0, 3 - len(numbers))


def fetch_latest_release(timeout=15):
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        payload = response.read(1024 * 1024 + 1)
    if len(payload) > 1024 * 1024:
        raise ValueError("Release information is too large.")
    data = json.loads(payload.decode("utf-8"))
    tag = str(data.get("tag_name", ""))
    url = str(data.get("html_url", ""))
    if not re.fullmatch(r"v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", tag):
        raise ValueError("Invalid release version.")
    if not url.startswith("https://github.com/GD-fandev/godinavi/releases/"):
        raise ValueError("Invalid release URL.")
    return {"version": tag.lstrip("v"), "url": url}


def is_newer_version(latest, current=APP_VERSION):
    return version_tuple(latest) > version_tuple(current)
