"""Manual coordinates require an explicit legacy opt-in, including old configs."""


def legacy_enabled(config):
    return config.get("legacy_ocr_regions") is True
