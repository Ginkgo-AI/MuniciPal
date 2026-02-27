"""PostgreSQL feedback repository."""

from __future__ import annotations

from sqlalchemy import delete, func, select

from municipal.db.engine import DatabaseManager
from municipal.db.models import FeedbackEntryRow
from municipal.web.mission_control import FeedbackEntry, FlagType


class PostgresFeedbackRepository:
    """Postgres-backed feedback entry storage."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def add(self, entry: FeedbackEntry) -> FeedbackEntry:
        async with self._db.session() as db:
            row = FeedbackEntryRow(
                feedback_id=entry.feedback_id,
                timestamp=entry.timestamp,
                staff_id=entry.staff_id,
                session_id=entry.session_id,
                message_index=entry.message_index,
                flag_type=entry.flag_type.value,
                note=entry.note,
            )
            db.add(row)
            await db.commit()
        return entry

    async def list_all(self) -> list[FeedbackEntry]:
        async with self._db.session() as db:
            result = await db.execute(
                select(FeedbackEntryRow).order_by(FeedbackEntryRow.timestamp.desc())
            )
            return [self._row_to_entry(r) for r in result.scalars().all()]

    async def get_for_session(self, session_id: str) -> list[FeedbackEntry]:
        async with self._db.session() as db:
            result = await db.execute(
                select(FeedbackEntryRow).where(
                    FeedbackEntryRow.session_id == session_id
                )
            )
            return [self._row_to_entry(r) for r in result.scalars().all()]

    async def get_by_id(self, feedback_id: str) -> FeedbackEntry | None:
        async with self._db.session() as db:
            row = await db.get(FeedbackEntryRow, feedback_id)
            if row is None:
                return None
            return self._row_to_entry(row)

    async def count(self) -> int:
        async with self._db.session() as db:
            result = await db.execute(
                select(func.count()).select_from(FeedbackEntryRow)
            )
            return result.scalar_one()

    async def clear(self) -> None:
        async with self._db.session() as db:
            await db.execute(delete(FeedbackEntryRow))
            await db.commit()

    @staticmethod
    def _row_to_entry(row: FeedbackEntryRow) -> FeedbackEntry:
        return FeedbackEntry(
            feedback_id=row.feedback_id,
            timestamp=row.timestamp,
            staff_id=row.staff_id,
            session_id=row.session_id,
            message_index=row.message_index,
            flag_type=FlagType(row.flag_type),
            note=row.note,
        )
