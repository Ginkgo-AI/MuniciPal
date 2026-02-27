"""Tests for WP6: PostgresAuditRepository — hash chain integrity."""

from __future__ import annotations

import pytest

from municipal.core.types import AuditEvent, DataClassification
from municipal.db.base import Base
from municipal.db.engine import DatabaseManager
from municipal.repositories.postgres.audit import PostgresAuditRepository

import municipal.db.models  # noqa: F401


@pytest.fixture
async def repo():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield PostgresAuditRepository(db)
    await db.close()


def _make_event(action: str = "test_action") -> AuditEvent:
    return AuditEvent(
        session_id="s1",
        actor="tester",
        action=action,
        resource="test-resource",
        classification=DataClassification.PUBLIC,
    )


async def test_log_event(repo):
    entry = await repo.log(_make_event())
    assert entry.entry_hash
    assert entry.previous_hash


async def test_hash_chain_integrity(repo):
    for i in range(5):
        await repo.log(_make_event(f"action_{i}"))
    assert await repo.verify_chain() is True


async def test_query_by_actor(repo):
    await repo.log(_make_event())
    events = await repo.query({"actor": "tester"})
    assert len(events) == 1
    assert events[0].actor == "tester"


async def test_query_by_session(repo):
    await repo.log(_make_event())
    events = await repo.query({"session_id": "s1"})
    assert len(events) == 1


async def test_empty_chain_is_valid(repo):
    assert await repo.verify_chain() is True
