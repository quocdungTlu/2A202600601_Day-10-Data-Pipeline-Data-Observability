# Day 10 - Data Pipeline & Data Observability

[![Tests](https://github.com/quocdungTlu/2A202600601_Day-10-Data-Pipeline-Data-Observability/actions/workflows/tests.yml/badge.svg)](https://github.com/quocdungTlu/2A202600601_Day-10-Data-Pipeline-Data-Observability/actions/workflows/tests.yml)

**Student:** Luong Quoc Dung | **ID:** 2A202600601 | **Batch:** Batch 03

End-to-end RAG data pipeline with full observability: ingest academic papers from the
Crossref REST API, clean and embed them, evaluate retrieval quality, then simulate data
corruption and verify the observability layer catches and repairs the damage.

---

## Architecture

```
Crossref REST API
      |
      v
[Ingestion] crossref.py
      |
      +-- data/raw/crossref_response.json   (raw API response)
      +-- data/raw/crossref_records.json    (parsed PaperRecord list)
      |
      v
[Cleaning] cleaning.py
      |
      +-- data/clean/papers_clean.csv / .json
      |
      v
[Embedding] embeddings.py + ChromaDB
      |
      +-- data/embeddings/papers_embeddings.json
      |       ChromaDB collection: papers-baseline
      |
      v
[Evaluation] testset.py + metrics.py
      |
      +-- data/eval/test_set.json
      +-- data/results/baseline_metrics.json
      |
      v
[Observability] quality.py + reporting.py
      |
      +-- data/quality/baseline_quality.json
      +-- data/quality/freshness_report.json
      +-- data/reports/phase1_report.md

      +-- [Corruption] corruption.py
      |         |
      |         v (6 corruption types)
      |   data/clean/papers_clean_corrupted.csv
      |   data/results/corrupted_metrics.json
      |         |
      |         v
      |   [Repair] re-ingest from raw snapshot
      |         |
      |         v
      |   data/clean/papers_clean_repaired.csv
      |   data/results/repaired_metrics.json
      |         |
      +-----------> data/reports/corruption_report.md
```

---

## Results

### Phase 1 — Baseline Pipeline

| Metric | Value | Status |
|--------|-------|--------|
| Records ingested | 23 | Crossref API |
| Records after cleaning | 23 | 0 filtered |
| Embedding model | all-MiniLM-L6-v2 | sentence-transformers |
| Test questions | 18 | 4 question types |
| **Retrieval Hit Rate** | **1.000** | Perfect |
| **Mean Token F1** | **1.000** | Perfect |
| **Judge Accuracy** | **1.000** | Perfect |
| **Mean Judge Score** | **5.000 / 5** | Perfect |
| Data Quality Checks | **8 / 8 passed** | All green |
| Freshness (stale rows) | 0 / 23 (0%) | Fresh |

### Phase 2 — Corruption & Repair

6 corruption types applied: drop_latest (3 rows), blank_summary (20%),
noise_injection (10%), truncate_title (15%), stale_dates (20%), add_duplicates (5 rows)

| Metric | Baseline | Corrupted | Delta | Repaired | Recovery |
|--------|----------|-----------|-------|----------|----------|
| Retrieval Hit Rate | 1.000 | 0.667 | -33% | **1.000** | +100% |
| Mean Token F1 | 1.000 | 0.563 | -44% | **1.000** | +100% |
| Judge Accuracy | 1.000 | 0.556 | -44% | **1.000** | +100% |
| Mean Judge Score | 5.000 | 3.222 | -36% | **5.000** | +100% |
| Quality Checks | 8/8 | 4/8 | -4 | **8/8** | Full |

> Full repair to baseline confirmed. Observability layer correctly flagged all corruptions.

---

## Setup

```bash
# 1. Install dependencies
uv sync

# 2. Configure LLM provider
cp .env.example .env
# Edit .env — set LLM_PROVIDER, LLM_MODEL, and the corresponding API key
# Supported providers: openai | anthropic | gemini | openrouter | ollama | custom
```

---

## How to Run

```bash
# Run Phase 1 only (ingest + embed + evaluate + report)
uv run python script/run_phase1.py

# Run Corruption & Repair flow (requires Phase 1 artifacts)
uv run python script/run_corruption_flow.py

# Run everything in sequence
uv run python script/run_all.py

# Run validation tests
uv run pytest tests/ -v
```

---

## Project Structure

```
src/
  core/          config.py, utils.py
  ingestion/     crossref.py, cleaning.py, corruption.py
  retrieval/     embeddings.py, index.py, llm.py, qa.py, agent.py
  evaluation/    testset.py, metrics.py
  observability/ quality.py, reporting.py
  pipelines/     phase1.py, corruption_flow.py

script/
  run_phase1.py
  run_corruption_flow.py
  run_all.py

tests/
  conftest.py          fixtures
  test_cleaning.py     9 tests — data cleaning logic
  test_quality.py      6 tests — quality & freshness checks
  test_corruption.py   7 tests — corruption simulation

data/
  raw/           Crossref API response + parsed records
  clean/         Cleaned CSVs (baseline, corrupted, repaired)
  embeddings/    Embedding vectors for all 3 versions
  eval/          Test set (18 Q&A pairs, 4 question types)
  quality/       Quality & freshness JSON reports
  results/       Metrics + LLM answers (baseline/corrupted/repaired)
  reports/       phase1_report.md, corruption_report.md
```

---

## RAGAS

RAGAS (context_precision, context_recall, faithfulness, answer_relevancy) is supported in the
codebase via `src/evaluation/metrics.py` but is disabled by default because `scikit-network`
(a RAGAS dependency) requires a C++ compiler to build on Windows.

To enable on Linux/Mac or Windows with MSVC installed:
```bash
pip install ragas
RUN_RAGAS=1 uv run python script/run_phase1.py
```

The four primary metrics (retrieval_hit_rate, mean_token_f1, judge_accuracy, mean_judge_score)
fully cover retrieval and generation quality without RAGAS.

---

## LLM Providers

| Provider | .env key |
|----------|----------|
| openai | `OPENAI_API_KEY` |
| anthropic | `ANTHROPIC_API_KEY` |
| gemini | `GOOGLE_API_KEY` |
| openrouter | `OPENROUTER_API_KEY` |
| ollama | `OLLAMA_BASE_URL` (default: http://localhost:11434) |
| custom | `CUSTOM_LLM_BASE_URL` + `CUSTOM_LLM_API_KEY` |

---

## References

- [Guide.md](Guide.md)
- [Rubric.md](Rubric.md)
- [Phase 1 Report](data/reports/phase1_report.md)
- [Corruption & Repair Report](data/reports/corruption_report.md)
