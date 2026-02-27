"""Async database engine and session management."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class DatabaseManager:
    """Manages the async SQLAlchemy engine and session factory.

    Usage::

        db = DatabaseManager("postgresql+asyncpg://user:pass@host/db")
        async with db.session() as session:
            ...
        await db.close()
    """

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 5,
    ) -> None:
        kwargs: dict[str, Any] = {"echo": echo}
        if "sqlite" not in database_url:
            kwargs["pool_size"] = pool_size
            kwargs["pool_pre_ping"] = True
        self._engine: AsyncEngine = create_async_engine(database_url, **kwargs)
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    def session(self) -> AsyncSession:
        """Create a new async session."""
        return self._session_factory()

    async def close(self) -> None:
        """Dispose of the engine connection pool."""
        await self._engine.dispose()
