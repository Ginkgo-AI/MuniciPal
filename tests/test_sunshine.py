"""Tests for Sunshine Report generation (Phase 4 — WP5)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from municipal.core.config import Settings
from municipal.core.types import DataClassification
from municipal.governance.approval import ApprovalGate
from municipal.intake.models import Case
from municipal.intake.store import IntakeStore
from municipal.notifications.models import Notification, NotificationChannel, NotificationStatus
from municipal.notifications.store import NotificationStore
from municipal.review.sunshine import SunshineReportGenerator
from municipal.web.app import create_app


# --- Unit tests ---


@pytest.fixture
def store():
    return IntakeStore()


@pytest.fixture
def notification_store():
    return NotificationStore()


@pytest.fixture
def generator(store, notification_store):
    return SunshineReportGenerator(
        intake_store=store,
        notification_store=notification_store,
    )


def _make_case(wizard_id="permit_application", status="submitted", **data_kw) -> Case:
    return Case(
        wizard_id=wizard_id,
        session_id="session-1",
        data=data_kw or {},
        classification=DataClassification.SENSITIVE,
        status=status,
    )


class TestSunshineGenerator:
    def test_empty_store(self, generator):
        report = generator.generate()
        assert report.total_cases == 0
        assert report.cases_by_type == {}

    def test_cases_by_type(self, generator, store):
        store.save_case(_make_case(wizard_id="permit_application"))
        store.save_case(_make_case(wizard_id="permit_application"))
        store.save_case(_make_case(wizard_id="foia_request"))
        report = generator.generate()
        assert report.total_cases == 3
        assert report.cases_by_type["permit_application"] == 2
        assert report.cases_by_type["foia_request"] == 1

    def test_cases_by_status(self, generator, store):
        store.save_case(_make_case(status="submitted"))
        store.save_case(_make_case(status="approved"))
        store.save_case(_make_case(status="submitted"))
        report = generator.generate()
        assert report.cases_by_status["submitted"] == 2
        assert report.cases_by_status["approved"] == 1

    def test_foia_metrics(self, generator, store):
        store.save_case(_make_case(wizard_id="foia_request"))
        store.save_case(_make_case(wizard_id="foia_request"))
        report = generator.generate()
        assert report.foia_metrics["total_requests"] == 2

    def test_311_stats(self, generator, store):
        store.save_case(_make_case(wizard_id="service_request_311", category="pothole"))
        store.save_case(_make_case(wizard_id="service_request_311", category="pothole"))
        store.save_case(_make_case(wizard_id="service_request_311", category="noise"))
        report = generator.generate()
        assert report.service_311_stats["total_tickets"] == 3
        assert report.service_311_stats["by_category"]["pothole"] == 2
        assert report.service_311_stats["by_category"]["noise"] == 1

    def test_notification_summary(self, generator, notification_store):
        notif = Notification(
            session_id="s1",
            channel=NotificationChannel.EMAIL,
            recipient="user@example.com",
            subject="Test",
            body="Test body",
            status=NotificationStatus.DELIVERED,
        )
        notification_store.save(notif)
        report = generator.generate()
        assert report.notification_summary["total_sent"] == 1

    def test_approval_stats(self, store):
        approval_gate = ApprovalGate()
        gen = SunshineReportGenerator(
            intake_store=store,
            approval_gate=approval_gate,
        )
        # Create some approval requests
        approval_gate.request_approval("permit_decision", "case:1", "user1")
        req = approval_gate.request_approval("permit_decision", "case:2", "user2")
        approval_gate.approve(req.request_id, "admin1")
        approval_gate.approve(req.request_id, "admin2")

        report = gen.generate()
        assert report.approval_stats["total_requests"] == 2
        assert report.approval_stats["pending"] == 1
        assert report.approval_stats["approved"] == 1

    def test_report_model_fields(self, generator):
        report = generator.generate()
        assert report.title == "Annual Sunshine Report"
        assert report.generated_at is not None


# --- API integration tests ---


@pytest.fixture
def client():
    mock_rag = MagicMock()
    mock_rag.query.return_value = MagicMock(answer="test", sources=[], confidence=0.9)
    app = create_app(settings=Settings(), rag_pipeline=mock_rag)
    return TestClient(app)


class TestSunshineAPI:
    def test_sunshine_json_endpoint(self, client):
        resp = client.get("/api/review/sunshine")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cases" in data
        assert "cases_by_type" in data
        assert data["title"] == "Annual Sunshine Report"

    def test_sunshine_pdf_endpoint(self, client):
        resp = client.get("/api/review/sunshine/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        # PDF should start with %PDF
        assert resp.content[:4] == b"%PDF"
