"""In-memory notification store."""

from __future__ import annotations

from municipal.notifications.models import Notification


class NotificationStore:
    """In-memory store for notifications."""

    def __init__(self) -> None:
        self._notifications: dict[str, Notification] = {}

    def save(self, notification: Notification) -> Notification:
        self._notifications[notification.id] = notification
        return notification

    def get(self, notification_id: str) -> Notification | None:
        return self._notifications.get(notification_id)

    def list_for_session(self, session_id: str) -> list[Notification]:
        return [
            n for n in self._notifications.values()
            if n.session_id == session_id
        ]

    def list_all(self) -> list[Notification]:
        return list(self._notifications.values())

    @property
    def count(self) -> int:
        return len(self._notifications)
