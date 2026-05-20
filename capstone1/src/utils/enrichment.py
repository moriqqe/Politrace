"""Record enrichment: sentiment, word count, and keyword matching."""

from __future__ import annotations

from collections import Counter

from rich.console import Console
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .keywords import build_contains_check

console = Console()
_analyzer = SentimentIntensityAnalyzer()


def _get_text(record: dict, text_field: str) -> str | None:
    text = record.get(text_field)
    if text is None or not str(text).strip():
        return None
    return str(text)


def _label_from_compound(compound: float) -> str:
    if compound >= 0.05:
        return "positive"
    if compound <= -0.05:
        return "negative"
    return "neutral"


def add_sentiment(records: list[dict], text_field: str = "text") -> list[dict]:
    """Add sentiment_score and sentiment_label using VADER."""
    for record in records:
        text = _get_text(record, text_field)
        if text is None:
            record["sentiment_score"] = 0.0
            record["sentiment_label"] = "neutral"
            continue

        scores = _analyzer.polarity_scores(text)
        compound = scores["compound"]
        record["sentiment_score"] = float(compound)
        record["sentiment_label"] = _label_from_compound(compound)

    return records


def add_word_count(records: list[dict], text_field: str = "text") -> list[dict]:
    """Add word_count from whitespace-split text."""
    for record in records:
        text = _get_text(record, text_field)
        record["word_count"] = len(text.split()) if text is not None else 0

    return records


def add_keywords(records: list[dict], text_field: str = "text") -> list[dict]:
    """Add mentioned_leaders and mentioned_hotspots from keyword config."""
    for record in records:
        text = _get_text(record, text_field)
        if text is None:
            record["mentioned_leaders"] = ""
            record["mentioned_hotspots"] = ""
            continue

        matches = build_contains_check(text)
        record["mentioned_leaders"] = ", ".join(matches["leaders"])
        record["mentioned_hotspots"] = ", ".join(matches["hotspots"])

    return records


def enrich_all(records: list[dict], text_field: str = "text") -> list[dict]:
    """Apply sentiment, word count, and keyword enrichment; print summary."""
    enriched = add_sentiment(records, text_field=text_field)
    enriched = add_word_count(enriched, text_field=text_field)
    enriched = add_keywords(enriched, text_field=text_field)

    total = len(enriched)
    scores = [r.get("sentiment_score", 0.0) for r in enriched]
    avg_score = sum(scores) / total if total else 0.0

    distribution = Counter(r.get("sentiment_label", "neutral") for r in enriched)
    leader_counts: Counter[str] = Counter()
    for record in enriched:
        leaders = record.get("mentioned_leaders") or ""
        for name in leaders.split(", "):
            if name:
                leader_counts[name] += 1

    console.print("\n[bold]Enrichment summary[/bold]")
    console.print(f"  Total records: {total}")
    console.print(f"  Avg sentiment score: {avg_score:.4f}")
    console.print(
        "  Sentiment distribution: "
        f"positive={distribution.get('positive', 0)}, "
        f"neutral={distribution.get('neutral', 0)}, "
        f"negative={distribution.get('negative', 0)}"
    )
    if leader_counts:
        top_leaders = leader_counts.most_common(5)
        leaders_str = ", ".join(f"{name} ({count})" for name, count in top_leaders)
        console.print(f"  Top mentioned leaders: {leaders_str}")
    else:
        console.print("  Top mentioned leaders: none")

    return enriched
