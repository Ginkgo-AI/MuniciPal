"""Tests for session takeover routing and staff messaging (WP6)."""

from __future__ import annotations

from unittest.mock import MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient

from municipal.core.config import Settings
from municipal.web.app import create_app


@pytest.fixture
def mock_rag_pipeline():
    from municipal.rag.pipeline import RAGPipeline
    from municipal.rag.citation import CitedAnswer

    pipeline = MagicMock(spec=RAGPipeline)
    pipeline.ask = AsyncMock(
        return_value=CitedAnswer(
            answer="RAG answer",
            citations=[],
            confidence=0.9,
            sources_used=0,
            low_confidence=False,
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
    from tests.conftest import install_staff_token
    token = install_staff_token(app)
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


def _create_session(client) -> str:
    resp = client.post("/api/sessions", json={"session_type": "anonymous"})
    return resp.json()["session_id"]


class TestTakeoverRouting:
    def test_normal_chat_returns_rag_answer(self, client):
        session_id = _create_session(client)
        resp = client.post("/api/chat", json={
            "session_id": session_id,
            "message": "What is recycling?",
        })
        assert resp.status_code == 200
        assert "RAG answer" in resp.json()["response"]

    def test_takeover_returns_placeholder(self, client):
        session_id = _create_session(client)

        # Take over the session
        client.post(f"/api/staff/sessions/{session_id}/takeover", json={
            "staff_id": "admin",
        })

        # Chat should return takeover message
        resp = client.post("/api/chat", json={
            "session_id": session_id,
            "message": "Hello?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "staff member" in data["response"].lower()

    def test_release_restores_normal_chat(self, client):
        session_id = _create_session(client)

        # Take over then release
        client.post(f"/api/staff/sessions/{session_id}/takeover", json={
            "staff_id": "admin",
        })
        client.post(f"/api/staff/sessions/{session_id}/release")

        # Chat should work normally again
        resp = client.post("/api/chat", json={
            "session_id": session_id,
            "message": "What is recycling?",
        })
        assert resp.status_code == 200
        assert "RAG answer" in resp.json()["response"]


class TestStaffMessage:
    def test_staff_sends_message(self, client):
        session_id = _create_session(client)

        resp = client.post(f"/api/staff/sessions/{session_id}/message", json={
            "staff_id": "admin",
            "message": "I'll help you with this.",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["staff_id"] == "admin"
        assert data["message"] == "I'll help you with this."

    def test_staff_message_appears_in_session(self, client):
        session_id = _create_session(client)

        client.post(f"/api/staff/sessions/{session_id}/message", json={
            "staff_id": "admin",
            "message": "Hello from staff.",
        })

        # Check session messages
        resp = client.get(f"/api/sessions/{session_id}")
        messages = resp.json()["messages"]
        assert any("[Staff: admin]" in m["content"] for m in messages)

    def test_staff_message_to_nonexistent_session(self, client):
        resp = client.post("/api/staff/sessions/nonexistent/message", json={
            "staff_id": "admin",
            "message": "Hello",
        })
        assert resp.status_code == 404


class TestShadowComparisonAPI:
    def test_list_comparisons_empty(self, client):
        resp = client.get("/api/staff/shadow/comparisons")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_shadow_stats_empty(self, client):
        resp = client.get("/api/staff/shadow/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_comparisons"] == 0
        assert data["divergence_rate"] == 0.0

    def test_shadow_comparisons_with_data(self, app, client):
        from municipal.web.mission_control import ShadowComparisonResult

        store = app.state.comparison_store
        store.add(ShadowComparisonResult(
            session_id="s1", user_message="Q1",
            production_response="A", candidate_response="B", diverged=True,
        ))

        resp = client.get("/api/staff/shadow/comparisons")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["diverged"] is True

    def test_shadow_stats_with_data(self, app, client):
        from municipal.web.mission_control import ShadowComparisonResult

        store = app.state.comparison_store
        store.add(ShadowComparisonResult(
            session_id="s1", user_message="Q1",
            production_response="A", candidate_response="A", diverged=False,
        ))
        store.add(ShadowComparisonResult(
            session_id="s1", user_message="Q2",
            production_response="A", candidate_response="B", diverged=True,
        ))

        resp = client.get("/api/staff/shadow/stats")
        data = resp.json()
        assert data["total_comparisons"] == 2
        assert data["divergence_rate"] == 0.5
