"""Collection limits and settings from environment."""

from __future__ import annotations

import os

_DEFAULTS = {
    "twitter": 15000,
    "telegram": 15000,
}

_ENV_KEYS = {
    "twitter": "MAX_RECORDS_TWITTER",
    "telegram": "MAX_RECORDS_TELEGRAM",
}


def get_max_records(platform: str) -> int:
    """Return per-platform record cap (env override, then built-in defaults)."""
    env_key = _ENV_KEYS.get(platform)
    if env_key and os.getenv(env_key):
        return int(os.getenv(env_key))
    return _DEFAULTS.get(platform, 15000)
