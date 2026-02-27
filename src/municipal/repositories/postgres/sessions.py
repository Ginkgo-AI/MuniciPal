"""PostgreSQL session repository."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from municipal.chat.session import ChatMessage, ChatSession, MessageRole
from municipal.core.types import SessionType
from municipal.db.engine import DatabaseManager
from municipal.db.models import MessageRow, SessionRow


class PostgresSessionRepository:
    """Postgres-backed session storage."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def create_session(
        self, session_type: SessionType = SessionType.ANONYMOUS
    ) -> ChatSession:
        session = ChatSession(session_type=session_type)
        row = SessionRow(
            session_id=session.session_id,
            session_type=session.session_type.value,
            created_at=session.created_at,
            last_active=session.last_active,
        )
        async with self._db.session() as db:
            db.add(row)
            await db.commit()
        return session

    async def get_session(self, session_id: str) -> ChatSession | None:
        async with self._db.session() as db:
            result = await db.execute(
                select(SessionRow).where(SessionRow.session_id == session_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None

            msg_result = await db.execute(
                select(MessageRow)
                .where(MessageRow.session_id == session_id)
                .order_by(MessageRow.timestamp)
            )
            msg_rows = msg_result.scalars().all()

        return ChatSession(
            session_id=row.session_id,
            session_type=SessionType(row.session_type),
            messages=[
                ChatMessage(
                    role=MessageRole(m.role),
                    content=m.content,
                    timestamp=m.timestamp,
                    citations=m.citations,
                    confidence=m.confidence,
                    low_confidence=m.low_confidence,
                )
                for m in msg_rows
            ],
            created_at=row.created_at,
            last_active=row.last_active,
        )

    async def add_message(self, session_id: str, message: ChatMessage) -> None:
        async with self._db.session() as db:
            result = await db.execute(
                select(SessionRow).where(SessionRow.session_id == session_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                raise KeyError(f"Session {session_id!r} not found")

            msg_row = MessageRow(
                session_id=session_id,
                role=message.role.value,
                content=message.content,
                timestamp=message.timestamp,
                citations=message.citations,
                confidence=message.confidence,
                low_confidence=message.low_confidence,
            )
            db.add(msg_row)
            row.last_active = datetime.now(timezone.utc)
            await db.commit()

    async def list_active_sessions(self) -> list[ChatSession]:
        async with self._db.session() as db:
            result = await db.execute(
                select(SessionRow).order_by(SessionRow.last_active.desc())
            )
            rows = result.scalars().all()

            sessions = []
            for row in rows:
                msg_result = await db.execute(
                    select(MessageRow)
                    .where(MessageRow.session_id == row.session_id)
                    .order_by(MessageRow.timestamp)
                )
                msg_rows = msg_result.scalars().all()

                sessions.append(
                    ChatSession(
                        session_id=row.session_id,
                        session_type=SessionType(row.session_type),
                        messages=[
                            ChatMessage(
                                role=MessageRole(m.role),
                                content=m.content,
                                timestamp=m.timestamp,
                                citations=m.citations,
                                confidence=m.confidence,
                                low_confidence=m.low_confidence,
                            )
                            for m in msg_rows
                        ],
                        created_at=row.created_at,
                        last_active=row.last_active,
                    )
                )
        return sessions
