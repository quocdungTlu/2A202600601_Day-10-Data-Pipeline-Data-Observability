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

## Root Cause Analysis

### Why did `retrieval_hit_rate` drop?
- **blank_summary** (20% of rows): Documents with empty abstracts produce near-zero embedding vectors,
  making them unretrievable by cosine similarity search.
- **drop_latest** (3 newest records removed): Reduced corpus coverage causes test questions about
  recent papers to return no matching document.

### Why did `mean_token_f1` drop?
- **noise_injection** (10% of rows): Injected garbage text (`CORRUPTED_DATA ... [NOISE_INJECTED_XQ9Z]`)
  is included in the context window, diluting the factual content and lowering token overlap with reference answers.
- **blank_summary**: Empty documents contribute nothing useful to the LLM context, degrading answer quality.

### Why did `judge_accuracy` drop?
- Combined effect of corrupted content and missing documents reduces answer faithfulness below the LLM
  judge's acceptance threshold, even when retrieval partially succeeds.

### Why did repair fully restore metrics?
- The repair step **re-ingests from the original raw JSON snapshot** (not the API) and re-runs the
  full cleaning pipeline. This guarantees bit-for-bit identical output to the baseline, achieving
  complete metric recovery to 1.000 / 5.000.

## Recommendations for Production

1. **Monitor `retrieval_hit_rate` continuously** — a drop below 0.9 should trigger an automatic
   re-ingestion from the source API.
2. **Alert on blank `summary` rate** — set a threshold at 5%; above that, pause ingestion and
   investigate the upstream data source.
3. **Schedule freshness scans daily** — stale_rows > 10% indicates the ingestion pipeline has stalled.
4. **Keep raw snapshots immutable** — the raw JSON is the ground truth for repair. Never overwrite it.
5. **Use `paper_id_unique` check as a deduplication gate** before loading into the vector store.

## Conclusion

- Data corruption caused measurable degradation across all retrieval and generation metrics
  (hit_rate: -33%, token_f1: -44%, judge_accuracy: -44%).
- The observability layer correctly flagged corrupted rows via quality checks:
  `paper_id_unique`, `summary_not_null`, and `freshness` all failed on the corrupted dataset.
- Re-ingesting and re-cleaning from the raw Crossref snapshot **fully restored** all metrics
  to baseline levels (1.000 / 5.000), confirming the repair strategy is sound.
- This demonstrates the critical value of data quality monitoring and immutable raw storage
  in production RAG pipelines.
