from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from ingestion.crossref import PaperRecord


@pytest.fixture
def sample_records() -> list[PaperRecord]:
    """10 valid + 2 invalid records for testing cleaning and corruption logic."""
    valid = [
        PaperRecord(
            paper_id=f"10.1234/test.{i:03d}",
            title=t,
            summary=s,
            authors=["Author A", "Author B"],
            categories=["cs.AI", "cs.CL"],
            primary_category="cs.AI",
            published=p,
            updated=p,
            abs_url=f"https://doi.org/10.1234/test.{i:03d}",
            pdf_url="",
            comment="",
        )
        for i, (t, s, p) in enumerate(
            [
                (
                    "Retrieval Augmented Generation Survey",
                    "This paper provides a comprehensive survey of retrieval augmented generation (RAG) systems, covering architecture design, embedding methods, chunking strategies, and evaluation protocols for large language models in open-domain QA.",
                    "2026-01-10",
                ),
                (
                    "Agentic LLM Benchmark Design",
                    "We propose new evaluation benchmarks for large language model agents focused on multi-step reasoning, tool use, and factual accuracy in knowledge-intensive tasks with complex dependencies.",
                    "2026-01-25",
                ),
                (
                    "ChromaDB vs FAISS at Scale",
                    "An empirical study of ChromaDB and FAISS performance characteristics for semantic search in production retrieval-augmented generation pipelines at scale with millions of embeddings.",
                    "2026-02-05",
                ),
                (
                    "MiniLM Embedding Quality",
                    "Quantitative analysis of sentence-transformers all-MiniLM-L6-v2 embedding quality across academic domains, with ablation studies on chunk size and overlap for optimal retrieval performance.",
                    "2026-02-20",
                ),
                (
                    "Data Quality Monitoring for ML",
                    "A framework for automated data quality monitoring in machine learning pipelines using statistical tests, schema validation, and freshness checks to detect drift and corruption early.",
                    "2026-03-01",
                ),
                (
                    "LangChain Production Patterns",
                    "Best practices for deploying LangChain-based RAG systems in production, including prompt engineering, retry logic, streaming responses, and cost optimization across multiple LLM providers.",
                    "2026-03-15",
                ),
                (
                    "Graph RAG with Knowledge Graphs",
                    "Integration of knowledge graph traversal into retrieval augmented generation pipelines, enabling multi-hop reasoning over structured and unstructured data sources for complex query answering.",
                    "2026-04-02",
                ),
                (
                    "Token F1 Evaluation for RAG",
                    "Comprehensive evaluation of token-level F1 metrics for RAG answer quality assessment, comparing token overlap, semantic similarity, and LLM-as-judge approaches on academic benchmarks.",
                    "2026-04-18",
                ),
                (
                    "Hybrid Search in Vector Stores",
                    "Combining dense vector search with sparse BM25 retrieval improves recall for long-tail queries in RAG systems while maintaining sub-second latency at production scale.",
                    "2026-05-03",
                ),
                (
                    "Self-RAG with Reflection Tokens",
                    "Self-reflective retrieval augmented generation using special control tokens allows the model to decide when to retrieve, what to retrieve, and whether retrieved passages are relevant.",
                    "2026-05-20",
                ),
            ],
            start=1,
        )
    ]
    invalid = [
        PaperRecord(
            paper_id="10.1234/test.bad1",
            title="",  # empty title — filtered by cleaning
            summary="Should be filtered because title is empty.",
            authors=[],
            categories=[],
            primary_category="",
            published="2026-04-01",
            updated="2026-04-01",
            abs_url="",
            pdf_url="",
            comment="",
        ),
        PaperRecord(
            paper_id="10.1234/test.bad2",
            title="Short Paper",
            summary="Too short.",  # < 5 words — filtered by cleaning
            authors=["Frank Brown"],
            categories=["cs.AI"],
            primary_category="cs.AI",
            published="2026-04-15",
            updated="2026-04-15",
            abs_url="",
            pdf_url="",
            comment="",
        ),
    ]
    return valid + invalid


@pytest.fixture
def run_date() -> datetime:
    return datetime(2026, 6, 10, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def clean_df(sample_records, run_date):
    from ingestion.cleaning import build_clean_dataframe

    return build_clean_dataframe(sample_records, run_date)


@pytest.fixture
def mock_settings(tmp_path):
    s = MagicMock()
    s.freshness_threshold_days = 180
    s.paths.quality_dir = tmp_path
    return s
