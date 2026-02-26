"""Notification service Protocol and mock implementation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from municipal.notifications.models import Notification, NotificationStatus
from municipal.notifications.store import NotificationStore


@runtime_checkable
class NotificationService(Protocol):
    """Protocol for notification delivery services."""

    def send(self, notification: Notification) -> Notification: ...

    def get_status(self, notification_id: str) -> NotificationStatus | None: ...

    def list_for_session(self, session_id: str) -> list[Notification]: ...


class MockNotificationService:
    """Mock notification service that immediately delivers all notifications."""

    def __init__(self, store: NotificationStore | None = None) -> None:
        self._store = store or NotificationStore()

    @property
    def store(self) -> NotificationStore:
        return self._store

    def send(self, notification: Notification) -> Notification:
        notification.status = NotificationStatus.DELIVERED
        notification.delivered_at = datetime.now(timezone.utc)
        self._store.save(notification)
        return notification

    def get_status(self, notification_id: str) -> NotificationStatus | None:
        n = self._store.get(notification_id)
        return n.status if n else None

    def list_for_session(self, session_id: str) -> list[Notification]:
        return self._store.list_for_session(session_id)
