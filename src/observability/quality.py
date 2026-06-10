from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run a suite of data quality checks and save results to the quality directory."""
    total_rows = len(df)

    # --- paper_id ---
    if "paper_id" in df.columns:
        paper_id_null = int(df["paper_id"].isna().sum())
        paper_id_unique = int(df["paper_id"].nunique())
        paper_id_duplicates = max(0, total_rows - paper_id_null - paper_id_unique)
    else:
        paper_id_null = total_rows
        paper_id_unique = 0
        paper_id_duplicates = 0

    # --- title ---
    title_null = int(df["title"].isna().sum() + (df["title"] == "").sum()) if "title" in df.columns else total_rows

    # --- summary ---
    if "summary" in df.columns:
        summary_null = int(df["summary"].isna().sum() + (df["summary"] == "").sum())
        s_chars = df["summary_chars"] if "summary_chars" in df.columns else df["summary"].str.len()
        s_words = df["summary_words"] if "summary_words" in df.columns else df["summary"].str.split().str.len()
        summary_min_chars = int(s_chars.min()) if total_rows > 0 else 0
        summary_mean_chars = float(s_chars.mean()) if total_rows > 0 else 0.0
        summary_max_chars = int(s_chars.max()) if total_rows > 0 else 0
        short_by_chars = int((s_chars < 50).sum()) if total_rows > 0 else 0
        short_by_words = int((s_words < 10).sum()) if total_rows > 0 else 0
    else:
        summary_null = total_rows
        summary_min_chars = summary_max_chars = short_by_chars = short_by_words = 0
        summary_mean_chars = 0.0

    # --- text_for_embedding ---
    embed_missing = 0
    if "text_for_embedding" in df.columns and total_rows > 0:
        embed_missing = int(df["text_for_embedding"].isna().sum() + (df["text_for_embedding"] == "").sum())

    # --- freshness / age ---
    stale_rows = age_min = age_max = 0
    age_mean = 0.0
    if "age_days" in df.columns and total_rows > 0:
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
        age_min = int(df["age_days"].min())
        age_max = int(df["age_days"].max())
        age_mean = float(df["age_days"].mean())
    pct_stale = round(100.0 * stale_rows / total_rows, 1) if total_rows > 0 else 0.0

    checks: dict[str, Any] = {
        "row_count": {
            "value": total_rows,
            "threshold": 5,
            "passed": total_rows >= 5,
        },
        "paper_id_not_null": {
            "null_count": paper_id_null,
            "passed": paper_id_null == 0,
        },
        "paper_id_unique": {
            "duplicate_count": paper_id_duplicates,
            "unique_count": paper_id_unique,
            "passed": paper_id_duplicates == 0,
        },
        "title_not_null": {
            "null_or_empty_count": title_null,
            "passed": title_null == 0,
        },
        "summary_not_null": {
            "null_or_empty_count": summary_null,
            "passed": summary_null == 0,
        },
        "summary_length": {
            "min_chars": summary_min_chars,
            "mean_chars": round(summary_mean_chars, 1),
            "max_chars": summary_max_chars,
            "short_by_chars": short_by_chars,
            "short_by_words": short_by_words,
            "passed": short_by_chars == 0,
        },
        "text_for_embedding": {
            "missing_count": embed_missing,
            "passed": embed_missing == 0,
        },
        "freshness": {
            "stale_rows": stale_rows,
            "pct_stale": pct_stale,
            "total_rows": total_rows,
            "threshold_days": settings.freshness_threshold_days,
            "passed": stale_rows == 0,
        },
        "age_days": {
            "min": age_min,
            "max": age_max,
            "mean": round(age_mean, 1),
        },
    }

    checkable = [
        "row_count", "paper_id_not_null", "paper_id_unique",
        "title_not_null", "summary_not_null", "summary_length",
        "text_for_embedding", "freshness",
    ]
    passed = sum(1 for k in checkable if checks[k].get("passed", False))
    checks["summary"] = {
        "total_checks": len(checkable),
        "passed_checks": passed,
        "failed_checks": len(checkable) - passed,
        "overall_passed": passed == len(checkable),
    }

    output_path = settings.paths.quality_dir / f"{report_name}_quality.json"
    write_json(output_path, checks)
    return checks


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarise dataset freshness and write a JSON report."""
    from pathlib import Path

    total_rows = len(df)
    latest_published = oldest_published = ""
    stale_rows = 0

    if "published_dt" in df.columns and total_rows > 0:
        valid = df["published_dt"].dropna()
        if len(valid) > 0:
            latest_published = str(valid.max().date())
            oldest_published = str(valid.min().date())
    elif "published" in df.columns and total_rows > 0:
        non_empty = df["published"].dropna().replace("", pd.NA).dropna()
        if len(non_empty) > 0:
            latest_published = str(non_empty.max())
            oldest_published = str(non_empty.min())

    if "age_days" in df.columns and total_rows > 0:
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())

    pct_stale = round(100.0 * stale_rows / total_rows, 1) if total_rows > 0 else 0.0

    report: dict[str, Any] = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "pct_stale": pct_stale,
        "total_rows": total_rows,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": stale_rows == 0,
    }

    write_json(Path(report_path), report)
    return report
