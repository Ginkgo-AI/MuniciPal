"""Tests for WP3: Repository protocol conformance.

Verifies that existing in-memory stores satisfy the runtime-checkable
Protocol interfaces — ensuring zero changes to existing stores.
"""

from __future__ import annotations

import asyncio

import pytest

from municipal.chat.session import SessionManager
from municipal.governance.audit import AuditLogger
from municipal.graph.store import GraphStore
from municipal.intake.store import IntakeStore
from municipal.notifications.store import NotificationStore
from municipal.repositories import resolve
from municipal.repositories.protocols import (
    FeedbackRepository,
    GraphRepository,
    IntakeRepository,
    NotificationRepository,
    PaymentRepository,
    SessionRepository,
    ShadowComparisonRepository,
    TakeoverRepository,
)
from municipal.web.finance_router import PaymentStore
from municipal.web.mission_control import (
    FeedbackStore,
    ShadowComparisonStore,
)
from municipal.web.mission_control_v1 import SessionTakeoverManager


def test_session_manager_satisfies_protocol():
    assert isinstance(SessionManager(), SessionRepository)


def test_intake_store_satisfies_protocol():
    assert isinstance(IntakeStore(), IntakeRepository)


def test_graph_store_satisfies_protocol():
    assert isinstance(GraphStore(), GraphRepository)


def test_notification_store_satisfies_protocol():
    assert isinstance(NotificationStore(), NotificationRepository)


def test_feedback_store_satisfies_protocol():
    assert isinstance(FeedbackStore(), FeedbackRepository)


def test_shadow_comparison_store_satisfies_protocol():
    assert isinstance(ShadowComparisonStore(), ShadowComparisonRepository)


def test_payment_store_satisfies_protocol():
    assert isinstance(PaymentStore(), PaymentRepository)


def test_takeover_manager_satisfies_protocol():
    assert isinstance(SessionTakeoverManager(), TakeoverRepository)


async def test_resolve_with_sync_value():
    """resolve() should return sync values directly."""
    result = await resolve(42)
    assert result == 42


async def test_resolve_with_async_value():
    """resolve() should await coroutines."""

    async def async_fn():
        return "hello"

    result = await resolve(async_fn())
    assert result == "hello"
