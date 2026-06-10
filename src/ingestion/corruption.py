from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from core.utils import write_json

_SEED = 42


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply six types of synthetic data corruption to simulate real-world data quality issues.

    Types applied:
    1. Drop latest records   → data loss / freshness gap
    2. Blank summaries       → missing content
    3. Noise injection       → semantic corruption
    4. Truncate titles       → broken metadata
    5. Stale dates           → freshness violations
    6. Duplicate rows        → inflated counts
    """
    rng = random.Random(_SEED)
    corrupted = df.copy()
    n_original = len(df)
    log: list[dict] = []

    # 1. Drop the 3 most-recent records (simulates data loss at ingestion)
    if len(corrupted) > 5:
        drop_count = min(3, len(corrupted) - 5)
        drop_idx = (
            corrupted.sort_values("published_dt", ascending=False)
            .head(drop_count)
            .index.tolist()
        )
        dropped_ids = [str(corrupted.loc[i, "paper_id"]) for i in drop_idx]
        log.append({
            "type": "drop_latest",
            "count": len(drop_idx),
            "pct": round(100 * len(drop_idx) / n_original, 1),
            "paper_ids": dropped_ids,
        })
        corrupted = corrupted.drop(index=drop_idx).reset_index(drop=True)

    n = len(corrupted)

    # 2. Blank summaries on ~20% of rows (simulates missing abstract field)
    blank_count = max(1, int(n * 0.20))
    blank_idx = rng.sample(range(n), blank_count)
    for i in blank_idx:
        corrupted.at[i, "summary"] = ""
    log.append({
        "type": "blank_summary",
        "count": blank_count,
        "pct": round(100 * blank_count / n, 1),
    })

    # 3. Noise injection on ~10% of non-blanked rows (simulates garbled text)
    noise_pool = [i for i in range(n) if i not in blank_idx]
    noise_count = max(1, int(n * 0.10))
    noise_idx = rng.sample(noise_pool, min(noise_count, len(noise_pool)))
    for i in noise_idx:
        corrupted.at[i, "summary"] = (
            "CORRUPTED_DATA " + str(corrupted.at[i, "summary"]) + " [NOISE_INJECTED_XQ9Z]"
        )
    log.append({
        "type": "noise_injection",
        "count": len(noise_idx),
        "pct": round(100 * len(noise_idx) / n, 1),
    })

    # 4. Truncate titles to 10 chars on ~15% of rows (simulates truncated metadata)
    trunc_count = max(1, int(n * 0.15))
    trunc_idx = rng.sample(range(n), trunc_count)
    for i in trunc_idx:
        corrupted.at[i, "title"] = str(corrupted.at[i, "title"])[:10]
    log.append({
        "type": "truncate_title",
        "count": trunc_count,
        "pct": round(100 * trunc_count / n, 1),
    })

    # 5. Make publication dates stale (5 years old) on ~20% of rows
    stale_count = max(1, int(n * 0.20))
    stale_idx = rng.sample(range(n), stale_count)
    stale_str = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
    stale_ts = pd.Timestamp(stale_str)
    stale_age = int((pd.Timestamp.now().normalize() - stale_ts).days)
    for i in stale_idx:
        corrupted.at[i, "published"] = stale_str
        corrupted.at[i, "published_dt"] = stale_ts
        corrupted.at[i, "age_days"] = stale_age
    log.append({
        "type": "stale_dates",
        "count": stale_count,
        "pct": round(100 * stale_count / n, 1),
        "stale_date_set_to": stale_str,
    })

    # 6. Append 5 duplicate rows (simulates double-ingestion)
    dup_count = min(5, n)
    if dup_count > 0:
        dups = corrupted.head(dup_count).copy()
        corrupted = pd.concat([corrupted, dups], ignore_index=True)
        log.append({
            "type": "add_duplicates",
            "count": dup_count,
            "pct": round(100 * dup_count / n, 1),
        })

    # Rebuild derived columns
    corrupted["summary"] = corrupted["summary"].fillna("")
    corrupted["summary_chars"] = corrupted["summary"].str.len()
    corrupted["summary_words"] = corrupted["summary"].str.split().str.len().fillna(0).astype(int)
    corrupted["text_for_embedding"] = (
        "Title: " + corrupted["title"].fillna("")
        + "\nAbstract: " + corrupted["summary"]
        + "\nAuthors: " + corrupted["authors_joined"].fillna("")
        + "\nCategories: " + corrupted["categories_joined"].fillna("")
        + "\nPublished: " + corrupted["published"].fillna("")
    )

    write_json(
        Path(output_log_path),
        {
            "original_rows": n_original,
            "corrupted_rows": len(corrupted),
            "net_change": len(corrupted) - n_original,
            "corruption_types": len(log),
            "corruptions": log,
        },
    )

    return corrupted
