"""Tests for WP4: PostgresNotificationRepository with SQLite async."""

from __future__ import annotations

import pytest

from municipal.db.base import Base
from municipal.db.engine import DatabaseManager
from municipal.notifications.models import Notification, NotificationChannel
from municipal.repositories.postgres.notifications import PostgresNotificationRepository

import municipal.db.models  # noqa: F401


@pytest.fixture
async def repo():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield PostgresNotificationRepository(db)
    await db.close()


async def test_save_and_get(repo):
    n = Notification(session_id="s1", recipient="test@example.com", subject="Hi")
    await repo.save(n)
    found = await repo.get(n.id)
    assert found is not None
    assert found.recipient == "test@example.com"


async def test_list_for_session(repo):
    await repo.save(Notification(session_id="s1", subject="A"))
    await repo.save(Notification(session_id="s2", subject="B"))
    assert len(await repo.list_for_session("s1")) == 1


async def test_list_all(repo):
    await repo.save(Notification(session_id="s1"))
    await repo.save(Notification(session_id="s2"))
    assert len(await repo.list_all()) == 2


async def test_update_notification(repo):
    n = Notification(session_id="s1", subject="Original")
    await repo.save(n)
    n.subject = "Updated"
    await repo.save(n)
    found = await repo.get(n.id)
    assert found.subject == "Updated"
