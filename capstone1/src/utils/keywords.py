# keywords.yaml - leaders, hotspots, channels

from __future__ import annotations

from pathlib import Path

import yaml

_DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "keywords.yaml"


def load_keywords(config_path: str = "config/keywords.yaml") -> dict:
    path = Path(config_path)
    if not path.is_absolute():
        path = _DEFAULT_CONFIG.parent.parent / path
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_search_queries(platform: str) -> list[str]:
    config = load_keywords()
    queries = config.get("search_queries", {}).get(platform, [])
    return list(queries)


_VALID_TELEGRAM_CATEGORIES = (
    "russian_state",
    "ukrainian",
    "western",
    "osint_trackers",
    "middle_east",
    "all",
)


def get_telegram_channels(category: str = "all") -> list[str]:
    config = load_keywords()
    channels = config.get("telegram_channels", {})
    if category == "all":
        seen: set[str] = set()
        result: list[str] = []
        for names in channels.values():
            for name in names:
                if name not in seen:
                    seen.add(name)
                    result.append(name)
        return result
    if category not in channels:
        valid = ", ".join(_VALID_TELEGRAM_CATEGORIES)
        raise ValueError(f"unknown category {category!r}; valid options: {valid}")
    return list(channels[category])


def get_channel_camp(username: str) -> str:
    config = load_keywords()
    channels = config.get("telegram_channels", {})
    for camp, names in channels.items():
        if username in names:
            return camp
    return "unknown"


def build_contains_check(text: str) -> dict[str, list[str]]:
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
    all_channels = get_telegram_channels("all")
    camps = ("russian_state", "ukrainian", "western", "osint_trackers", "middle_east")

    print("Keywords config summary")
    print(f"  Leaders: {len(leaders)}")
    print(f"  Hotspots: {len(hotspots)}")
    print(f"  Twitter queries: {len(twitter)}")
    print("  Telegram channels by camp:")
    for camp in camps:
        print(f"    {camp}: {len(get_telegram_channels(camp))}")
    print(f"  Telegram channels (all): {len(all_channels)}")
    print()
    print("Sample contains check:")
    sample = "Trump discussed Ukraine ceasefire with NATO allies."
    matches = build_contains_check(sample)
    print(f"  Text: {sample!r}")
    print(f"  leaders: {matches['leaders']}")
    print(f"  hotspots: {matches['hotspots']}")
