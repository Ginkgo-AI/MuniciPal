"""Tests for MuniciPal chat module and web API.

Covers session management, the ChatService response flow (with mocked
RAG pipeline), and FastAPI endpoint integration tests.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from municipal.chat.session import ChatMessage, ChatSession, MessageRole, SessionManager
from municipal.chat.service import ChatService
from municipal.core.config import Settings
from municipal.core.types import DataClassification, SessionType
from municipal.governance.audit import AuditLogger
from municipal.rag.citation import Citation, CitedAnswer
from municipal.rag.pipeline import RAGPipeline
from municipal.web.app import create_app


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def session_manager():
    return SessionManager()


@pytest.fixture
def mock_rag_pipeline():
    """Create a mock RAGPipeline with a working ask() method."""
    pipeline = MagicMock(spec=RAGPipeline)
    pipeline.ask = AsyncMock(
        return_value=CitedAnswer(
            answer="The recycling pickup is on Tuesdays.",
            citations=[
                Citation(
                    source="waste-management.pdf",
                    section="Schedule",
                    quote="Recycling collection occurs every Tuesday.",
                    relevance_score=0.92,
                )
            ],
            confidence=0.88,
            sources_used=1,
            low_confidence=False,
        )
    )
    return pipeline


@pytest.fixture
def mock_audit_logger(tmp_path):
    """Create an AuditLogger writing to a temp directory."""
    from municipal.core.config import AuditConfig

    config = AuditConfig(log_dir=str(tmp_path / "audit"))
    return AuditLogger(config=config)


@pytest.fixture
def chat_service(mock_rag_pipeline, session_manager, mock_audit_logger):
    return ChatService(
        rag_pipeline=mock_rag_pipeline,
        session_manager=session_manager,
        audit_logger=mock_audit_logger,
    )


@pytest.fixture
def app(mock_rag_pipeline, mock_audit_logger):
    """Create a FastAPI app with mocked dependencies."""
    return create_app(
        settings=Settings(),
        rag_pipeline=mock_rag_pipeline,
        audit_logger=mock_audit_logger,
    )


@pytest.fixture
def client(app):
    return TestClient(app)


# =========================================================================
# Session Management Tests
# =========================================================================


class TestSessionManager:
    def test_create_session(self, session_manager):
        session = session_manager.create_session()
        assert isinstance(session, ChatSession)
        assert session.session_type == SessionType.ANONYMOUS
        assert session.messages == []
        assert session.session_id is not None

    def test_create_session_with_type(self, session_manager):
        session = session_manager.create_session(SessionType.VERIFIED)
        assert session.session_type == SessionType.VERIFIED

    def test_get_session(self, session_manager):
        session = session_manager.create_session()
        retrieved = session_manager.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_get_session_not_found(self, session_manager):
        result = session_manager.get_session("nonexistent-id")
        assert result is None

    def test_add_message(self, session_manager):
        session = session_manager.create_session()
        msg = ChatMessage(role=MessageRole.USER, content="Hello")
        session_manager.add_message(session.session_id, msg)

        updated = session_manager.get_session(session.session_id)
        assert len(updated.messages) == 1
        assert updated.messages[0].content == "Hello"

    def test_add_message_updates_last_active(self, session_manager):
        session = session_manager.create_session()
        original_active = session.last_active

        msg = ChatMessage(role=MessageRole.USER, content="Test")
        session_manager.add_message(session.session_id, msg)

        updated = session_manager.get_session(session.session_id)
        assert updated.last_active >= original_active

    def test_add_message_nonexistent_session(self, session_manager):
        msg = ChatMessage(role=MessageRole.USER, content="Hello")
        with pytest.raises(KeyError, match="not found"):
            session_manager.add_message("bad-id", msg)

    def test_list_active_sessions(self, session_manager):
        s1 = session_manager.create_session()
        s2 = session_manager.create_session()

        # Touch s1 to make it most recent
        session_manager.add_message(
            s1.session_id, ChatMessage(role=MessageRole.USER, content="hi")
        )

        sessions = session_manager.list_active_sessions()
        assert len(sessions) == 2
        # s1 should be first (most recently active)
        assert sessions[0].session_id == s1.session_id


# =========================================================================
# ChatService Tests
# =========================================================================


class TestChatService:
    @pytest.mark.asyncio
    async def test_respond_success(self, chat_service, session_manager):
        session = session_manager.create_session()

        response = await chat_service.respond(
            session_id=session.session_id,
            user_message="When is recycling pickup?",
        )

        assert response.role == MessageRole.ASSISTANT
        assert "recycling" in response.content.lower() or "Tuesday" in response.content
        assert response.confidence == 0.88
        assert response.low_confidence is False
        assert response.citations is not None
        assert len(response.citations) == 1

    @pytest.mark.asyncio
    async def test_respond_records_user_message(self, chat_service, session_manager):
        session = session_manager.create_session()

        await chat_service.respond(
            session_id=session.session_id,
            user_message="Test question",
        )

        updated = session_manager.get_session(session.session_id)
        # Should have user message + assistant response
        assert len(updated.messages) == 2
        assert updated.messages[0].role == MessageRole.USER
        assert updated.messages[0].content == "Test question"
        assert updated.messages[1].role == MessageRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_respond_low_confidence_kill_switch(
        self, session_manager, mock_audit_logger
    ):
        """When confidence is low, the kill-switch message is appended."""
        low_conf_pipeline = MagicMock(spec=RAGPipeline)
        low_conf_pipeline.ask = AsyncMock(
            return_value=CitedAnswer(
                answer="I think maybe it is on Wednesdays.",
                citations=[],
                confidence=0.3,
                sources_used=0,
                low_confidence=True,
            )
        )

        service = ChatService(
            rag_pipeline=low_conf_pipeline,
            session_manager=session_manager,
            audit_logger=mock_audit_logger,
        )

        session = session_manager.create_session()
        response = await service.respond(
            session_id=session.session_id,
            user_message="What day?",
        )

        assert response.low_confidence is True
        assert "contact city staff" in response.content.lower()

    @pytest.mark.asyncio
    async def test_respond_nonexistent_session(self, chat_service):
        with pytest.raises(KeyError, match="not found"):
            await chat_service.respond(
                session_id="nonexistent",
                user_message="Hello",
            )

    @pytest.mark.asyncio
    async def test_respond_rag_error_handled(
        self, session_manager, mock_audit_logger
    ):
        """RAG pipeline errors are caught and a friendly message is returned."""
        error_pipeline = MagicMock(spec=RAGPipeline)
        error_pipeline.ask = AsyncMock(side_effect=RuntimeError("LLM is down"))

        service = ChatService(
            rag_pipeline=error_pipeline,
            session_manager=session_manager,
            audit_logger=mock_audit_logger,
        )

        session = session_manager.create_session()
        response = await service.respond(
            session_id=session.session_id,
            user_message="Test",
        )

        assert response.role == MessageRole.ASSISTANT
        assert "error" in response.content.lower()
        assert response.low_confidence is True

    @pytest.mark.asyncio
    async def test_respond_logs_audit_event(
        self, chat_service, session_manager, mock_audit_logger
    ):
        session = session_manager.create_session()

        await chat_service.respond(
            session_id=session.session_id,
            user_message="Recycling question",
        )

        events = mock_audit_logger.query(
            {"session_id": session.session_id, "action": "chat_response"}
        )
        assert len(events) == 1
        assert events[0].details["question"] == "Recycling question"


# =========================================================================
# API Endpoint Tests
# =========================================================================


class TestAPIEndpoints:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "municipal-digital-librarian"

    def test_create_session(self, client):
        response = client.post(
            "/api/sessions", json={"session_type": "anonymous"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["session_type"] == "anonymous"
        assert data["message_count"] == 0

    def test_create_session_invalid_type(self, client):
        response = client.post(
            "/api/sessions", json={"session_type": "invalid"}
        )
        assert response.status_code == 400

    def test_get_session(self, client):
        # Create a session first
        create_resp = client.post(
            "/api/sessions", json={"session_type": "anonymous"}
        )
        session_id = create_resp.json()["session_id"]

        # Retrieve it
        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["messages"] == []

    def test_get_session_not_found(self, client):
        response = client.get("/api/sessions/nonexistent")
        assert response.status_code == 404

    def test_list_sessions(self, client):
        # Create two sessions
        client.post("/api/sessions", json={"session_type": "anonymous"})
        client.post("/api/sessions", json={"session_type": "anonymous"})

        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_chat_endpoint(self, client):
        # Create session
        create_resp = client.post(
            "/api/sessions", json={"session_type": "anonymous"}
        )
        session_id = create_resp.json()["session_id"]

        # Send chat message
        response = client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "When is recycling?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "citations" in data
        assert "confidence" in data
        assert "low_confidence" in data
        assert isinstance(data["citations"], list)

    def test_chat_endpoint_session_not_found(self, client):
        response = client.post(
            "/api/chat",
            json={"session_id": "bad-id", "message": "Hello"},
        )
        assert response.status_code == 404

    def test_serve_chat_ui(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "MuniciPal" in response.text
        assert "Digital Librarian" in response.text
        assert "Disclaimer" in response.text

    def test_chat_preserves_history(self, client):
        """After chatting, session history reflects the exchange."""
        create_resp = client.post(
            "/api/sessions", json={"session_type": "anonymous"}
        )
        session_id = create_resp.json()["session_id"]

        client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "Hello"},
        )

        session_resp = client.get(f"/api/sessions/{session_id}")
        data = session_resp.json()
        assert data["message_count"] == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"
