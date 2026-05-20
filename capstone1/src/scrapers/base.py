"""Abstract base class for platform scrapers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from rich.console import Console

from .progress import make_task_progress

console = Console()


class BaseScraper(ABC):
    """Base scraper with shared persistence and orchestration."""

    def __init__(self, output_dir: str = "data/raw", max_records: int = 10000) -> None:
        self.output_dir = Path(output_dir)
        self.max_records = max_records
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def scrape(self, query: str, **kwargs) -> list[dict]:
        """Fetch records for a single query. Implemented by subclasses."""
        ...

    def save(self, records: list[dict], filename: str, format: str = "csv") -> str:
        """Save records to {output_dir}/{filename}.{format}. Returns full output path."""
        if format not in ("csv", "json"):
            console.print(f"Unsupported format: {format}", style="yellow")
            raise ValueError(f"Unsupported format: {format}")

        output_path = self.output_dir / f"{filename}.{format}"

        if format == "csv":
            pd.DataFrame(records).to_csv(output_path, index=False)
        else:
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, ensure_ascii=False)

        console.print(f"Saved {len(records)} records to {output_path}", style="green")
        return str(output_path.resolve())

    @staticmethod
    def _record_id(record: dict) -> str | int | None:
        for key in ("id", "tweet_id", "post_id", "message_id"):
            value = record.get(key)
            if value is not None:
                return value
        return None

    def scrape_and_save(
        self,
        queries: list[str],
        filename_prefix: str,
        limit_key: str | None = None,
        **kwargs,
    ) -> str:
        """Scrape all queries, dedupe by id, save aggregated results. Returns output path."""
        all_records: list[dict] = []
        seen_ids: set = set()

        with make_task_progress("Scraping queries") as progress:
            task = progress.add_task(
                f"Queries (target {self.max_records:,} records)",
                total=len(queries),
            )
            for index, query in enumerate(queries):
                remaining = self.max_records - len(all_records)
                if remaining <= 0:
                    break

                queries_left = len(queries) - index
                per_query = max(1, min(remaining, remaining // queries_left))
                batch_kwargs = dict(kwargs)
                if limit_key:
                    batch_kwargs[limit_key] = per_query

                progress.update(
                    task,
                    description=(
                        f"Query {index + 1}/{len(queries)}: {query!r} "
                        f"({len(all_records):,}/{self.max_records:,}) — fetching..."
                    ),
                )
                progress.stop()
                try:
                    batch = self.scrape(query, **batch_kwargs)
                except Exception as exc:
                    console.print(f"Failed query {query!r}: {exc}", style="red")
                    progress.start()
                    progress.advance(task)
                    continue
                finally:
                    if not progress.finished:
                        progress.start()

                for record in batch:
                    record_id = self._record_id(record)
                    if record_id is not None:
                        if record_id in seen_ids:
                            continue
                        seen_ids.add(record_id)
                    all_records.append(record)

                if len(all_records) >= self.max_records:
                    console.print(
                        f"Reached max_records ({self.max_records:,}), stopping early.",
                        style="yellow",
                    )
                    all_records = all_records[: self.max_records]
                    progress.advance(task)
                    break

                progress.advance(task)

        if not all_records:
            console.print("No records collected.", style="yellow")
            return ""

        return self.save(all_records, filename_prefix)

    @staticmethod
    def timestamp() -> str:
        """Return current UTC time as an ISO 8601 string."""
        return datetime.now(timezone.utc).isoformat()
