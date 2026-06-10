from __future__ import annotations

import json

import pytest

from ingestion.corruption import corrupt_clean_dataframe


def test_corruption_log_created(clean_df, tmp_path):
    log_path = tmp_path / "corruption.json"
    corrupt_clean_dataframe(clean_df, log_path)
    assert log_path.exists()


def test_corruption_has_six_types(clean_df, tmp_path):
    log_path = tmp_path / "corruption.json"
    corrupt_clean_dataframe(clean_df, log_path)
    log = json.loads(log_path.read_text())
    assert log["corruption_types"] == 6, f"Expected 6 corruption types, got {log['corruption_types']}"


def test_corruption_net_change(clean_df, tmp_path):
    log_path = tmp_path / "corruption.json"
    corrupted = corrupt_clean_dataframe(clean_df, log_path)
    log = json.loads(log_path.read_text())
    assert len(corrupted) == log["corrupted_rows"]
    # net_change = duplicates_added - rows_dropped
    assert log["net_change"] == log["corrupted_rows"] - log["original_rows"]


def test_corruption_blank_summaries_applied(clean_df, tmp_path):
    log_path = tmp_path / "corruption.json"
    corrupted = corrupt_clean_dataframe(clean_df, log_path)
    blank_count = (corrupted["summary"] == "").sum()
    assert blank_count > 0, "blank_summary corruption should produce empty summaries"


def test_corruption_stale_dates_applied(clean_df, tmp_path):
    log_path = tmp_path / "corruption.json"
    corrupt_clean_dataframe(clean_df, log_path)
    log = json.loads(log_path.read_text())
    stale_entry = next((c for c in log["corruptions"] if c["type"] == "stale_dates"), None)
    assert stale_entry is not None
    assert stale_entry["count"] > 0
    assert "2021" in stale_entry.get("stale_date_set_to", "")


def test_corruption_preserves_schema(clean_df, tmp_path):
    log_path = tmp_path / "corruption.json"
    corrupted = corrupt_clean_dataframe(clean_df, log_path)
    for col in ("paper_id", "title", "summary", "text_for_embedding", "summary_chars", "summary_words"):
        assert col in corrupted.columns, f"Column '{col}' missing after corruption"


def test_corruption_is_deterministic(clean_df, tmp_path):
    log1 = tmp_path / "log1.json"
    log2 = tmp_path / "log2.json"
    df1 = corrupt_clean_dataframe(clean_df, log1)
    df2 = corrupt_clean_dataframe(clean_df, log2)
    assert list(df1["paper_id"]) == list(df2["paper_id"]), "Corruption must be deterministic (fixed seed)"
