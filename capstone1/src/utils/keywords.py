"""Load and query geopolitical keyword configuration."""

from __future__ import annotations

from pathlib import Path

import yaml

_DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "keywords.yaml"


def load_keywords(config_path: str = "config/keywords.yaml") -> dict:
    """Load and return the YAML keyword config as a dict."""
    path = Path(config_path)
    if not path.is_absolute():
        path = _DEFAULT_CONFIG.parent.parent / path
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_search_queries(platform: str) -> list[str]:
    """Return search queries for the given platform (twitter or instagram)."""
    config = load_keywords()
    queries = config.get("search_queries", {}).get(platform, [])
    return list(queries)


def get_telegram_channels(category: str = "all") -> list[str]:
    """Return Telegram channel usernames, optionally filtered by category."""
    config = load_keywords()
    channels = config.get("telegram_channels", {})
    if category == "all":
        result: list[str] = []
        for names in channels.values():
            result.extend(names)
        return result
    return list(channels.get(category, []))


def build_contains_check(text: str) -> dict[str, list[str]]:
    """Return matched leaders and hotspots found in text (case-insensitive)."""
    config = load_keywords()
    lowered = text.lower()
    return {
        "leaders": [k for k in config.get("leaders", []) if k.lower() in lowered],
        "hotspots": [k for k in config.get("hotspots", []) if k.lower() in lowered],
    }


if __name__ == "__main__":
    config = load_keywords()
    leaders = config.get("leaders", [])
    hotspots = config.get("hotspots", [])
    twitter = get_search_queries("twitter")
    instagram = get_search_queries("instagram")
    all_channels = get_telegram_channels("all")

    print("Keywords config summary")
    print(f"  Leaders: {len(leaders)}")
    print(f"  Hotspots: {len(hotspots)}")
    print(f"  Twitter queries: {len(twitter)}")
    print(f"  Instagram queries: {len(instagram)}")
    print(f"  Telegram channels (all): {len(all_channels)}")
    print()
    print("Sample contains check:")
    sample = "Trump discussed Ukraine ceasefire with NATO allies."
    matches = build_contains_check(sample)
    print(f"  Text: {sample!r}")
    print(f"  leaders: {matches['leaders']}")
    print(f"  hotspots: {matches['hotspots']}")
