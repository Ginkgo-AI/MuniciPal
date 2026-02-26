"""Tests for notification engine, service, and store."""

from __future__ import annotations

import pytest

from municipal.notifications.engine import NotificationEngine
from municipal.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
)
from municipal.notifications.service import MockNotificationService
from municipal.notifications.store import NotificationStore


class TestNotificationStore:
    def setup_method(self) -> None:
        self.store = NotificationStore()

    def test_save_and_get(self) -> None:
        n = Notification(session_id="s1", recipient="user@example.com", subject="Test")
        self.store.save(n)
        assert self.store.get(n.id) is n

    def test_get_nonexistent(self) -> None:
        assert self.store.get("nope") is None

    def test_list_for_session(self) -> None:
        self.store.save(Notification(session_id="s1", subject="A"))
        self.store.save(Notification(session_id="s2", subject="B"))
        self.store.save(Notification(session_id="s1", subject="C"))
        assert len(self.store.list_for_session("s1")) == 2

    def test_count(self) -> None:
        self.store.save(Notification(session_id="s1"))
        assert self.store.count == 1


class TestMockNotificationService:
    def setup_method(self) -> None:
        self.service = MockNotificationService()

    def test_send_immediately_delivers(self) -> None:
        n = Notification(session_id="s1", recipient="user@test.com", subject="Hi")
        result = self.service.send(n)
        assert result.status == NotificationStatus.DELIVERED
        assert result.delivered_at is not None

    def test_get_status(self) -> None:
        n = Notification(session_id="s1")
        self.service.send(n)
        assert self.service.get_status(n.id) == NotificationStatus.DELIVERED

    def test_get_status_not_found(self) -> None:
        assert self.service.get_status("nope") is None

    def test_list_for_session(self) -> None:
        self.service.send(Notification(session_id="s1"))
        self.service.send(Notification(session_id="s2"))
        assert len(self.service.list_for_session("s1")) == 1


class TestNotificationEngine:
    def setup_method(self) -> None:
        self.service = MockNotificationService()
        self.engine = NotificationEngine(service=self.service)

    def test_send_direct(self) -> None:
        n = self.engine.send_direct(
            session_id="s1",
            recipient="user@test.com",
            subject="Hello",
            body="World",
        )
        assert n.status == NotificationStatus.DELIVERED
        assert n.subject == "Hello"

    def test_notify_case_update_with_template(self) -> None:
        n = self.engine.notify_case_update(
            template_id="case_submitted",
            session_id="s1",
            recipient="user@test.com",
            context={"case_id": "C-123", "wizard_title": "Permit Application"},
        )
        assert n.status == NotificationStatus.DELIVERED
        assert "C-123" in n.subject
        assert "Permit Application" in n.body

    def test_notify_case_update_no_template(self) -> None:
        n = self.engine.notify_case_update(
            template_id="nonexistent_template",
            session_id="s1",
            recipient="user@test.com",
        )
        assert n.status == NotificationStatus.DELIVERED

    def test_notify_approval_approved(self) -> None:
        n = self.engine.notify_approval_decision(
            approved=True,
            session_id="s1",
            recipient="user@test.com",
            context={"case_id": "C-456"},
        )
        assert "Approved" in n.subject or "approved" in n.body.lower()

    def test_notify_approval_denied(self) -> None:
        n = self.engine.notify_approval_decision(
            approved=False,
            session_id="s1",
            recipient="user@test.com",
            context={"case_id": "C-789", "reason": "Incomplete docs"},
        )
        assert "Denied" in n.subject or "denied" in n.body.lower()

    def test_templates_loaded(self) -> None:
        assert "case_submitted" in self.engine.templates
        assert "ticket_created" in self.engine.templates
