"""Instagram raw CSV cleaning."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import console, derive_output_path, log_row_counts, print_summary_table

NUMERIC_COLS = ["like_count", "comment_count", "user_followers"]


def clean_instagram(input_path: str, output_path: str | None = None) -> str:
    """Clean Instagram scrape CSV and save to data/clean/. Returns output path."""
    in_path = Path(input_path)
    out_path = Path(output_path) if output_path else derive_output_path(input_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold]Cleaning Instagram:[/bold] {in_path}")
    df = pd.read_csv(in_path)
    before = len(df)

    df = df.dropna(subset=["caption"])
    df["empty_caption"] = df["caption"].astype(str).str.strip() == ""

    if "post_id" in df.columns:
        df = df.drop_duplicates(subset=["post_id"], keep="first")

    df["taken_at"] = pd.to_datetime(df["taken_at"], errors="coerce")
    df = df.dropna(subset=["taken_at"])

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = df[col].astype(int)

    df["source_type"] = "api_scrape"

    after = len(df)
    log_row_counts(before, after)
    print_summary_table(df, "Instagram — cleaned data summary")

    df.to_csv(out_path, index=False)
    console.print(f"Saved to {out_path}", style="green")
    return str(out_path.resolve())
