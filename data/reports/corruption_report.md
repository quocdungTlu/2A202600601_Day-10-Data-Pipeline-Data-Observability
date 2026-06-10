# Corruption & Repair Comparison Report

## Overview

This report compares pipeline performance across three dataset versions:
- **Baseline**: original clean dataset from Crossref
- **Corrupted**: dataset with 6 types of synthetic corruption applied
- **Repaired**: dataset re-ingested and re-cleaned from the original raw source

## Metrics Comparison

| Metric | Baseline | Corrupted (Δ) | Bar | Repaired (Δ) | Bar |
|--------|----------|---------------|-----|--------------|-----|
| retrieval_hit_rate | 1.000 | 0.667 -0.333 | `█████████████░░░░░░░` | 1.000 +0.000 | `████████████████████` |
| mean_token_f1 | 1.000 | 0.563 -0.437 | `███████████░░░░░░░░░` | 1.000 +0.000 | `████████████████████` |
| judge_accuracy | 1.000 | 0.556 -0.444 | `███████████░░░░░░░░░` | 1.000 +0.000 | `████████████████████` |
| mean_judge_score | 5.000 | 3.222 -1.778 | `█████████████░░░░░░░` | 5.000 +0.000 | `████████████████████` |

> Δ values are relative to baseline. Bar width = value on a 0–1 scale.

## Analysis

- **Degradation detected:** `retrieval_hit_rate` dropped by 0.333 (33.3%); `mean_token_f1` dropped by 0.437 (43.7%); `judge_accuracy` dropped by 0.444 (44.4%).
- **After repair:** `retrieval_hit_rate` recovered by 0.333; `mean_token_f1` recovered by 0.437; `judge_accuracy` recovered by 0.444.
- **Quality checks that failed on corrupted data:** `paper_id_unique`, `summary_not_null`, `freshness`.

## Data Quality Checks

| Check | Corrupted | Repaired |
|-------|-----------|----------|
| row_count | ✓ | ✓ |
| paper_id_not_null | ✓ | ✓ |
| paper_id_unique | ✗ | ✓ |
| title_not_null | ✓ | ✓ |
| summary_not_null | ✗ | ✓ |
| freshness | ✗ | ✓ |

## Freshness

| Field | Corrupted | Repaired |
|-------|-----------|----------|
| latest_published | 2026-05-12 | 2026-06-02 |
| oldest_published | 2021-06-11 | 2025-12-19 |
| stale_rows | 6 (24.0%) | 0 (0.0%) |
| is_fresh | ❌ No | ✅ Yes |

## Corruption Types Applied

| # | Type | Impact |
|---|------|--------|
| 1 | Drop latest records | Removes recent documents, degrades freshness |
| 2 | Blank summary | Empty text_for_embedding → retrieval failures |
| 3 | Noise injection | Corrupts semantic content → lower F1 |
| 4 | Truncate titles | Breaks exact-match lookup |
| 5 | Stale publication dates | Fails freshness checks |
| 6 | Duplicate rows | Inflates row count, misleads quality checks |

## Conclusion

- Data corruption caused measurable degradation across all retrieval and generation metrics.
- Data observability checks correctly flagged the corrupted rows (blank summaries, duplicates, stale dates).
- Re-ingesting and re-cleaning from the raw Crossref snapshot fully restored performance to baseline levels.
- This demonstrates the value of data quality monitoring in production RAG pipelines.
