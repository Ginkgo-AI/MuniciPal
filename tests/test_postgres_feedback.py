"""Tests for WP4: PostgresFeedbackRepository with SQLite async."""

from __future__ import annotations

import pytest

from municipal.db.base import Base
from municipal.db.engine import DatabaseManager
from municipal.repositories.postgres.feedback import PostgresFeedbackRepository
from municipal.web.mission_control import FeedbackEntry, FlagType

import municipal.db.models  # noqa: F401


@pytest.fixture
async def repo():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield PostgresFeedbackRepository(db)
    await db.close()


async def test_add_and_get_by_id(repo):
    entry = FeedbackEntry(
        session_id="s1",
        message_index=0,
        flag_type=FlagType.INACCURATE,
        note="Wrong answer",
    )
    await repo.add(entry)
    found = await repo.get_by_id(entry.feedback_id)
    assert found is not None
    assert found.note == "Wrong answer"
    assert found.flag_type == FlagType.INACCURATE


async def test_list_all(repo):
    for i in range(3):
        await repo.add(
            FeedbackEntry(session_id="s1", message_index=i, flag_type=FlagType.OTHER)
        )
    assert len(await repo.list_all()) == 3


async def test_get_for_session(repo):
    await repo.add(FeedbackEntry(session_id="s1", message_index=0, flag_type=FlagType.OTHER))
    await repo.add(FeedbackEntry(session_id="s2", message_index=0, flag_type=FlagType.OTHER))
    assert len(await repo.get_for_session("s1")) == 1


async def test_count(repo):
    await repo.add(FeedbackEntry(session_id="s1", message_index=0, flag_type=FlagType.OTHER))
    assert await repo.count() == 1


async def test_clear(repo):
    await repo.add(FeedbackEntry(session_id="s1", message_index=0, flag_type=FlagType.OTHER))
    await repo.clear()
    assert await repo.count() == 0
