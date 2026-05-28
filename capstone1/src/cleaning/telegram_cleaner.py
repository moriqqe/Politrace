# clean telegram csv

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import console, derive_output_path, log_row_counts, print_summary_table

NUMERIC_COLS = ["views", "forwards", "replies_count", "reactions_count"]


def clean_telegram(input_path: str, output_path: str | None = None) -> str:
    in_path = Path(input_path)
    out_path = Path(output_path) if output_path else derive_output_path(input_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold]Cleaning Telegram:[/bold] {in_path}")
    df = pd.read_csv(in_path)
    before = len(df)

    df = df.dropna(subset=["text"])
    df = df[df["text"].astype(str).str.strip() != ""]

    if "message_id" in df.columns and "channel_username" in df.columns:
        df = df.drop_duplicates(subset=["message_id", "channel_username"], keep="first")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = df[col].astype(int)

    df["source_type"] = "api_scrape"

    after = len(df)
    log_row_counts(before, after)
    print_summary_table(df, "Telegram — cleaned data summary")

    df.to_csv(out_path, index=False)
    console.print(f"Saved to {out_path}", style="green")
    return str(out_path.resolve())
