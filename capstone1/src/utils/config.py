"""Collection limits and settings from environment."""

from __future__ import annotations

import os

_DEFAULTS = {
    "twitter": 1500,
    "instagram": 1500,
    "telegram": 10000,
}

_ENV_KEYS = {
    "twitter": "MAX_RECORDS_TWITTER",
    "instagram": "MAX_RECORDS_INSTAGRAM",
    "telegram": "MAX_RECORDS_TELEGRAM",
}


def get_max_records(platform: str) -> int:
    """Return per-platform record cap (env override, then built-in defaults)."""
    env_key = _ENV_KEYS.get(platform)
    if env_key and os.getenv(env_key):
        return int(os.getenv(env_key))
    return _DEFAULTS.get(platform, 10000)
