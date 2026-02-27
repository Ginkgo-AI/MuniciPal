"""PostgreSQL takeover repository.

Uses the `taken_over_by` column on the sessions table.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from municipal.db.engine import DatabaseManager
from municipal.db.models import SessionRow


class PostgresTakeoverRepository:
    """Postgres-backed session takeover management."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def takeover(self, session_id: str, staff_id: str) -> dict[str, Any]:
        async with self._db.session() as db:
            row = await db.get(SessionRow, session_id)
            if row is None:
                raise KeyError(f"Session {session_id!r} not found")
            row.taken_over_by = staff_id
            await db.commit()
        return {
            "session_id": session_id,
            "staff_id": staff_id,
            "status": "taken_over",
        }

    async def release(self, session_id: str) -> dict[str, Any]:
        async with self._db.session() as db:
            row = await db.get(SessionRow, session_id)
            if row is None:
                raise KeyError(f"Session {session_id!r} not found")
            staff_id = row.taken_over_by
            row.taken_over_by = None
            await db.commit()
        return {
            "session_id": session_id,
            "staff_id": staff_id,
            "status": "released",
        }

    async def is_taken_over(self, session_id: str) -> bool:
        async with self._db.session() as db:
            row = await db.get(SessionRow, session_id)
            return row is not None and row.taken_over_by is not None

    async def get_controller(self, session_id: str) -> str | None:
        async with self._db.session() as db:
            row = await db.get(SessionRow, session_id)
            return row.taken_over_by if row else None

    async def list_takeovers(self) -> dict[str, str]:
        async with self._db.session() as db:
            result = await db.execute(
                select(SessionRow).where(SessionRow.taken_over_by.isnot(None))
            )
            return {
                r.session_id: r.taken_over_by
                for r in result.scalars().all()
            }
