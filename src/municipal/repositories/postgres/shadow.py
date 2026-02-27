"""PostgreSQL shadow comparison repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, select

from municipal.db.engine import DatabaseManager
from municipal.db.models import ShadowComparisonRow
from municipal.web.mission_control import ShadowComparisonResult


class PostgresShadowComparisonRepository:
    """Postgres-backed shadow comparison storage."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def add(self, result: ShadowComparisonResult) -> ShadowComparisonResult:
        async with self._db.session() as db:
            row = ShadowComparisonRow(
                comparison_id=result.comparison_id,
                session_id=result.session_id,
                user_message=result.user_message,
                production_response=result.production_response,
                candidate_response=result.candidate_response,
                diverged=result.diverged,
                timestamp=result.timestamp,
            )
            db.add(row)
            await db.commit()
        return result

    async def list_all(self) -> list[ShadowComparisonResult]:
        async with self._db.session() as db:
            result = await db.execute(
                select(ShadowComparisonRow).order_by(ShadowComparisonRow.timestamp.desc())
            )
            return [self._row_to_result(r) for r in result.scalars().all()]

    async def get_for_session(self, session_id: str) -> list[ShadowComparisonResult]:
        async with self._db.session() as db:
            result = await db.execute(
                select(ShadowComparisonRow).where(
                    ShadowComparisonRow.session_id == session_id
                )
            )
            return [self._row_to_result(r) for r in result.scalars().all()]

    async def stats(self) -> dict[str, Any]:
        async with self._db.session() as db:
            total_result = await db.execute(
                select(func.count()).select_from(ShadowComparisonRow)
            )
            total = total_result.scalar_one()

            diverged_result = await db.execute(
                select(func.count())
                .select_from(ShadowComparisonRow)
                .where(ShadowComparisonRow.diverged.is_(True))
            )
            diverged = diverged_result.scalar_one()

        return {
            "total_comparisons": total,
            "diverged_count": diverged,
            "divergence_rate": round(diverged / total, 4) if total > 0 else 0.0,
        }

    async def clear(self) -> None:
        async with self._db.session() as db:
            await db.execute(delete(ShadowComparisonRow))
            await db.commit()

    @staticmethod
    def _row_to_result(row: ShadowComparisonRow) -> ShadowComparisonResult:
        return ShadowComparisonResult(
            comparison_id=row.comparison_id,
            session_id=row.session_id,
            user_message=row.user_message,
            production_response=row.production_response,
            candidate_response=row.candidate_response,
            diverged=row.diverged,
            timestamp=row.timestamp,
        )
