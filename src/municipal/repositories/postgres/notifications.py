"""PostgreSQL notification repository."""

from __future__ import annotations

from sqlalchemy import func, select

from municipal.db.engine import DatabaseManager
from municipal.db.models import NotificationRow
from municipal.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
)


class PostgresNotificationRepository:
    """Postgres-backed notification storage."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def save(self, notification: Notification) -> Notification:
        async with self._db.session() as db:
            existing = await db.get(NotificationRow, notification.id)
            if existing:
                existing.session_id = notification.session_id
                existing.channel = notification.channel.value
                existing.recipient = notification.recipient
                existing.subject = notification.subject
                existing.body = notification.body
                existing.status = notification.status.value
                existing.priority = notification.priority.value
                existing.template_id = notification.template_id
                existing.metadata_json = notification.metadata
                existing.delivered_at = notification.delivered_at
            else:
                row = NotificationRow(
                    id=notification.id,
                    session_id=notification.session_id,
                    channel=notification.channel.value,
                    recipient=notification.recipient,
                    subject=notification.subject,
                    body=notification.body,
                    status=notification.status.value,
                    priority=notification.priority.value,
                    template_id=notification.template_id,
                    metadata_json=notification.metadata,
                    created_at=notification.created_at,
                    delivered_at=notification.delivered_at,
                )
                db.add(row)
            await db.commit()
        return notification

    async def get(self, notification_id: str) -> Notification | None:
        async with self._db.session() as db:
            row = await db.get(NotificationRow, notification_id)
            if row is None:
                return None
            return self._row_to_notification(row)

    async def list_for_session(self, session_id: str) -> list[Notification]:
        async with self._db.session() as db:
            result = await db.execute(
                select(NotificationRow).where(NotificationRow.session_id == session_id)
            )
            return [self._row_to_notification(r) for r in result.scalars().all()]

    async def list_all(self) -> list[Notification]:
        async with self._db.session() as db:
            result = await db.execute(select(NotificationRow))
            return [self._row_to_notification(r) for r in result.scalars().all()]

    @property
    def count(self) -> int:
        raise NotImplementedError("Use async_count() instead for Postgres")

    async def async_count(self) -> int:
        async with self._db.session() as db:
            result = await db.execute(select(func.count()).select_from(NotificationRow))
            return result.scalar_one()

    @staticmethod
    def _row_to_notification(row: NotificationRow) -> Notification:
        return Notification(
            id=row.id,
            session_id=row.session_id,
            channel=NotificationChannel(row.channel),
            recipient=row.recipient,
            subject=row.subject,
            body=row.body,
            status=NotificationStatus(row.status),
            priority=NotificationPriority(row.priority),
            template_id=row.template_id,
            metadata=row.metadata_json or {},
            created_at=row.created_at,
            delivered_at=row.delivered_at,
        )
