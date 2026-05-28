# clean twitter csv

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import console, derive_output_path, log_row_counts, print_summary_table

NUMERIC_COLS = ["likes", "retweets", "replies", "views", "user_followers"]


def _dedupe_tweets(df: pd.DataFrame) -> pd.DataFrame:
    # dedupe by tweet_id when present else text+date
    if "tweet_id" not in df.columns:
        return df.drop_duplicates(subset=["text", "date"], keep="first")

    ids = df["tweet_id"].astype("string")
    populated = ids.notna() & (ids.str.strip() != "")

    if populated.any():
        with_id = df[populated].drop_duplicates(subset=["tweet_id"], keep="first")
        without_id = df[~populated]
        if len(without_id):
            without_id = without_id.drop_duplicates(subset=["text", "date"], keep="first")
        return pd.concat([with_id, without_id], ignore_index=True)

    return df.drop_duplicates(subset=["text", "date"], keep="first")


def clean_twitter(input_path: str, output_path: str | None = None) -> str:
    in_path = Path(input_path)
    out_path = Path(output_path) if output_path else derive_output_path(input_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold]Cleaning Twitter:[/bold] {in_path}")
    df = pd.read_csv(in_path)
    before = len(df)

    df = df.dropna(subset=["text"])
    df = df[df["text"].astype(str).str.strip() != ""]
    df = _dedupe_tweets(df)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = df[col].astype(int)

    df["text"] = df["text"].astype(str).str.strip()
    df["source_type"] = "api_scrape"

    after = len(df)
    log_row_counts(before, after)
    print_summary_table(df, "Twitter — cleaned data summary")

    df.to_csv(out_path, index=False)
    console.print(f"Saved to {out_path}", style="green")
    return str(out_path.resolve())
