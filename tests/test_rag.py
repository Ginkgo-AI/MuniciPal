"""Tests for the Munici-Pal RAG pipeline.

Covers chunking logic, ingestion, retrieval/confidence scoring,
citation parsing, and the low-confidence kill-switch.
"""

from __future__ import annotations

import asyncio
import math
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from municipal.core.types import DataClassification
from municipal.rag.ingest import (
    DocumentIngester,
    IngestResult,
    chunk_text,
    _split_on_sentence_boundary,
    _detect_section_header,
)
from municipal.rag.retrieve import Retriever, RetrievalResult, distance_to_confidence
from municipal.rag.citation import (
    CitationEngine,
    CitedAnswer,
    Citation,
    _parse_citations,
    _build_context_block,
    _LOW_CONFIDENCE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Chunking tests
# ---------------------------------------------------------------------------

class TestChunking:
    """Tests for text chunking logic."""

    def test_paragraph_splitting(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunk_text(text)
        assert len(chunks) == 3
        assert chunks[0]["text"] == "First paragraph."
        assert chunks[1]["text"] == "Second paragraph."
        assert chunks[2]["text"] == "Third paragraph."

    def test_chunk_indices_are_sequential(self):
        text = "One.\n\nTwo.\n\nThree."
        chunks = chunk_text(text)
        indices = [c["chunk_index"] for c in chunks]
        assert indices == [0, 1, 2]

    def test_long_paragraph_splitting(self):
        """Paragraphs exceeding max_chunk_chars are split on sentence boundaries."""
        sentences = ["This is sentence number %d. " % i for i in range(20)]
        long_para = "".join(sentences)
        chunks = chunk_text(long_para, max_chunk_chars=100)
        assert len(chunks) > 1
        for chunk in chunks:
            # Each chunk should be non-empty
            assert len(chunk["text"]) > 0

    def test_section_header_extraction_from_markdown(self):
        text = "# Introduction\n\nSome introductory text.\n\n## Details\n\nSome details."
        chunks = chunk_text(text)
        # First chunk is the heading itself
        assert chunks[0]["section_header"] == "Introduction"
        assert chunks[1]["section_header"] == "Introduction"
        # After the ## Details heading
        assert chunks[2]["section_header"] == "Details"
        assert chunks[3]["section_header"] == "Details"

    def test_no_section_header_for_plain_text(self):
        text = "Just plain text.\n\nAnother paragraph."
        chunks = chunk_text(text)
        for chunk in chunks:
            assert chunk["section_header"] is None

    def test_empty_text_returns_no_chunks(self):
        chunks = chunk_text("")
        assert chunks == []

    def test_whitespace_only_returns_no_chunks(self):
        chunks = chunk_text("   \n\n   \n\n   ")
        assert chunks == []

    def test_sentence_boundary_splitting(self):
        text = "Short sentence. " * 30  # well over 500 chars
        parts = _split_on_sentence_boundary(text, max_chars=100)
        assert len(parts) > 1
        for part in parts:
            assert len(part) > 0

    def test_detect_section_header(self):
        assert _detect_section_header("# Hello World") == "Hello World"
        assert _detect_section_header("### Sub Section") == "Sub Section"
        assert _detect_section_header("No heading here") is None


# ---------------------------------------------------------------------------
# Ingestion tests
# ---------------------------------------------------------------------------

class TestIngestion:
    """Tests for DocumentIngester with a mocked VectorStore."""

    def _make_ingester(self) -> tuple[DocumentIngester, MagicMock, MagicMock]:
        mock_store = MagicMock()
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = DataClassification.PUBLIC
        ingester = DocumentIngester(mock_store, mock_classifier)
        return ingester, mock_store, mock_classifier

    def test_ingest_file_creates_chunks(self, tmp_path: Path):
        ingester, mock_store, _ = self._make_ingester()
        test_file = tmp_path / "test.md"
        test_file.write_text("# Title\n\nParagraph one.\n\nParagraph two.")

        result = ingester.ingest_file(
            str(test_file), {"collection": "test_col"}
        )

        assert isinstance(result, IngestResult)
        assert result.num_chunks > 0
        assert result.collection == "test_col"
        assert result.classification == DataClassification.PUBLIC
        assert len(result.chunk_ids) == result.num_chunks

        # VectorStore.add_documents should have been called once
        mock_store.add_documents.assert_called_once()
        docs = mock_store.add_documents.call_args[0][0]
        assert len(docs) == result.num_chunks

    def test_ingest_file_default_collection(self, tmp_path: Path):
        ingester, mock_store, _ = self._make_ingester()
        test_file = tmp_path / "test.txt"
        test_file.write_text("Some content.")

        result = ingester.ingest_file(str(test_file))
        assert result.collection == "ordinances"

    def test_ingest_file_metadata_propagated(self, tmp_path: Path):
        ingester, mock_store, _ = self._make_ingester()
        test_file = tmp_path / "test.md"
        test_file.write_text("Content here.")

        ingester.ingest_file(
            str(test_file),
            {"collection": "col", "department": "planning"},
        )

        docs = mock_store.add_documents.call_args[0][0]
        assert docs[0].metadata["department"] == "planning"
        assert docs[0].metadata["source_file"] == str(test_file)

    def test_ingest_directory(self, tmp_path: Path):
        ingester, mock_store, _ = self._make_ingester()

        (tmp_path / "a.md").write_text("File A.")
        (tmp_path / "b.txt").write_text("File B.")
        (tmp_path / "c.pdf").write_text("Ignored.")  # not supported

        results = ingester.ingest_directory(str(tmp_path))
        assert len(results) == 2  # only .md and .txt
        assert mock_store.add_documents.call_count == 2

    def test_ingest_empty_file(self, tmp_path: Path):
        ingester, mock_store, _ = self._make_ingester()
        test_file = tmp_path / "empty.md"
        test_file.write_text("")

        result = ingester.ingest_file(str(test_file))
        assert result.num_chunks == 0
        mock_store.add_documents.assert_not_called()

    def test_classification_passed_to_documents(self, tmp_path: Path):
        ingester, mock_store, mock_classifier = self._make_ingester()
        mock_classifier.classify.return_value = DataClassification.INTERNAL

        test_file = tmp_path / "test.md"
        test_file.write_text("Content.")

        result = ingester.ingest_file(str(test_file))
        assert result.classification == DataClassification.INTERNAL

        docs = mock_store.add_documents.call_args[0][0]
        assert docs[0].classification == DataClassification.INTERNAL


# ---------------------------------------------------------------------------
# Retrieval and confidence scoring tests
# ---------------------------------------------------------------------------

class TestConfidenceScoring:
    """Tests for distance-to-confidence conversion."""

    def test_zero_distance_is_full_confidence(self):
        assert distance_to_confidence(0.0) == 1.0

    def test_large_distance_is_low_confidence(self):
        score = distance_to_confidence(10.0)
        assert score < 0.01

    def test_moderate_distance(self):
        score = distance_to_confidence(1.0)
        assert 0.5 < score < 0.7  # exp(-0.5) ~ 0.607

    def test_confidence_is_clamped_to_unit_interval(self):
        assert 0.0 <= distance_to_confidence(100.0) <= 1.0
        assert 0.0 <= distance_to_confidence(0.0) <= 1.0

    def test_monotonically_decreasing(self):
        prev = 1.0
        for d in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
            score = distance_to_confidence(d)
            assert score < prev
            prev = score


class TestRetriever:
    """Tests for Retriever with a mocked VectorStore."""

    def _make_retriever(self, search_results: list) -> Retriever:
        mock_store = MagicMock()
        mock_store.query.return_value = search_results
        return Retriever(mock_store)

    def test_retrieve_returns_results_with_confidence(self):
        from municipal.vectordb.store import SearchResult

        sr = SearchResult(
            document_id="chunk-1",
            content="Some content",
            metadata={"source_file": "test.md", "section_header": "Intro"},
            classification=DataClassification.PUBLIC,
            distance=0.5,
        )
        retriever = self._make_retriever([sr])
        results = retriever.retrieve("query", "col")

        assert len(results) == 1
        assert results[0].chunk_id == "chunk-1"
        assert results[0].source == "test.md"
        assert results[0].confidence_score == distance_to_confidence(0.5)

    def test_results_sorted_by_confidence_descending(self):
        from municipal.vectordb.store import SearchResult

        srs = [
            SearchResult(
                document_id=f"chunk-{i}",
                content=f"Content {i}",
                metadata={"source_file": f"file{i}.md"},
                distance=d,
            )
            for i, d in enumerate([2.0, 0.1, 1.0])
        ]
        retriever = self._make_retriever(srs)
        results = retriever.retrieve("query", "col")

        confidences = [r.confidence_score for r in results]
        assert confidences == sorted(confidences, reverse=True)

    def test_empty_results(self):
        retriever = self._make_retriever([])
        results = retriever.retrieve("query", "col")
        assert results == []


# ---------------------------------------------------------------------------
# Citation engine tests
# ---------------------------------------------------------------------------

class TestCitationParsing:
    """Tests for citation extraction from LLM output."""

    def test_parse_single_citation(self):
        results = [
            MagicMock(
                source="noise_ordinance.md",
                content="Quiet hours are 10 PM to 7 AM.",
                confidence_score=0.8,
                metadata={"section_header": "Quiet Hours"},
            )
        ]
        answer = "The quiet hours are from 10 PM to 7 AM [Source: noise_ordinance.md]."
        citations = _parse_citations(answer, results)
        assert len(citations) == 1
        assert citations[0].source == "noise_ordinance.md"
        assert citations[0].section == "Quiet Hours"
        assert citations[0].relevance_score == 0.8

    def test_parse_multiple_citations(self):
        results = [
            MagicMock(
                source="file_a.md",
                content="Content A",
                confidence_score=0.9,
                metadata={},
            ),
            MagicMock(
                source="file_b.md",
                content="Content B",
                confidence_score=0.7,
                metadata={"section_header": "Section B"},
            ),
        ]
        answer = "Info from A [Source: file_a.md] and B [Source: file_b.md]."
        citations = _parse_citations(answer, results)
        assert len(citations) == 2

    def test_duplicate_citations_deduplicated(self):
        results = [
            MagicMock(
                source="file.md",
                content="Content",
                confidence_score=0.9,
                metadata={},
            )
        ]
        answer = "[Source: file.md] and again [Source: file.md]."
        citations = _parse_citations(answer, results)
        assert len(citations) == 1

    def test_unknown_source_in_citation(self):
        results = []
        answer = "Something [Source: unknown.md]."
        citations = _parse_citations(answer, results)
        assert len(citations) == 1
        assert citations[0].source == "unknown.md"
        assert citations[0].relevance_score == 0.0
        assert citations[0].quote == ""


class TestCitationEngine:
    """Tests for CitationEngine with mocked LLM and Retriever."""

    def _make_engine(
        self,
        llm_response: str,
        retrieval_results: list[RetrievalResult],
    ) -> CitationEngine:
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=llm_response)

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = retrieval_results

        return CitationEngine(mock_llm, mock_retriever)

    def test_answer_with_citations(self):
        results = [
            RetrievalResult(
                content="Quiet hours: 10 PM - 7 AM.",
                source="noise.md",
                chunk_id="c1",
                distance=0.3,
                confidence_score=0.86,
                metadata={"section_header": "Quiet Hours"},
            )
        ]
        engine = self._make_engine(
            "Quiet hours are 10 PM to 7 AM [Source: noise.md].",
            results,
        )

        answer = asyncio.get_event_loop().run_until_complete(
            engine.answer("What are quiet hours?", "ordinances")
        )

        assert isinstance(answer, CitedAnswer)
        assert "10 PM" in answer.answer
        assert len(answer.citations) == 1
        assert answer.citations[0].source == "noise.md"
        assert answer.confidence > _LOW_CONFIDENCE_THRESHOLD
        assert answer.low_confidence is False

    def test_low_confidence_kill_switch(self):
        """When average confidence is below threshold, low_confidence is True."""
        results = [
            RetrievalResult(
                content="Vague content",
                source="file.md",
                chunk_id="c1",
                distance=5.0,
                confidence_score=0.08,  # very low
                metadata={},
            )
        ]
        engine = self._make_engine(
            "Some answer [Source: file.md].",
            results,
        )

        answer = asyncio.get_event_loop().run_until_complete(
            engine.answer("Obscure question?", "col")
        )

        assert answer.low_confidence is True
        assert answer.confidence < _LOW_CONFIDENCE_THRESHOLD

    def test_no_results_returns_refusal(self):
        """When no retrieval results, the engine returns a refusal."""
        engine = self._make_engine("Should not be called", [])

        answer = asyncio.get_event_loop().run_until_complete(
            engine.answer("Anything?", "col")
        )

        assert "cannot find" in answer.answer.lower()
        assert answer.low_confidence is True
        assert answer.confidence == 0.0
        assert answer.sources_used == 0

    def test_confidence_computed_from_cited_sources(self):
        """Confidence should be the average of cited source confidence scores."""
        results = [
            RetrievalResult(
                content="Content A",
                source="a.md",
                chunk_id="c1",
                distance=0.2,
                confidence_score=0.9,
                metadata={},
            ),
            RetrievalResult(
                content="Content B",
                source="b.md",
                chunk_id="c2",
                distance=1.0,
                confidence_score=0.6,
                metadata={},
            ),
        ]
        engine = self._make_engine(
            "Answer using [Source: a.md] and [Source: b.md].",
            results,
        )

        answer = asyncio.get_event_loop().run_until_complete(
            engine.answer("Question?", "col")
        )

        expected_confidence = (0.9 + 0.6) / 2
        assert abs(answer.confidence - expected_confidence) < 0.01


# ---------------------------------------------------------------------------
# Context block formatting
# ---------------------------------------------------------------------------

class TestContextBlock:
    """Tests for context block formatting."""

    def test_build_context_block(self):
        results = [
            MagicMock(
                source="test.md",
                content="Some content here.",
                metadata={"section_header": "Intro"},
            ),
        ]
        block = _build_context_block(results)
        assert "[1] Source: test.md (Section: Intro)" in block
        assert "Some content here." in block

    def test_build_context_no_section(self):
        results = [
            MagicMock(
                source="test.md",
                content="Content.",
                metadata={},
            ),
        ]
        block = _build_context_block(results)
        assert "[1] Source: test.md\nContent." in block
