"""CLI application for Capstone 1 data collection."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional

import pandas as pd
import typer
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table

from .cleaning import clean_instagram, clean_telegram, clean_twitter
from .scrapers.base import console
from .scrapers.instagram import InstagramScraper
from .scrapers.telegram import TelegramScraper
from .scrapers.twitter import TwitterScraper
from .utils.config import get_max_records
from .utils.enrichment import enrich_all
from .utils.keywords import get_search_queries, get_telegram_channels

__version__ = "0.1.0"

app = typer.Typer(
    name="capstone1",
    help="Political Discourse Data Collector — scrape and clean social media data.",
    epilog="""
Examples:
  python main.py scrape twitter --defaults --max 1500
  python main.py scrape instagram --query ukraine --query gaza
  python main.py scrape telegram --category western
  python main.py scrape all
  python main.py clean all
""",
    rich_markup_mode="rich",
)

scrape_app = typer.Typer(help="Scrape data from social platforms.")
clean_app = typer.Typer(help="Clean raw scraped CSV files.")
app.add_typer(scrape_app, name="scrape")
app.add_typer(clean_app, name="clean")


def _print_banner() -> None:
    console.print(
        Panel(
            "[bold]Capstone 1[/bold]\n"
            "Political Discourse Data Collector\n"
            "Twitter/Instagram: 1,500 · Telegram: 10,000 (defaults)",
            title="Capstone 1",
            border_style="green",
        )
    )


def _merge_queries(
    platform: str,
    queries: Optional[List[str]],
    use_defaults: bool,
) -> list[str]:
    merged: list[str] = []
    if use_defaults:
        merged.extend(get_search_queries(platform))
    if queries:
        merged.extend(queries)
    seen: set[str] = set()
    unique: list[str] = []
    for q in merged:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique


def _load_records_from_csv(path: str) -> list[dict]:
    csv_path = Path(path)
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return []
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return []
    if df.empty:
        return []
    return df.to_dict(orient="records")


def _resolve_max(platform: str, cli_max: int | None) -> int:
    if cli_max is not None:
        return cli_max
    return get_max_records(platform)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
        is_eager=True,
    ),
) -> None:
    """Capstone 1 — Political Discourse Data Collector."""
    if version:
        console.print(f"Capstone 1 v{__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()
    _print_banner()


@scrape_app.command("twitter")
def scrape_twitter(
    queries: Optional[List[str]] = typer.Option(
        None, "--query", "-q", help="Search queries (can pass multiple)"
    ),
    max_records: Optional[int] = typer.Option(
        None, "--max", "-m", help="Cap total records (default: 1500 from .env)"
    ),
    output_prefix: str = typer.Option("twitter", "--output", "-o"),
    use_defaults: bool = typer.Option(
        True, "--defaults/--no-defaults", help="Use default queries from keywords.yaml"
    ),
) -> None:
    """Scrape Twitter/X via Apify and save enriched raw CSV."""
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        console.print("APIFY_API_TOKEN not set in .env", style="red")
        raise typer.Exit(1)

    limit = _resolve_max("twitter", max_records)
    query_list = _merge_queries("twitter", queries, use_defaults)
    if not query_list:
        console.print("No queries provided.", style="red")
        raise typer.Exit(1)

    console.print(f"Twitter target: {limit:,} records across {len(query_list)} queries", style="green")
    scraper = TwitterScraper(token, max_records=limit)
    raw_path = scraper.scrape_and_save(
        query_list, output_prefix, limit_key="max_tweets"
    )
    if not raw_path:
        console.print("No records collected; skipping enrichment.", style="yellow")
        raise typer.Exit(1)
    records = _load_records_from_csv(raw_path)
    if not records:
        console.print("No records collected; skipping enrichment.", style="yellow")
        raise typer.Exit(1)
    enriched = enrich_all(records, text_field="text")
    out_path = scraper.save(enriched, f"{output_prefix}_raw")
    console.print(
        f"Twitter scrape complete: {len(enriched):,} records → {out_path}",
        style="green",
    )


@scrape_app.command("instagram")
def scrape_instagram(
    queries: Optional[List[str]] = typer.Option(
        None, "--query", "-q", help="Hashtags or profiles (can pass multiple)"
    ),
    max_records: Optional[int] = typer.Option(
        None, "--max", "-m", help="Cap total records (default: 1500 from .env)"
    ),
    output_prefix: str = typer.Option("instagram", "--output", "-o"),
    use_defaults: bool = typer.Option(
        True, "--defaults/--no-defaults", help="Use default queries from keywords.yaml"
    ),
) -> None:
    """Scrape Instagram via Apify and save enriched raw CSV."""
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        console.print("APIFY_API_TOKEN not set in .env", style="red")
        raise typer.Exit(1)

    limit = _resolve_max("instagram", max_records)
    query_list = _merge_queries("instagram", queries, use_defaults)
    if not query_list:
        console.print("No queries provided.", style="red")
        raise typer.Exit(1)

    console.print(f"Instagram target: {limit:,} records across {len(query_list)} queries", style="green")
    scraper = InstagramScraper(token, max_records=limit)
    raw_path = scraper.scrape_and_save(
        query_list, output_prefix, limit_key="max_posts"
    )
    if not raw_path:
        console.print("No records collected; skipping enrichment.", style="yellow")
        raise typer.Exit(1)
    records = _load_records_from_csv(raw_path)
    if not records:
        console.print("No records collected; skipping enrichment.", style="yellow")
        raise typer.Exit(1)
    enriched = enrich_all(records, text_field="caption")
    out_path = scraper.save(enriched, f"{output_prefix}_raw")
    console.print(
        f"Instagram scrape complete: {len(enriched):,} records → {out_path}",
        style="green",
    )


@scrape_app.command("telegram")
def scrape_telegram(
    channels: Optional[List[str]] = typer.Option(None, "--channel", "-c"),
    category: str = typer.Option(
        "all",
        "--category",
        help="all | pro_kremlin | western | neutral_trackers",
    ),
    max_records: Optional[int] = typer.Option(
        None, "--max", "-m", help="Cap total records (default: 10000 from .env)"
    ),
    output_prefix: str = typer.Option("telegram", "--output", "-o"),
) -> None:
    """Scrape Telegram channels via Telethon and save enriched raw CSV."""
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    phone = os.getenv("TELEGRAM_PHONE")
    if not all([api_id, api_hash, phone]):
        console.print(
            "TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_PHONE must be set",
            style="red",
        )
        raise typer.Exit(1)

    limit = _resolve_max("telegram", max_records)
    channel_list = list(channels) if channels else get_telegram_channels(category)
    if not channel_list:
        console.print("No channels to scrape.", style="red")
        raise typer.Exit(1)

    console.print(
        f"Telegram target: {limit:,} messages across {len(channel_list)} channels",
        style="green",
    )
    scraper = TelegramScraper(int(api_id), api_hash, phone, max_records=limit)
    raw_path = scraper.scrape_channels(channel_list, filename_prefix=output_prefix)
    if not raw_path:
        console.print("No records collected; skipping enrichment.", style="yellow")
        raise typer.Exit(1)
    records = _load_records_from_csv(raw_path)
    if not records:
        console.print("No records collected; skipping enrichment.", style="yellow")
        raise typer.Exit(1)
    enriched = enrich_all(records, text_field="text")
    out_path = scraper.save(enriched, f"{output_prefix}_raw")
    console.print(
        f"Telegram scrape complete: {len(enriched):,} records → {out_path}",
        style="green",
    )


@scrape_app.command("all")
def scrape_all(
    twitter_max: Optional[int] = typer.Option(None, "--twitter-max", help="Twitter cap"),
    instagram_max: Optional[int] = typer.Option(None, "--instagram-max", help="Instagram cap"),
    telegram_max: Optional[int] = typer.Option(None, "--telegram-max", help="Telegram cap"),
    max_records: Optional[int] = typer.Option(
        None, "--max", "-m", help="Set same cap for all platforms (overrides per-platform)"
    ),
) -> None:
    """Run Twitter, Instagram, and Telegram scrapers in sequence."""
    tw = max_records if max_records is not None else _resolve_max("twitter", twitter_max)
    ig = max_records if max_records is not None else _resolve_max("instagram", instagram_max)
    tg = max_records if max_records is not None else _resolve_max("telegram", telegram_max)

    steps = [
        ("Twitter", lambda: scrape_twitter(max_records=tw, use_defaults=True)),
        ("Instagram", lambda: scrape_instagram(max_records=ig, use_defaults=True)),
        ("Telegram", lambda: scrape_telegram(max_records=tg)),
    ]

    with Progress(
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("All platforms", total=len(steps))
        for name, run_step in steps:
            progress.update(task, description=f"Platform: {name}")
            try:
                run_step()
            except typer.Exit:
                console.print(f"{name} scrape aborted.", style="red")
                raise
            except Exception as exc:
                console.print(f"{name} scrape failed: {exc}", style="red")
            progress.advance(task)

    console.print("All platform scrapes finished.", style="green")


@clean_app.command("all")
def clean_all(
    raw_dir: str = typer.Option("data/raw"),
    clean_dir: str = typer.Option("data/clean"),
) -> None:
    """Clean all matching raw CSV files into data/clean/."""
    raw_path = Path(raw_dir)
    clean_path = Path(clean_dir)
    clean_path.mkdir(parents=True, exist_ok=True)

    patterns = {
        re.compile(r"^twitter_.*\.csv$"): clean_twitter,
        re.compile(r"^instagram_.*\.csv$"): clean_instagram,
        re.compile(r"^telegram_.*\.csv$"): clean_telegram,
    }

    results: list[tuple[str, str, int]] = []

    for csv_file in sorted(raw_path.glob("*.csv")):
        cleaner = None
        for pattern, fn in patterns.items():
            if pattern.match(csv_file.name):
                cleaner = fn
                break
        if cleaner is None:
            continue

        out_file = clean_path / f"{csv_file.stem}_clean{csv_file.suffix}"
        console.print(f"Cleaning {csv_file.name}...", style="green")
        out = cleaner(str(csv_file), str(out_file))
        row_count = len(pd.read_csv(out))
        results.append((csv_file.name, out, row_count))

    table = Table(title="Cleaned files summary")
    table.add_column("Input")
    table.add_column("Output")
    table.add_column("Rows", justify="right")

    for inp, out, rows in results:
        table.add_row(inp, out, str(rows))

    if results:
        console.print(table)
        console.print(f"Cleaned {len(results)} file(s).", style="green")
    else:
        console.print(
            f"No matching CSV files found in {raw_path} "
            "(expected twitter_*.csv, instagram_*.csv, telegram_*.csv).",
            style="yellow",
        )
