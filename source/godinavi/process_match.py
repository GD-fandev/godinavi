"""Recognize the official client and versioned local combat clients."""
import re


def _is_godius(name):
    return name == "godius.exe" or re.fullmatch(r"godius_local_combat_v[0-9]+\.exe", name) is not None


def matches_game_process(actual, configured="Godius.exe"):
    actual = actual.casefold()
    names = [configured] if isinstance(configured, str) else configured
    return any(actual == name.casefold() or (_is_godius(actual) and _is_godius(name.casefold())) for name in names)
