"""Collect the certificate policy file required by some Python distributions."""

from pathlib import Path

from PyInstaller.utils.hooks import get_module_file_attribute

ssl_directory = Path(get_module_file_attribute("ssl")).parent
policy_file = ssl_directory / "codex-rejected-cas.pem"
datas = [(str(policy_file), ".")] if policy_file.is_file() else []
