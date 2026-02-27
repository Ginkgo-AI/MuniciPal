"""PostgreSQL auth token repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from municipal.db.engine import DatabaseManager
from municipal.db.models import AuthTokenRow


class PostgresAuthTokenRepository:
    """Postgres-backed auth token storage."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def save_token(
        self,
        token: str,
        user_id: str,
        tier: str,
        display_name: str,
        expires_at: datetime,
    ) -> None:
        async with self._db.session() as db:
            existing = await db.get(AuthTokenRow, token)
            if existing:
                existing.user_id = user_id
                existing.tier = tier
                existing.display_name = display_name
                existing.expires_at = expires_at
            else:
                row = AuthTokenRow(
                    token=token,
                    user_id=user_id,
                    tier=tier,
                    display_name=display_name,
                    expires_at=expires_at,
                )
                db.add(row)
            await db.commit()

    async def get_token(self, token: str) -> dict[str, Any] | None:
        async with self._db.session() as db:
            row = await db.get(AuthTokenRow, token)
            if row is None:
                return None
            return {
                "user_id": row.user_id,
                "tier": row.tier,
                "display_name": row.display_name,
                "expires_at": row.expires_at,
            }

    async def delete_token(self, token: str) -> bool:
        async with self._db.session() as db:
            row = await db.get(AuthTokenRow, token)
            if row is None:
                return False
            await db.delete(row)
            await db.commit()
            return True
