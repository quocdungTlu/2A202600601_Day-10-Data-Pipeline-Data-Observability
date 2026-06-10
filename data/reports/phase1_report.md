# Phase 1 — Baseline Pipeline Report

## Data Source

| Field | Value |
|-------|-------|
| Source API | Crossref REST API |
| Query | agentic retrieval augmented generation large language model |
| Filter | from-pub-date:2025-12-12,has-abstract:true |
| Records fetched | 23 |
| Records after cleaning | 23 |

## Evaluation Metrics

| Metric | Value | Bar (0 → 1) |
|--------|-------|-------------|
| Retrieval Hit Rate | 1.000 | `████████████████████` |
| Mean Token F1 | 1.000 | `████████████████████` |
| Judge Accuracy | 1.000 | `████████████████████` |
| Mean Judge Score | 5.000 | `████████████████████` |

> **Samples evaluated:** 18

## Data Quality

| Check | Status | Detail |
|-------|--------|--------|
| Row count | ✓ | 23 rows |
| paper_id not null | ✓ | nulls=0 |
| paper_id unique | ✓ | dupes=0 |
| title not null | ✓ | empty=0 |
| summary not null | ✓ | empty=0 |
| summary length | ✓ | min=1037 / mean=1805.8 / max=2515 chars |
| text_for_embedding | ✓ | missing=0 |
| freshness | ✓ | stale=0 (0.0%) |

**Result: 8/8 checks passed** ✅ All good

## Freshness

| Field | Value |
|-------|-------|
| Latest published | 2026-06-02 |
| Oldest published | 2025-12-19 |
| Stale rows | 0 / 23 (0.0%) |
| Threshold | 180 days |
| Is fresh | ✅ Yes |
