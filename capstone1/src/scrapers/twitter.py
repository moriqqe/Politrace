"""Twitter/X scraper via Apify."""

from __future__ import annotations

import os

from apify_client import ApifyClient

from ..utils.keywords import build_contains_check
from .base import BaseScraper, console
from .progress import run_with_status_wait

ACTOR_ID = "danek/twitter-scraper-ppr"
# Rough Apify runtime hint for progress display (varies by query size)
APIFY_ESTIMATE_SEC = 45


def _first(*values):
    """Return the first non-empty value."""
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _normalize_tweet(item: dict) -> dict:
    """Map danek/twitter-scraper-ppr (and legacy) fields to our CSV schema."""
    author = item.get("author") or item.get("user") or {}
    if not isinstance(author, dict):
        author = {}

    screen_name = _first(
        author.get("screen_name"),
        author.get("userName"),
        author.get("username"),
    )
    tweet_id = _first(item.get("tweet_id"), item.get("id"), item.get("tweetId"))
    tweet_id = str(tweet_id) if tweet_id is not None else None

    url = _first(item.get("url"), item.get("twitterUrl"))
    if not url and tweet_id and screen_name:
        url = f"https://twitter.com/{screen_name}/status/{tweet_id}"

    hashtags = item.get("hashtags") or []
    if isinstance(hashtags, list):
        hashtags_str = ", ".join(str(tag) for tag in hashtags)
    else:
        hashtags_str = str(hashtags) if hashtags else ""

    return {
        "tweet_id": tweet_id,
        "date": _first(item.get("created_at"), item.get("createdAt"), item.get("date")),
        "text": _first(item.get("text"), item.get("full_text")) or "",
        "likes": _first(item.get("favorites"), item.get("likeCount"), item.get("favorite_count")) or 0,
        "retweets": _first(item.get("retweets"), item.get("retweetCount"), item.get("retweet_count")) or 0,
        "replies": _first(item.get("replies"), item.get("replyCount"), item.get("reply_count")) or 0,
        "views": _first(item.get("views"), item.get("viewCount")) or 0,
        "user_name": screen_name,
        "user_followers": _first(
            author.get("followers"),
            author.get("followers_count"),
            author.get("sub_count"),
        )
        or 0,
        "user_verified": _first(
            author.get("blue_verified"),
            author.get("isVerified"),
            author.get("verified"),
        )
        or False,
        "hashtags": hashtags_str,
        "is_retweet": item.get("isRetweet", False),
        "url": url,
        "platform": "twitter",
        "collection_date": BaseScraper.timestamp(),
    }


class TwitterScraper(BaseScraper):
    """Scrape Twitter/X posts using an Apify actor."""

    def __init__(
        self,
        apify_token: str,
        output_dir: str = "data/raw",
        max_records: int = 15000,
    ) -> None:
        super().__init__(output_dir=output_dir, max_records=max_records)
        self.apify_token = apify_token
        self.client = ApifyClient(apify_token)

    def scrape(self, query: str, max_tweets: int | None = None, **kwargs) -> list[dict]:
        """Run Apify actor for one search query and return normalized tweets."""
        limit = max_tweets or self.max_records
        run_input = {
            "query": query,
            "max_posts": limit,
            "search_type": "Latest",
        }

        console.print(
            f"Starting Apify run for {query!r} (up to {limit} posts)...",
            style="green",
        )

        def _run_actor() -> dict:
            return self.client.actor(ACTOR_ID).call(run_input=run_input)

        try:
            run = run_with_status_wait(
                f"Apify Twitter: {query!r}",
                _run_actor,
                estimate_seconds=APIFY_ESTIMATE_SEC,
            )
            dataset_id = run["defaultDatasetId"]
        except Exception as exc:
            console.print(f"Apify run failed: {exc}", style="red")
            raise

        records: list[dict] = []
        for item in self.client.dataset(dataset_id).iterate_items():
            records.append(_normalize_tweet(item))

        console.print(f"Collected {len(records)} tweets for {query!r}", style="green")
        return records

    def enrich_with_keywords(self, records: list[dict]) -> list[dict]:
        """Add mentioned_leaders and mentioned_hotspots from keyword matching."""
        for record in records:
            text = record.get("text") or ""
            matches = build_contains_check(text)
            record["mentioned_leaders"] = ", ".join(matches["leaders"])
            record["mentioned_hotspots"] = ", ".join(matches["hotspots"])
        return records


if __name__ == "__main__":
    try:
        token = os.getenv("APIFY_API_TOKEN")
        if not token:
            console.print("APIFY_API_TOKEN not set in environment", style="red")
            console.print("Check your API token in .env", style="yellow")
            raise SystemExit(1)

        scraper = TwitterScraper(token)
        results = scraper.scrape("Ukraine war", max_tweets=20)
        if results:
            console.print("First result:", style="green")
            print(results[0])
        else:
            console.print("No tweets returned.", style="yellow")
    except SystemExit:
        raise
    except Exception as exc:
        console.print(f"Scrape failed: {exc}", style="red")
        console.print("Check your APIFY_API_TOKEN in .env and network connectivity.", style="yellow")
        raise SystemExit(1) from exc
