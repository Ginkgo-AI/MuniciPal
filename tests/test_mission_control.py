"""Tests for Mission Control v0 — staff dashboard routes and stores."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from municipal.web.mission_control import (
    FeedbackEntry,
    FeedbackStore,
    FlagType,
    ShadowModeManager,
)


# ---------------------------------------------------------------------------
# FeedbackStore unit tests
# ---------------------------------------------------------------------------


class TestFeedbackStore:
    """Tests for the in-memory FeedbackStore."""

    def test_add_and_count(self) -> None:
        store = FeedbackStore()
        assert store.count() == 0

        entry = FeedbackEntry(
            session_id="sess-1",
            message_index=0,
            flag_type=FlagType.INACCURATE,
            note="Wrong answer",
        )
        result = store.add(entry)
        assert result.feedback_id == entry.feedback_id
        assert store.count() == 1

    def test_list_all_newest_first(self) -> None:
        store = FeedbackStore()
        e1 = FeedbackEntry(session_id="s1", message_index=0, flag_type=FlagType.INACCURATE)
        e2 = FeedbackEntry(session_id="s2", message_index=1, flag_type=FlagType.OTHER)
        store.add(e1)
        store.add(e2)

        entries = store.list_all()
        assert len(entries) == 2
        # Newest first (e2 created after e1)
        assert entries[0].session_id == "s2"

    def test_get_for_session(self) -> None:
        store = FeedbackStore()
        store.add(FeedbackEntry(session_id="s1", message_index=0, flag_type=FlagType.INACCURATE))
        store.add(FeedbackEntry(session_id="s2", message_index=0, flag_type=FlagType.OTHER))
        store.add(FeedbackEntry(session_id="s1", message_index=1, flag_type=FlagType.MISSING_INFO))

        result = store.get_for_session("s1")
        assert len(result) == 2
        assert all(e.session_id == "s1" for e in result)

    def test_get_by_id(self) -> None:
        store = FeedbackStore()
        entry = FeedbackEntry(session_id="s1", message_index=0, flag_type=FlagType.INACCURATE)
        store.add(entry)

        found = store.get_by_id(entry.feedback_id)
        assert found is not None
        assert found.feedback_id == entry.feedback_id

        assert store.get_by_id("nonexistent") is None

    def test_clear(self) -> None:
        store = FeedbackStore()
        store.add(FeedbackEntry(session_id="s1", message_index=0, flag_type=FlagType.INACCURATE))
        assert store.count() == 1
        store.clear()
        assert store.count() == 0


# ---------------------------------------------------------------------------
# ShadowModeManager unit tests
# ---------------------------------------------------------------------------


class TestShadowModeManager:
    """Tests for the in-memory ShadowModeManager."""

    def test_enable_and_is_active(self) -> None:
        mgr = ShadowModeManager()
        assert mgr.is_active("sess-1") is False
        mgr.enable("sess-1")
        assert mgr.is_active("sess-1") is True

    def test_disable(self) -> None:
        mgr = ShadowModeManager()
        mgr.enable("sess-1")
        mgr.disable("sess-1")
        assert mgr.is_active("sess-1") is False

    def test_toggle(self) -> None:
        mgr = ShadowModeManager()
        result = mgr.toggle("sess-1", True)
        assert result is True
        assert mgr.is_active("sess-1") is True

        result = mgr.toggle("sess-1", False)
        assert result is False
        assert mgr.is_active("sess-1") is False

    def test_list_active(self) -> None:
        mgr = ShadowModeManager()
        mgr.enable("s1")
        mgr.enable("s2")
        active = mgr.list_active()
        assert set(active) == {"s1", "s2"}

    def test_clear(self) -> None:
        mgr = ShadowModeManager()
        mgr.enable("s1")
        mgr.clear()
        assert mgr.is_active("s1") is False
        assert mgr.list_active() == []

    def test_disable_nonexistent_is_noop(self) -> None:
        mgr = ShadowModeManager()
        mgr.disable("nonexistent")  # Should not raise
        assert mgr.is_active("nonexistent") is False


# ---------------------------------------------------------------------------
# API endpoint tests (using FastAPI TestClient)
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_app():
    """Create a test app with mock dependencies."""
    from unittest.mock import MagicMock

    from municipal.chat.session import ChatMessage, MessageRole, SessionManager
    from municipal.core.config import Settings
    from municipal.core.types import AuditEvent, DataClassification, SessionType
    from municipal.governance.audit import AuditLogger
    from municipal.web.app import create_app

    # Create a mock RAG pipeline
    mock_rag = MagicMock()

    # Create a real audit logger with temp dir
    import tempfile

    tmpdir = tempfile.mkdtemp()
    from municipal.core.config import AuditConfig

    audit_config = AuditConfig(log_dir=tmpdir)
    audit_logger = AuditLogger(config=audit_config)

    # Add a test audit event
    audit_logger.log(
        AuditEvent(
            session_id="test-session",
            actor="test-user",
            action="query",
            resource="knowledge-base",
            classification=DataClassification.PUBLIC,
        )
    )

    settings = Settings()
    app = create_app(
        settings=settings,
        rag_pipeline=mock_rag,
        audit_logger=audit_logger,
    )

    # Create a test session with messages
    sm: SessionManager = app.state.session_manager
    session = sm.create_session(session_type=SessionType.ANONYMOUS)
    sm.add_message(
        session.session_id,
        ChatMessage(role=MessageRole.USER, content="What are library hours?"),
    )
    sm.add_message(
        session.session_id,
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="The library is open 9am-5pm.",
            confidence=0.85,
        ),
    )

    # Store session_id for tests
    app.state._test_session_id = session.session_id

    return app


@pytest.fixture()
def client(test_app):
    """Create a TestClient with staff auth from the test app."""
    from tests.conftest import install_staff_token
    token = install_staff_token(test_app)
    return TestClient(test_app, headers={"Authorization": f"Bearer {token}"})


class TestStaffSessionsAPI:
    """Tests for GET /api/staff/sessions."""

    def test_list_sessions(self, client, test_app) -> None:
        resp = client.get("/api/staff/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        session = data[0]
        assert "session_id" in session
        assert "session_type" in session
        assert "message_count" in session
        assert "shadow_mode" in session
        assert session["shadow_mode"] is False

    def test_sessions_include_shadow_mode(self, client, test_app) -> None:
        sid = test_app.state._test_session_id
        # Enable shadow mode
        client.post("/api/staff/shadow", json={"session_id": sid, "enabled": True})

        resp = client.get("/api/staff/sessions")
        data = resp.json()
        session = next(s for s in data if s["session_id"] == sid)
        assert session["shadow_mode"] is True


class TestStaffAuditAPI:
    """Tests for GET /api/staff/audit."""

    def test_list_audit_entries(self, client) -> None:
        resp = client.get("/api/staff/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        entry = data[0]
        assert "event_id" in entry
        assert "timestamp" in entry
        assert "actor" in entry
        assert "action" in entry
        assert "classification" in entry

    def test_filter_by_actor(self, client) -> None:
        resp = client.get("/api/staff/audit?actor=test-user")
        data = resp.json()
        assert len(data) >= 1
        assert all(e["actor"] == "test-user" for e in data)

    def test_filter_by_nonexistent_actor(self, client) -> None:
        resp = client.get("/api/staff/audit?actor=nonexistent")
        data = resp.json()
        assert data == []

    def test_filter_by_classification(self, client) -> None:
        resp = client.get("/api/staff/audit?classification=public")
        data = resp.json()
        assert len(data) >= 1
        assert all(e["classification"] == "public" for e in data)


class TestFeedbackAPI:
    """Tests for POST/GET /api/staff/feedback."""

    def test_submit_feedback(self, client, test_app) -> None:
        sid = test_app.state._test_session_id
        resp = client.post(
            "/api/staff/feedback",
            json={
                "session_id": sid,
                "message_index": 1,
                "flag_type": "inaccurate",
                "note": "Hours are wrong",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert "feedback_id" in data

    def test_submit_feedback_invalid_flag_type(self, client, test_app) -> None:
        sid = test_app.state._test_session_id
        resp = client.post(
            "/api/staff/feedback",
            json={
                "session_id": sid,
                "message_index": 1,
                "flag_type": "bad_type",
                "note": "",
            },
        )
        assert resp.status_code == 400

    def test_submit_feedback_invalid_session(self, client) -> None:
        resp = client.post(
            "/api/staff/feedback",
            json={
                "session_id": "nonexistent",
                "message_index": 0,
                "flag_type": "inaccurate",
                "note": "",
            },
        )
        assert resp.status_code == 404

    def test_submit_feedback_invalid_message_index(self, client, test_app) -> None:
        sid = test_app.state._test_session_id
        resp = client.post(
            "/api/staff/feedback",
            json={
                "session_id": sid,
                "message_index": 99,
                "flag_type": "inaccurate",
                "note": "",
            },
        )
        assert resp.status_code == 400

    def test_list_feedback(self, client, test_app) -> None:
        sid = test_app.state._test_session_id
        # Submit some feedback first
        client.post(
            "/api/staff/feedback",
            json={
                "session_id": sid,
                "message_index": 1,
                "flag_type": "inaccurate",
                "note": "Test",
            },
        )
        resp = client.get("/api/staff/feedback")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["session_id"] == sid

    def test_list_feedback_by_session(self, client, test_app) -> None:
        sid = test_app.state._test_session_id
        client.post(
            "/api/staff/feedback",
            json={
                "session_id": sid,
                "message_index": 1,
                "flag_type": "other",
                "note": "Filtered",
            },
        )
        resp = client.get(f"/api/staff/feedback?session_id={sid}")
        data = resp.json()
        assert all(e["session_id"] == sid for e in data)


class TestShadowAPI:
    """Tests for POST /api/staff/shadow."""

    def test_toggle_shadow_on(self, client, test_app) -> None:
        sid = test_app.state._test_session_id
        resp = client.post(
            "/api/staff/shadow",
            json={"session_id": sid, "enabled": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == sid
        assert data["shadow_mode"] is True

    def test_toggle_shadow_off(self, client, test_app) -> None:
        sid = test_app.state._test_session_id
        # Enable then disable
        client.post("/api/staff/shadow", json={"session_id": sid, "enabled": True})
        resp = client.post(
            "/api/staff/shadow",
            json={"session_id": sid, "enabled": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["shadow_mode"] is False


class TestStaffPages:
    """Tests for HTML page routes."""

    def test_staff_dashboard(self, client) -> None:
        resp = client.get("/staff/")
        assert resp.status_code == 200
        assert "Mission Control" in resp.text

    def test_staff_sessions_page(self, client) -> None:
        resp = client.get("/staff/sessions")
        assert resp.status_code == 200
        assert "Mission Control" in resp.text

    def test_staff_audit_page(self, client) -> None:
        resp = client.get("/staff/audit")
        assert resp.status_code == 200
        assert "Mission Control" in resp.text


class TestExistingRoutesNotBroken:
    """Verify existing routes still work after adding Mission Control."""

    def test_health_check(self, client) -> None:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    def test_list_sessions(self, client) -> None:
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_session(self, client, test_app) -> None:
        sid = test_app.state._test_session_id
        resp = client.get(f"/api/sessions/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == sid
