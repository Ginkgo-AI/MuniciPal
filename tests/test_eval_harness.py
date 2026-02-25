"""Tests for the Munici-Pal evaluation harness."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from municipal.core.config import EvalConfig, LLMConfig
from municipal.core.types import EvalEntry, EvalResult
from municipal.eval.golden_dataset import load_dataset, validate_dataset
from municipal.eval.harness import EvalHarness, EvalReport, extract_citations
from municipal.eval.metrics import EvalMetrics, compute_metrics
from municipal.eval.reports import export_report, format_report
from municipal.llm.client import LLMClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_entries() -> list[EvalEntry]:
    return [
        EvalEntry(
            id="test-001",
            department="Public Works",
            category="311",
            question="How do I report a pothole?",
            expected_answer="Call 311 or use the online portal.",
            expected_sources=["311 Guide", "PW Policy"],
            difficulty="easy",
        ),
        EvalEntry(
            id="test-002",
            department="Finance",
            category="fees",
            question="What is the dog license fee?",
            expected_answer="The annual dog license fee is $25.",
            expected_sources=["Fee Schedule 2025"],
            difficulty="medium",
        ),
    ]


def _make_results() -> list[EvalResult]:
    return [
        EvalResult(
            entry_id="test-001",
            question="How do I report a pothole?",
            generated_answer="Call 311. [Source: 311 Guide]",
            expected_answer="Call 311 or use the online portal.",
            cited_sources=["311 Guide"],
            expected_sources=["311 Guide", "PW Policy"],
            answer_accurate=True,
            citation_precision=1.0,
            citation_recall=0.5,
            contains_hallucination=False,
            correctly_refused=False,
            latency_ms=150.0,
        ),
        EvalResult(
            entry_id="test-002",
            question="What is the dog license fee?",
            generated_answer="The fee is $25. [Source: Fee Schedule 2025]",
            expected_answer="The annual dog license fee is $25.",
            cited_sources=["Fee Schedule 2025"],
            expected_sources=["Fee Schedule 2025"],
            answer_accurate=True,
            citation_precision=1.0,
            citation_recall=1.0,
            contains_hallucination=False,
            correctly_refused=False,
            latency_ms=200.0,
        ),
    ]


class MockLLMClient(LLMClient):
    """A mock LLM client that returns deterministic answers for testing."""

    def __init__(self) -> None:
        super().__init__(LLMConfig())
        self._generate = AsyncMock()
        self._chat = AsyncMock()

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        return await self._generate(prompt, system_prompt=system_prompt, temperature=temperature)

    async def chat(self, messages: list[dict], *, temperature: float = 0.1) -> str:
        return await self._chat(messages, temperature=temperature)

    async def is_available(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Golden dataset tests
# ---------------------------------------------------------------------------

class TestGoldenDataset:
    def test_load_dataset_from_array(self, tmp_path: Path) -> None:
        entries = _make_entries()
        data = [e.model_dump() for e in entries]
        f = tmp_path / "ds.json"
        f.write_text(json.dumps(data))
        loaded = load_dataset(f)
        assert len(loaded) == 2
        assert loaded[0].id == "test-001"

    def test_load_dataset_from_object(self, tmp_path: Path) -> None:
        entries = _make_entries()
        data = {"entries": [e.model_dump() for e in entries]}
        f = tmp_path / "ds.json"
        f.write_text(json.dumps(data))
        loaded = load_dataset(f)
        assert len(loaded) == 2

    def test_load_dataset_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_dataset("/nonexistent/path.json")

    def test_load_dataset_invalid_entries(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text(json.dumps([{"id": "x"}]))  # missing required fields
        with pytest.raises(ValueError, match="validation failed"):
            load_dataset(f)

    def test_validate_dataset_clean(self) -> None:
        errors = validate_dataset(_make_entries())
        assert errors == []

    def test_validate_dataset_duplicate_ids(self) -> None:
        entries = _make_entries()
        entries[1].id = entries[0].id  # duplicate
        errors = validate_dataset(entries)
        assert any("duplicate" in e for e in errors)

    def test_validate_dataset_empty_question(self) -> None:
        entries = _make_entries()
        entries[0].question = "  "
        errors = validate_dataset(entries)
        assert any("question is empty" in e for e in errors)

    def test_validate_dataset_invalid_difficulty(self) -> None:
        entries = _make_entries()
        entries[0].difficulty = "extreme"
        errors = validate_dataset(entries)
        assert any("invalid difficulty" in e for e in errors)


# ---------------------------------------------------------------------------
# Citation extraction tests
# ---------------------------------------------------------------------------

class TestCitationExtraction:
    def test_source_pattern(self) -> None:
        text = "The fee is $25. [Source: Fee Schedule]"
        assert extract_citations(text) == ["Fee Schedule"]

    def test_ref_pattern(self) -> None:
        text = "See policy. [Ref: Policy Doc 1]"
        assert extract_citations(text) == ["Policy Doc 1"]

    def test_multiple_sources(self) -> None:
        text = "[Source: A] and [Ref: B] are cited."
        assert extract_citations(text) == ["A", "B"]

    def test_no_citations(self) -> None:
        assert extract_citations("No sources here.") == []

    def test_deduplication(self) -> None:
        text = "[Source: A] [Source: A]"
        assert extract_citations(text) == ["A"]


# ---------------------------------------------------------------------------
# Metrics tests
# ---------------------------------------------------------------------------

class TestMetrics:
    def test_compute_empty(self) -> None:
        m = compute_metrics([])
        assert m.total_entries == 0

    def test_compute_basic(self) -> None:
        results = _make_results()
        m = compute_metrics(results)
        assert m.total_entries == 2
        assert m.answer_accuracy == 1.0
        assert m.hallucination_rate == 0.0

    def test_passing_flag_with_config(self) -> None:
        results = _make_results()
        config = EvalConfig(
            accuracy_target=0.5,
            citation_precision_target=0.5,
            citation_recall_target=0.5,
            hallucination_max=0.1,
            latency_p50_target_ms=5000,
            latency_p95_target_ms=10000,
        )
        m = compute_metrics(results, config)
        assert m.passing is True

    def test_failing_flag(self) -> None:
        results = _make_results()
        config = EvalConfig(accuracy_target=1.0, hallucination_max=0.0, latency_p95_target_ms=1.0)
        m = compute_metrics(results, config)
        # Latency p95 is 195 which exceeds 1.0 ms target
        assert m.passing is False


# ---------------------------------------------------------------------------
# Report formatting tests
# ---------------------------------------------------------------------------

class TestReports:
    def test_format_report_contains_key_info(self) -> None:
        report = EvalReport(
            results=_make_results(),
            metrics=compute_metrics(_make_results()),
            model_id="test-model",
        )
        text = format_report(report)
        assert "test-model" in text
        assert "Answer accuracy" in text
        assert "PASS" in text or "FAIL" in text

    def test_export_report_creates_file(self, tmp_path: Path) -> None:
        report = EvalReport(
            results=_make_results(),
            metrics=compute_metrics(_make_results()),
            model_id="test-model",
        )
        out = tmp_path / "report.json"
        export_report(report, out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["model_id"] == "test-model"
        assert "metrics" in data


# ---------------------------------------------------------------------------
# Harness integration tests (mocked LLM)
# ---------------------------------------------------------------------------

class TestEvalHarness:
    @pytest.mark.asyncio
    async def test_harness_run(self) -> None:
        mock_client = MockLLMClient()

        # First call per entry: generate answer. Second call: judge verdict.
        answer_response = "Call 311 to report potholes. [Source: 311 Guide]"
        judge_response = json.dumps({"accurate": True, "hallucination": False, "reasoning": "ok"})
        mock_client._generate.side_effect = [
            answer_response, judge_response,  # entry 1
            answer_response, judge_response,  # entry 2
        ]

        entries = _make_entries()
        harness = EvalHarness(mock_client, EvalConfig())
        report = await harness.run(entries)

        assert len(report.results) == 2
        assert report.metrics.total_entries == 2
        assert report.model_id == "llama3.1:8b"
        assert all(r.answer_accurate for r in report.results)

    @pytest.mark.asyncio
    async def test_harness_handles_bad_judge_json(self) -> None:
        mock_client = MockLLMClient()
        mock_client._generate.side_effect = [
            "Some answer. [Source: X]",
            "NOT VALID JSON",  # judge returns garbage
        ]

        entries = _make_entries()[:1]
        harness = EvalHarness(mock_client, EvalConfig())
        report = await harness.run(entries)

        # Should not crash — conservative fallback is accurate=False
        assert len(report.results) == 1
        assert report.results[0].answer_accurate is False
