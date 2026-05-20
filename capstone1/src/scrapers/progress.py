"""Rich progress helpers with elapsed time and ETA."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

console = Console()


def make_task_progress(description: str = "Working") -> Progress:
    """Progress bar for finite tasks (queries, channels) with ETA."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=36),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console,
        expand=False,
    )


def run_with_status_wait(
    description: str,
    func: Callable[[], Any],
    estimate_seconds: int | None = None,
) -> Any:
    """Run a blocking remote job with a status spinner (works alongside query progress)."""
    result: dict[str, Any] = {}
    error: list[BaseException] = []

    def worker() -> None:
        try:
            result["value"] = func()
        except BaseException as exc:
            error.append(exc)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    hint = f" (~{estimate_seconds}s)" if estimate_seconds else ""
    with console.status(f"[bold green]{description}{hint}", spinner="dots") as status:
        start = time.monotonic()
        while thread.is_alive():
            elapsed = int(time.monotonic() - start)
            status.update(f"[bold green]{description}{hint}[/] — {elapsed}s elapsed")
            time.sleep(0.4)
        thread.join()

    if error:
        raise error[0]
    return result["value"]
