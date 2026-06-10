from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def _safe_title(title: str) -> str:
    """Escape single quotes in titles so they don't break the question string."""
    return title.replace("'", "\\'")


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a diverse evaluation test set from the cleaned dataset.

    Creates four question types per selected paper:
    - summary: what is this paper about?
    - authors: who wrote it?
    - date: when was it published?
    - categories: what subject areas?
    """
    if len(df) < 3:
        raise ValueError(f"Need at least 3 documents to build a test set, got {len(df)}.")

    # Spread selection across the dataframe to cover early/mid/late entries
    n_papers = min(6, len(df))
    indices = [int(i * (len(df) - 1) / (n_papers - 1)) for i in range(n_papers)] if n_papers > 1 else [0]
    selected = df.iloc[indices].drop_duplicates(subset=["paper_id"])

    samples: list[dict[str, Any]] = []
    idx = 0

    for _, row in selected.iterrows():
        paper_id = str(row["paper_id"])
        title = str(row["title"])
        safe_t = _safe_title(title)
        summary = str(row["summary"])
        authors_joined = str(row.get("authors_joined", ""))
        published = str(row.get("published", ""))
        categories_joined = str(row.get("categories_joined", ""))

        # 1. Summary question
        samples.append(
            {
                "id": f"q{idx:03d}",
                "question_type": "summary",
                "question": f"What is the paper '{safe_t}' about?",
                "ground_truth": first_sentence(summary),
                "ground_truth_doc_ids": [paper_id],
            }
        )
        idx += 1

        # 2. Authors question
        if authors_joined:
            samples.append(
                {
                    "id": f"q{idx:03d}",
                    "question_type": "authors",
                    "question": f"Who authored '{safe_t}'?",
                    "ground_truth": authors_joined,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            idx += 1

        # 3. Publication date question
        if published:
            samples.append(
                {
                    "id": f"q{idx:03d}",
                    "question_type": "date",
                    "question": f"When was '{safe_t}' published?",
                    "ground_truth": published,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            idx += 1

        # 4. Categories question
        if categories_joined:
            samples.append(
                {
                    "id": f"q{idx:03d}",
                    "question_type": "categories",
                    "question": f"What subject categories does '{safe_t}' belong to?",
                    "ground_truth": categories_joined,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            idx += 1

    write_json(Path(output_path), samples)
    return samples
