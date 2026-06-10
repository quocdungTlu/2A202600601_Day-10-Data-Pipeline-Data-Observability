from __future__ import annotations

import pytest

from ingestion.cleaning import build_clean_dataframe

REQUIRED_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "published",
    "published_dt",
    "age_days",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "summary_words",
    "text_for_embedding",
]


def test_required_columns_present(clean_df):
    for col in REQUIRED_COLUMNS:
        assert col in clean_df.columns, f"Missing required column: {col}"


def test_filters_empty_title(clean_df):
    assert (clean_df["title"] == "").sum() == 0, "Empty titles must be filtered"


def test_filters_short_summary(clean_df):
    assert (clean_df["summary_words"] < 5).sum() == 0, "Summaries with < 5 words must be filtered"


def test_valid_records_retained(clean_df):
    # 10 valid records in fixture; 2 invalid ones must be filtered
    assert len(clean_df) == 10


def test_no_duplicate_paper_ids(clean_df):
    assert clean_df["paper_id"].nunique() == len(clean_df)


def test_sorted_newest_first(clean_df):
    dates = clean_df["published_dt"].dropna().tolist()
    assert dates == sorted(dates, reverse=True), "DataFrame must be sorted newest-first"


def test_text_for_embedding_format(clean_df):
    for _, row in clean_df.iterrows():
        text = row["text_for_embedding"]
        assert text.startswith("Title: "), f"text_for_embedding must start with 'Title: '"
        assert "Abstract: " in text
        assert "Authors: " in text
        assert "Published: " in text


def test_age_days_non_negative(clean_df):
    assert (clean_df["age_days"] >= 0).all(), "age_days must be non-negative"


def test_summary_chars_consistent(clean_df):
    expected = clean_df["summary"].str.len()
    assert (clean_df["summary_chars"] == expected).all(), "summary_chars must equal len(summary)"
