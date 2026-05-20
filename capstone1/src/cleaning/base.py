"""Shared helpers for cleaning pipelines."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()


def derive_output_path(input_path: str) -> Path:
    """Map data/raw/foo.csv -> data/clean/foo_clean.csv."""
    path = Path(input_path)
    parts = ["clean" if part == "raw" else part for part in path.parts]
    out = Path(*parts)
    return out.parent / f"{out.stem}_clean{out.suffix}"


def log_row_counts(before: int, after: int) -> None:
    dropped = before - after
    console.print(f"  Rows before: {before}")
    console.print(f"  Rows after:  {after}")
    console.print(f"  Rows dropped: {dropped}", style="yellow")


def print_summary_table(df: pd.DataFrame, title: str) -> None:
    """Print column dtypes, null counts, and sample values."""
    table = Table(title=title)
    table.add_column("Column")
    table.add_column("Dtype")
    table.add_column("Nulls")
    table.add_column("Example")

    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        example = ""
        non_null = series.dropna()
        if len(non_null) > 0:
            example = str(non_null.iloc[0])
            if len(example) > 60:
                example = example[:57] + "..."
        table.add_row(col, str(series.dtype), str(null_count), example)

    console.print(table)
