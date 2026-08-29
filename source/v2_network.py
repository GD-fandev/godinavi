"""Bounded HTTPS access for GodiNavi v2 channel data and packages."""

from __future__ import annotations

import json
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

import certifi


JSON_LIMIT = 4 * 1024 * 1024


class NetworkError(RuntimeError):
    pass


def request(url, accept="application/octet-stream"):
    if urllib.parse.urlparse(url).scheme != "https":
        raise NetworkError("Only HTTPS downloads are allowed.")
    return urllib.request.Request(url, headers={
        "User-Agent": "GodiNavi-Updater/2.0",
        "Accept": accept,
        "Cache-Control": "no-cache",
    })


def fetch_json(url, limit=JSON_LIMIT, timeout=30):
    separator = "&" if urllib.parse.urlparse(url).query else "?"
    uncached = f"{url}{separator}_={int(time.time() * 1000)}"
    context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(
            request(uncached, "application/vnd.github.raw+json"), timeout=timeout, context=context
        ) as response:
            data = response.read(limit + 1)
    except OSError as exc:
        raise NetworkError(f"Could not download JSON: {exc}") from exc
    if len(data) > limit:
        raise NetworkError("Downloaded JSON exceeds the size limit.")
    try:
        return json.loads(data.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise NetworkError(f"Downloaded JSON is invalid: {exc}") from exc


def download(url, destination, expected_size, progress=None, timeout=120):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    context = ssl.create_default_context(cafile=certifi.where())
    downloaded = 0
    try:
        with urllib.request.urlopen(request(url), timeout=timeout, context=context) as response, destination.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > expected_size:
                    raise NetworkError("Download exceeded the manifest size.")
                output.write(chunk)
                if progress:
                    progress(downloaded, expected_size)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    if downloaded != expected_size:
        destination.unlink(missing_ok=True)
        raise NetworkError(f"Download size mismatch: expected {expected_size}, received {downloaded}.")

