from __future__ import annotations

import pandas as pd
import pytest

from observability.quality import build_freshness_report, run_data_quality_checks


def test_perfect_dataframe_passes_all_checks(clean_df, mock_settings):
    result = run_data_quality_checks(clean_df, mock_settings, "test_baseline")
    summary = result["summary"]
    assert summary["overall_passed"] is True
    assert summary["passed_checks"] == summary["total_checks"]
    assert summary["failed_checks"] == 0


def test_detects_duplicate_paper_ids(clean_df, mock_settings):
    df_duped = pd.concat([clean_df, clean_df.head(2)], ignore_index=True)
    result = run_data_quality_checks(df_duped, mock_settings, "test_duped")
    assert result["paper_id_unique"]["passed"] is False
    assert result["paper_id_unique"]["duplicate_count"] >= 2


def test_detects_blank_summary(clean_df, mock_settings):
    df_blank = clean_df.copy()
    df_blank.at[0, "summary"] = ""
    df_blank["summary_chars"] = df_blank["summary"].str.len()
    result = run_data_quality_checks(df_blank, mock_settings, "test_blank")
    assert result["summary_not_null"]["passed"] is False
    assert result["summary_not_null"]["null_or_empty_count"] >= 1


def test_detects_stale_rows(clean_df, mock_settings):
    df_stale = clean_df.copy()
    df_stale.at[0, "age_days"] = 999  # older than freshness_threshold_days=180
    result = run_data_quality_checks(df_stale, mock_settings, "test_stale")
    assert result["freshness"]["passed"] is False
    assert result["freshness"]["stale_rows"] >= 1


def test_freshness_report_has_required_fields(clean_df, mock_settings, tmp_path):
    report_path = tmp_path / "freshness.json"
    report = build_freshness_report(clean_df, mock_settings, report_path)
    for field in ("latest_published", "oldest_published", "stale_rows", "pct_stale", "is_fresh"):
        assert field in report, f"Missing field in freshness report: {field}"
    assert report_path.exists()


def test_freshness_report_correct_stale_count(clean_df, mock_settings, tmp_path):
    df_stale = clean_df.copy()
    # Force 3 rows to be stale
    for i in range(3):
        df_stale.at[i, "age_days"] = 999
    report = build_freshness_report(df_stale, mock_settings, tmp_path / "f.json")
    assert report["stale_rows"] == 3
    assert report["is_fresh"] is False
