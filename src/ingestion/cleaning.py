from __future__ import annotations

import html
from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord

_MIN_SUMMARY_WORDS = 5
_MIN_SUMMARY_CHARS = 30


def _clean_text(text: str) -> str:
    """Normalize whitespace and unescape any remaining HTML entities."""
    return normalize_whitespace(html.unescape(text))


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a DataFrame ready for embedding and evaluation."""
    rows = []
    for r in records:
        title = _clean_text(r.title)
        summary = _clean_text(r.summary)
        if not title or not summary:
            continue
        if len(summary.split()) < _MIN_SUMMARY_WORDS:
            continue
        rows.append(
            {
                "paper_id": r.paper_id,
                "title": title,
                "summary": summary,
                "authors": r.authors,
                "categories": r.categories,
                "primary_category": r.primary_category or (r.categories[0] if r.categories else ""),
                "published": r.published,
                "updated": r.updated,
                "abs_url": r.abs_url,
                "pdf_url": r.pdf_url,
                "comment": r.comment,
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Parse dates and compute age_days
    df["published_dt"] = pd.to_datetime(df["published"], errors="coerce")
    run_ts = pd.Timestamp(run_date.date())
    df["age_days"] = (run_ts - df["published_dt"]).dt.days.clip(lower=0).fillna(0).astype(int)

    # Helper columns
    df["authors_joined"] = df["authors"].apply(
        lambda x: compact_join(x) if isinstance(x, list) else str(x or "")
    )
    df["categories_joined"] = df["categories"].apply(
        lambda x: compact_join(x) if isinstance(x, list) else str(x or "")
    )
    df["summary_chars"] = df["summary"].str.len()
    df["summary_words"] = df["summary"].str.split().str.len()

    # text_for_embedding: title + abstract + metadata context
    df["text_for_embedding"] = (
        "Title: " + df["title"]
        + "\nAbstract: " + df["summary"]
        + "\nAuthors: " + df["authors_joined"]
        + "\nCategories: " + df["categories_joined"]
        + "\nPublished: " + df["published"].fillna("")
    )

    # Deduplicate on paper_id, filter short summaries
    df = df.drop_duplicates(subset=["paper_id"])
    df = df[df["summary_chars"] >= _MIN_SUMMARY_CHARS]

    # Sort newest first
    df = df.sort_values("published_dt", ascending=False, na_position="last").reset_index(drop=True)

    return df
