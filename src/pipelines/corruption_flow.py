from __future__ import annotations

import ast
import time

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _restore_csv(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in ("authors", "categories"):
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith("[") else []
            )
    df["published_dt"] = pd.to_datetime(df["published"], errors="coerce")
    if "age_days" in df.columns:
        df["age_days"] = df["age_days"].fillna(0).astype(int)
    return df


def _df_to_json_safe(df: pd.DataFrame) -> list[dict]:
    out = df.copy()
    if "published_dt" in out.columns:
        out["published_dt"] = out["published_dt"].astype(str)
    return out.to_dict(orient="records")


def _step(label: str) -> float:
    print(f"\n[Corruption Flow] {label}")
    return time.perf_counter()


def _done(t0: float) -> None:
    print(f"  >> done in {time.perf_counter() - t0:.1f}s")


def main() -> None:
    pipeline_start = time.perf_counter()
    settings = load_settings()
    run_date = now_utc()

    print("=" * 60)
    print("Corruption -> Evaluate -> Repair -> Compare Flow")
    print("=" * 60)

    # 1. Load baseline
    t = _step("Loading baseline data ...")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    df_clean = _restore_csv(settings.paths.clean_csv)
    print(f"  baseline records : {len(df_clean)}")
    _done(t)

    # 2. Corrupt
    t = _step("Applying data corruption ...")
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    corruption_log = read_json(settings.paths.corruption_log)
    print(f"  {len(df_clean)} rows -> {len(df_corrupted)} rows (net {corruption_log['net_change']:+d})")
    for c in corruption_log["corruptions"]:
        print(f"  [{c['type']}] {c['count']} rows ({c['pct']}%)")
    _done(t)

    # 3. Save corrupted
    t = _step("Saving corrupted artifacts ...")
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, _df_to_json_safe(df_corrupted))
    _done(t)

    # 4. Build corrupted index + evaluate
    t = _step("Building corrupted embedding index ...")
    corrupted_index = LocalEmbeddingIndex.build(
        df_corrupted, settings, settings.paths.corrupted_embeddings_json
    )
    _done(t)

    t = _step("Evaluating corrupted pipeline ...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    _print_metrics("Corrupted", corrupted_bundle.summary)
    _done(t)

    # 5. Quality checks on corrupted
    t = _step("Quality & freshness checks on corrupted ...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        df_corrupted, settings, settings.paths.quality_dir / "corrupted_freshness.json"
    )
    print(f"  passed {corrupted_quality['summary']['passed_checks']}/{corrupted_quality['summary']['total_checks']} checks")
    print(f"  stale rows: {corrupted_freshness['stale_rows']} ({corrupted_freshness['pct_stale']}%)")
    _done(t)

    # 6. Repair from raw source
    t = _step("Repairing from raw source ...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, run_date)
    print(f"  repaired records : {len(df_repaired)}")
    _done(t)

    # 7. Save repaired
    t = _step("Saving repaired artifacts ...")
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, _df_to_json_safe(df_repaired))
    _done(t)

    # 8. Build repaired index + evaluate
    t = _step("Building repaired embedding index ...")
    repaired_index = LocalEmbeddingIndex.build(
        df_repaired, settings, settings.paths.repaired_embeddings_json
    )
    _done(t)

    t = _step("Evaluating repaired pipeline ...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    _print_metrics("Repaired", repaired_bundle.summary)
    _done(t)

    # 9. Quality checks on repaired
    t = _step("Quality & freshness checks on repaired ...")
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired")
    repaired_freshness = build_freshness_report(
        df_repaired, settings, settings.paths.quality_dir / "repaired_freshness.json"
    )
    print(f"  passed {repaired_quality['summary']['passed_checks']}/{repaired_quality['summary']['total_checks']} checks")
    print(f"  stale rows: {repaired_freshness['stale_rows']} ({repaired_freshness['pct_stale']}%)")
    _done(t)

    # 10. Comparison report
    t = _step("Generating comparison report ...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    _done(t)

    # Final summary table
    total = time.perf_counter() - pipeline_start
    print(f"\n{'=' * 60}")
    print(f"Corruption Flow complete in {total:.1f}s")
    print(f"  Report : {settings.paths.comparison_report}")
    print()
    print(f"  {'Metric':<25} {'Baseline':>9} {'Corrupted':>10} {'Repaired':>9}")
    print(f"  {'-' * 57}")
    for key in ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]:
        b = float(baseline_metrics.get(key, 0))
        c = float(corrupted_bundle.summary.get(key, 0))
        r = float(repaired_bundle.summary.get(key, 0))
        delta_c = c - b
        delta_r = r - b
        print(
            f"  {key:<25} {b:>9.3f} {c:>9.3f} ({delta_c:+.3f}) {r:>8.3f} ({delta_r:+.3f})"
        )
    print(f"{'=' * 60}")


def _print_metrics(label: str, m: dict) -> None:
    print(f"  [{label}]"
          f"  hit_rate={float(m.get('retrieval_hit_rate', 0)):.3f}"
          f"  token_f1={float(m.get('mean_token_f1', 0)):.3f}"
          f"  judge_acc={float(m.get('judge_accuracy', 0)):.3f}"
          f"  judge_score={float(m.get('mean_judge_score', 0)):.3f}")
