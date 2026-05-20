"""Instagram scraper via Apify."""

from __future__ import annotations

import os

from apify_client import ApifyClient

from ..utils.keywords import build_contains_check
from .base import BaseScraper, console
from .progress import run_with_status_wait

APIFY_ESTIMATE_SEC = 90

ACTOR_ID = "apify/instagram-scraper"


class InstagramScraper(BaseScraper):
    """Scrape Instagram posts using an Apify actor."""

    def __init__(
        self,
        apify_token: str,
        output_dir: str = "data/raw",
        max_records: int = 1500,
    ) -> None:
        super().__init__(output_dir=output_dir, max_records=max_records)
        self.apify_token = apify_token
        self.client = ApifyClient(apify_token)

    def scrape(
        self,
        query: str,
        scrape_type: str = "hashtag",
        max_posts: int | None = None,
        **kwargs,
    ) -> list[dict]:
        """Run Apify actor for a hashtag or profile query."""
        limit = max_posts or self.max_records

        if scrape_type == "hashtag":
            run_input = {
                "hashtags": [query],
                "resultsType": "posts",
                "resultsLimit": limit,
            }
        elif scrape_type == "profile":
            run_input = {
                "usernames": [query],
                "resultsType": "posts",
                "resultsLimit": limit,
            }
        else:
            console.print(f"Unknown scrape_type: {scrape_type!r}", style="red")
            raise ValueError(f"Unknown scrape_type: {scrape_type}")

        console.print(
            f"Starting Apify run ({scrape_type}) for {query!r} (up to {limit} posts)...",
            style="green",
        )

        def _run_actor() -> dict:
            return self.client.actor(ACTOR_ID).call(run_input=run_input)

        try:
            run = run_with_status_wait(
                f"Apify Instagram: {query!r}",
                _run_actor,
                estimate_seconds=APIFY_ESTIMATE_SEC,
            )
            dataset_id = run["defaultDatasetId"]
        except Exception as exc:
            console.print(f"Apify run failed: {exc}", style="red")
            raise

        records: list[dict] = []
        for item in self.client.dataset(dataset_id).iterate_items():
            records.append(
                {
                    "post_id": item.get("id"),
                    "taken_at": item.get("timestamp"),
                    "caption": item.get("caption", ""),
                    "like_count": item.get("likesCount", 0),
                    "comment_count": item.get("commentsCount", 0),
                    "user_name": item.get("ownerUsername"),
                    "user_followers": item.get("ownerFollowersCount", 0),
                    "user_is_verified": item.get("ownerIsVerified", False),
                    "hashtags": ", ".join(item.get("hashtags") or []),
                    "media_type": item.get("type", "Image"),
                    "url": item.get("url"),
                    "display_url": item.get("displayUrl"),
                    "platform": "instagram",
                    "collection_date": BaseScraper.timestamp(),
                }
            )

        console.print(f"Collected {len(records)} posts for {query!r}", style="green")
        return records

    def enrich_with_keywords(self, records: list[dict]) -> list[dict]:
        """Add mentioned_leaders and mentioned_hotspots from caption keyword matching."""
        for record in records:
            text = record.get("caption") or ""
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

        scraper = InstagramScraper(token)
        results = scraper.scrape("ukraine", scrape_type="hashtag", max_posts=10)
        if results:
            console.print("First result:", style="green")
            print(results[0])
        else:
            console.print("No posts returned.", style="yellow")
    except SystemExit:
        raise
    except Exception as exc:
        console.print(f"Scrape failed: {exc}", style="red")
        console.print("Check your APIFY_API_TOKEN in .env and network connectivity.", style="yellow")
        raise SystemExit(1) from exc
