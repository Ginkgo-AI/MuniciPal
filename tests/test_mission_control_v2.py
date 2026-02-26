"""Tests for Mission Control v2 features: model registry, promotion API, enhanced metrics (WP6)."""

from __future__ import annotations

from unittest.mock import MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient

from municipal.core.config import Settings
from municipal.web.app import create_app
from municipal.web.mission_control_v1 import LLMLatencyTracker


@pytest.fixture
def mock_rag_pipeline():
    from municipal.rag.pipeline import RAGPipeline
    from municipal.rag.citation import CitedAnswer

    pipeline = MagicMock(spec=RAGPipeline)
    pipeline.ask = AsyncMock(
        return_value=CitedAnswer(
            answer="Test", citations=[], confidence=0.9,
            sources_used=0, low_confidence=False,
        )
    )
    return pipeline


@pytest.fixture
def mock_audit_logger(tmp_path):
    from municipal.core.config import AuditConfig
    from municipal.governance.audit import AuditLogger
    return AuditLogger(config=AuditConfig(log_dir=str(tmp_path / "audit")))


@pytest.fixture
def app(mock_rag_pipeline, mock_audit_logger):
    return create_app(
        settings=Settings(),
        rag_pipeline=mock_rag_pipeline,
        audit_logger=mock_audit_logger,
    )


@pytest.fixture
def client(app):
    return TestClient(app)


class TestLLMLatencyTracker:
    def test_empty_tracker(self):
        tracker = LLMLatencyTracker()
        assert tracker.p50() is None
        assert tracker.p95() is None
        assert tracker.count == 0

    def test_single_value(self):
        tracker = LLMLatencyTracker()
        tracker.record(100.0)
        assert tracker.p50() == 100.0
        assert tracker.p95() == 100.0

    def test_multiple_values(self):
        tracker = LLMLatencyTracker()
        for v in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            tracker.record(float(v))
        p50 = tracker.p50()
        p95 = tracker.p95()
        assert p50 is not None
        assert 50 <= p50 <= 60
        assert p95 is not None
        assert p95 >= 90

    def test_rolling_window(self):
        tracker = LLMLatencyTracker(window_size=5)
        for v in [100, 200, 300, 400, 500, 10, 20, 30, 40, 50]:
            tracker.record(float(v))
        assert tracker.count == 5  # window only keeps last 5

    def test_clear(self):
        tracker = LLMLatencyTracker()
        tracker.record(100.0)
        tracker.clear()
        assert tracker.count == 0


class TestModelRegistrationAPI:
    def test_register_candidate(self, client):
        resp = client.post("/api/staff/models/candidate", json={
            "provider": "vllm",
            "base_url": "http://candidate:8000",
            "model": "llama3.1-70b",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "candidate_registered"
        assert data["model"] == "llama3.1-70b"

    def test_list_models(self, client):
        resp = client.get("/api/staff/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "production" in data
        assert "candidate" in data

    def test_promote_candidate(self, client):
        # Register candidate first
        client.post("/api/staff/models/candidate", json={
            "provider": "vllm",
            "base_url": "http://candidate:8000",
            "model": "new-model",
        })
        # Promote
        resp = client.post("/api/staff/models/promote")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "promoted"
        assert data["production"]["model"] == "new-model"

    def test_promote_without_candidate_fails(self, client):
        resp = client.post("/api/staff/models/promote")
        assert resp.status_code == 400


class TestEnhancedMetrics:
    def test_metrics_include_llm_latency(self, app, client):
        # Record some latencies
        app.state.llm_tracker.record(100.0)
        app.state.llm_tracker.record(200.0)

        resp = client.get("/api/staff/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "llm_latency_p50_ms" in data
        assert data["llm_latency_p50_ms"] is not None

    def test_metrics_include_shadow_divergence(self, app, client):
        from municipal.web.mission_control import ShadowComparisonResult

        store = app.state.comparison_store
        store.add(ShadowComparisonResult(
            session_id="s1", user_message="Q",
            production_response="A", candidate_response="B", diverged=True,
        ))
        store.add(ShadowComparisonResult(
            session_id="s1", user_message="Q",
            production_response="A", candidate_response="A", diverged=False,
        ))

        resp = client.get("/api/staff/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["shadow_divergence_rate"] == 0.5
