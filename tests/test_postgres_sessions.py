"""Tests for WP4: PostgresSessionRepository with SQLite async."""

from __future__ import annotations

import pytest

from municipal.chat.session import ChatMessage, MessageRole
from municipal.core.types import SessionType
from municipal.db.base import Base
from municipal.db.engine import DatabaseManager
from municipal.repositories.postgres.sessions import PostgresSessionRepository

import municipal.db.models  # noqa: F401


@pytest.fixture
async def repo():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield PostgresSessionRepository(db)
    await db.close()


async def test_create_session(repo):
    session = await repo.create_session(SessionType.ANONYMOUS)
    assert session.session_id
    assert session.session_type == SessionType.ANONYMOUS


async def test_get_session(repo):
    created = await repo.create_session()
    found = await repo.get_session(created.session_id)
    assert found is not None
    assert found.session_id == created.session_id


async def test_get_session_not_found(repo):
    assert await repo.get_session("nonexistent") is None


async def test_add_message(repo):
    session = await repo.create_session()
    msg = ChatMessage(role=MessageRole.USER, content="Hello")
    await repo.add_message(session.session_id, msg)

    found = await repo.get_session(session.session_id)
    assert len(found.messages) == 1
    assert found.messages[0].content == "Hello"
    assert found.messages[0].role == MessageRole.USER


async def test_add_message_missing_session(repo):
    msg = ChatMessage(role=MessageRole.USER, content="Hi")
    with pytest.raises(KeyError):
        await repo.add_message("nonexistent", msg)


async def test_list_active_sessions(repo):
    await repo.create_session()
    await repo.create_session(SessionType.VERIFIED)
    sessions = await repo.list_active_sessions()
    assert len(sessions) == 2


async def test_round_trip_with_citations(repo):
    session = await repo.create_session()
    msg = ChatMessage(
        role=MessageRole.ASSISTANT,
        content="Answer",
        citations=[{"source": "doc1"}],
        confidence=0.9,
        low_confidence=False,
    )
    await repo.add_message(session.session_id, msg)

    found = await repo.get_session(session.session_id)
    assert found.messages[0].citations == [{"source": "doc1"}]
    assert found.messages[0].confidence == 0.9
