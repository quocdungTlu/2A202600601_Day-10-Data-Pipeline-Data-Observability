from __future__ import annotations

import time

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def _df_to_json_safe(df: pd.DataFrame) -> list[dict]:
    out = df.copy()
    if "published_dt" in out.columns:
        out["published_dt"] = out["published_dt"].astype(str)
    return out.to_dict(orient="records")


def _step(label: str) -> float:
    print(f"\n[Phase 1] {label}")
    return time.perf_counter()


def _done(t0: float) -> None:
    print(f"  >> done in {time.perf_counter() - t0:.1f}s")


def main() -> None:
    pipeline_start = time.perf_counter()
    settings = load_settings()
    run_date = now_utc()

    print("=" * 60)
    print("Phase 1 - Baseline Pipeline")
    print("=" * 60)
    print(f"  provider : {settings.llm_provider}")
    print(f"  model    : {settings.model_name}")
    print(f"  source   : {settings.source_api}")
    print(f"  query    : {settings.source_query}")

    # 2. Load or fetch raw records
    t = _step("Loading raw records ...")
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        print("  (using cached raw records)")
        records = load_raw_records(settings.paths.raw_records_json)
    print(f"  raw records : {len(records)}")
    _done(t)

    # 3. Clean data
    t = _step("Cleaning data ...")
    df = build_clean_dataframe(records, run_date)
    if df.empty:
        raise RuntimeError("Cleaning produced an empty dataframe — check raw records.")
    print(f"  clean records : {len(df)}")
    print(f"  date range    : {df['published'].min()} to {df['published'].max()}")
    _done(t)

    # 4. Save clean artifacts
    t = _step("Saving clean data ...")
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, _df_to_json_safe(df))
    _done(t)

    # 5. Build embedding index
    t = _step("Building embedding index ...")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f"  model : {settings.embedding_model}")
    print(f"  docs  : {len(index.documents)}")
    _done(t)

    # 6. Build or load evaluation test set
    t = _step("Preparing evaluation test set ...")
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(df, settings.paths.eval_testset)
        print(f"  built {len(test_set)} test questions")
    else:
        import json
        test_set = json.loads(settings.paths.eval_testset.read_text())
        print(f"  loaded {len(test_set)} cached test questions")
    _done(t)

    # 7. Evaluate
    t = _step("Evaluating pipeline ...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    m = bundle.summary
    print(f"  retrieval_hit_rate : {m['retrieval_hit_rate']:.3f}")
    print(f"  mean_token_f1      : {m['mean_token_f1']:.3f}")
    print(f"  judge_accuracy     : {m['judge_accuracy']:.3f}")
    print(f"  mean_judge_score   : {float(m['mean_judge_score']):.3f} / 5.000")
    _done(t)

    # 8. Data quality checks
    t = _step("Running data quality checks ...")
    quality = run_data_quality_checks(df, settings, "baseline")
    qs = quality["summary"]
    print(f"  {qs['passed_checks']}/{qs['total_checks']} checks passed")
    if qs["failed_checks"] > 0:
        failed = [k for k in quality if isinstance(quality[k], dict) and not quality[k].get("passed", True)]
        print(f"  failed: {', '.join(failed)}")
    _done(t)

    # Freshness report
    t = _step("Building freshness report ...")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(f"  latest    : {freshness['latest_published']}")
    print(f"  stale     : {freshness['stale_rows']} rows ({freshness['pct_stale']}%)")
    print(f"  is_fresh  : {freshness['is_fresh']}")
    _done(t)

    # 9. Markdown report
    t = _step("Generating markdown report ...")
    source_summary = {
        "source_api": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "total_records": len(records),
        "clean_records": len(df),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )
    _done(t)

    # 10. Agent demo
    t = _step("Agent demo questions ...")
    demo_questions = [
        "What papers are about retrieval augmented generation?",
        "What is the most recent paper in the corpus?",
        "List papers about large language models and agents.",
    ]
    demo_answers = []
    for q in demo_questions:
        result = answer_question(q, settings=settings, index=index)
        demo_answers.append({
            "question": q,
            "answer": result.answer,
            "retrieved_titles": result.retrieved_titles,
        })
        print(f"\n  Q: {q}")
        print(f"  A: {result.answer[:150]}")
    write_json(settings.paths.demo_answers, demo_answers)
    _done(t)

    total = time.perf_counter() - pipeline_start
    print(f"\n{'=' * 60}")
    print(f"Phase 1 complete in {total:.1f}s")
    print(f"  Report  : {settings.paths.baseline_report}")
    print(f"  Metrics : {settings.paths.baseline_metrics}")
    print(f"{'=' * 60}")
