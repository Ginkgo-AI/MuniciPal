"""Tests for WP2: DatabaseManager with SQLite async."""

from __future__ import annotations

import pytest

from municipal.db.base import Base
from municipal.db.engine import DatabaseManager

# Import models to populate metadata
import municipal.db.models  # noqa: F401


@pytest.fixture
async def db_manager():
    """Create a DatabaseManager with an in-memory SQLite database."""
    manager = DatabaseManager("sqlite+aiosqlite:///:memory:")
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield manager
    await manager.close()


async def test_engine_creation(db_manager):
    """DatabaseManager should create an engine."""
    assert db_manager.engine is not None


async def test_session_creation(db_manager):
    """DatabaseManager.session() should return an AsyncSession."""
    async with db_manager.session() as session:
        assert session is not None


async def test_create_and_query_session(db_manager):
    """Round-trip: insert a session row and read it back."""
    from municipal.db.models import SessionRow

    async with db_manager.session() as session:
        row = SessionRow(session_id="test-123", session_type="anonymous")
        session.add(row)
        await session.commit()

    async with db_manager.session() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(SessionRow).where(SessionRow.session_id == "test-123")
        )
        found = result.scalar_one_or_none()
        assert found is not None
        assert found.session_id == "test-123"
        assert found.session_type == "anonymous"


async def test_close(db_manager):
    """DatabaseManager.close() should dispose the engine."""
    await db_manager.close()
    # Engine should be disposed — creating a new connection should fail or
    # the pool should be invalidated. We just verify no exception on close.
