"""Chat session management with in-memory storage.

Provides models for chat messages and sessions, plus a SessionManager
that stores sessions in memory (suitable for Phase 1 single-instance
deployment).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from municipal.core.types import SessionType


class MessageRole(str, Enum):
    """Roles for chat messages."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """A single message in a chat session."""

    role: MessageRole
    content: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    citations: list[dict[str, Any]] | None = None
    confidence: float | None = None
    low_confidence: bool | None = None


class ChatSession(BaseModel):
    """A chat session containing a sequence of messages."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_type: SessionType = SessionType.ANONYMOUS
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_active: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class SessionManager:
    """In-memory session store.

    Manages creation, retrieval, and updates for chat sessions.
    Suitable for Phase 1 single-instance deployment. A persistent
    backend can be substituted later without changing the interface.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}

    def create_session(
        self, session_type: SessionType = SessionType.ANONYMOUS
    ) -> ChatSession:
        """Create a new chat session.

        Args:
            session_type: The type of session to create.

        Returns:
            The newly created ChatSession.
        """
        session = ChatSession(session_type=session_type)
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        """Retrieve a session by ID.

        Args:
            session_id: The UUID of the session.

        Returns:
            The ChatSession if found, or None.
        """
        return self._sessions.get(session_id)

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Append a message to an existing session.

        Args:
            session_id: The UUID of the session.
            message: The ChatMessage to append.

        Raises:
            KeyError: If the session does not exist.
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Session {session_id!r} not found")
        session.messages.append(message)
        session.last_active = datetime.now(timezone.utc)

    def list_active_sessions(self) -> list[ChatSession]:
        """Return all sessions, ordered by most recently active first.

        Returns:
            List of all ChatSession instances.
        """
        return sorted(
            self._sessions.values(),
            key=lambda s: s.last_active,
            reverse=True,
        )
