import json
import re
import ssl
import urllib.request

import certifi


APP_VERSION = "1.2.2"
LATEST_RELEASE_API = "https://api.github.com/repos/GD-fandev/godinavi/releases/latest"
USER_AGENT = "GodiNavi-VersionChecker/1.0"
RELEASE_DOWNLOAD_PREFIX = "https://github.com/GD-fandev/godinavi/releases/download/"
EXE_ASSET_NAME = "GodiNavi.exe"
CHECKSUM_ASSET_NAME = "GodiNavi.exe.sha256"


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
    assets = {str(item.get("name", "")): item for item in data.get("assets", []) if isinstance(item, dict)}
    exe = assets.get(EXE_ASSET_NAME, {})
    checksum = assets.get(CHECKSUM_ASSET_NAME, {})
    exe_url = str(exe.get("browser_download_url", ""))
    checksum_url = str(checksum.get("browser_download_url", ""))
    if exe_url and not exe_url.startswith(RELEASE_DOWNLOAD_PREFIX):
        raise ValueError("Invalid executable download URL.")
    if checksum_url and not checksum_url.startswith(RELEASE_DOWNLOAD_PREFIX):
        raise ValueError("Invalid checksum download URL.")
    return {
        "version": tag.lstrip("v"),
        "url": url,
        "body": str(data.get("body", "")),
        "exe_url": exe_url,
        "checksum_url": checksum_url,
        "size": int(exe.get("size", 0) or 0),
    }


def is_newer_version(latest, current=APP_VERSION):
    return version_tuple(latest) > version_tuple(current)


def extract_patch_notes(body, language):
    text = str(body or "").replace("\r\n", "\n")
    code = language if language in ("KR", "JP", "EN") else "EN"
    sections = {}
    marker = re.compile(r"<!--\s*(KR|JP|EN)\s*-->", re.IGNORECASE)
    matches = list(marker.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).upper()] = text[match.end():end].strip()
    if sections:
        return sections.get(code) or sections.get("EN") or next(iter(sections.values()))
    return text.strip()
