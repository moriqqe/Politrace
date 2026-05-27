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
            author = item.get("author") or item.get("user") or {}
            if not isinstance(author, dict):
                author = {}
            records.append(
                {
                    "tweet_id": item.get("id") or item.get("tweetId"),
                    "date": item.get("createdAt") or item.get("created_at"),
                    "text": item.get("text") or item.get("full_text") or "",
                    "likes": item.get("likeCount") or item.get("favorite_count") or 0,
                    "retweets": item.get("retweetCount") or item.get("retweet_count") or 0,
                    "replies": item.get("replyCount") or item.get("reply_count") or 0,
                    "views": item.get("viewCount") or item.get("views") or 0,
                    "user_name": author.get("userName") or author.get("username"),
                    "user_followers": author.get("followers") or author.get("followers_count") or 0,
                    "user_verified": author.get("isVerified") or author.get("verified") or False,
                    "hashtags": ", ".join(item.get("hashtags") or []),
                    "is_retweet": item.get("isRetweet", False),
                    "url": item.get("url") or item.get("twitterUrl"),
                    "platform": "twitter",
                    "collection_date": BaseScraper.timestamp(),
                }
            )

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
