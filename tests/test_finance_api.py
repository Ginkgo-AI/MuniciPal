"""Tests for Finance API router (WP3)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient

from municipal.core.config import Settings
from municipal.web.app import create_app


@pytest.fixture
def mock_rag_pipeline():
    from municipal.rag.pipeline import RAGPipeline
    from municipal.rag.citation import CitedAnswer, Citation

    pipeline = MagicMock(spec=RAGPipeline)
    pipeline.ask = AsyncMock(
        return_value=CitedAnswer(
            answer="Test answer",
            citations=[],
            confidence=0.9,
            sources_used=0,
            low_confidence=False,
        )
    )
    return pipeline


@pytest.fixture
def mock_audit_logger(tmp_path):
    from municipal.core.config import AuditConfig
    from municipal.governance.audit import AuditLogger

    config = AuditConfig(log_dir=str(tmp_path / "audit"))
    return AuditLogger(config=config)


@pytest.fixture
def app(mock_rag_pipeline, mock_audit_logger):
    return create_app(
        settings=Settings(),
        rag_pipeline=mock_rag_pipeline,
        audit_logger=mock_audit_logger,
    )


@pytest.fixture
def client(app):
    return TestClient(app)


class TestFeeScheduleEndpoints:
    def test_list_all_schedules(self, client):
        resp = client.get("/api/finance/schedule")
        assert resp.status_code == 200
        data = resp.json()
        assert "permit" in data
        assert "foia" in data
        assert "311" in data

    def test_get_permit_schedule(self, client):
        resp = client.get("/api/finance/schedule/permit")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        names = [e["name"] for e in data]
        assert "Building" in names

    def test_get_nonexistent_schedule(self, client):
        resp = client.get("/api/finance/schedule/nonexistent")
        assert resp.status_code == 404


class TestFeeEstimateEndpoint:
    def test_compute_permit_estimate(self, client):
        resp = client.post("/api/finance/estimate", json={
            "wizard_type": "permit",
            "data": {"permit_type": "Building", "area_sqft": 1000},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["wizard_type"] == "permit"
        assert data["total"] == 300.0
        assert len(data["line_items"]) == 2

    def test_compute_foia_estimate(self, client):
        resp = client.post("/api/finance/estimate", json={
            "wizard_type": "foia",
            "data": {"page_count": 100},
        })
        assert resp.status_code == 200
        assert resp.json()["total"] == 7.5

    def test_compute_311_estimate(self, client):
        resp = client.post("/api/finance/estimate", json={
            "wizard_type": "311",
            "data": {},
        })
        assert resp.status_code == 200
        assert resp.json()["total"] == 0.0

    def test_compute_unknown_type(self, client):
        resp = client.post("/api/finance/estimate", json={
            "wizard_type": "unknown",
            "data": {},
        })
        assert resp.status_code == 400

    def test_estimate_with_case_id(self, client):
        resp = client.post("/api/finance/estimate", json={
            "case_id": "case-123",
            "wizard_type": "permit",
            "data": {"permit_type": "Electrical"},
        })
        assert resp.status_code == 200
        assert resp.json()["case_id"] == "case-123"


class TestDeadlineEndpoint:
    def test_deadline_for_case(self, app, client):
        """Create a case via intake store, then check deadline."""
        from municipal.intake.models import Case

        case = Case(
            id="dl-case-1",
            session_id="test-session",
            wizard_id="permit",
            status="submitted",
            data={"permit_type": "Building"},
            created_at=datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc),
        )
        app.state.intake_store.save_case(case)

        resp = client.get("/api/finance/deadline/dl-case-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == "dl-case-1"
        assert data["statutory_days"] == 30
        assert data["business_days_only"] is True

    def test_deadline_case_not_found(self, client):
        resp = client.get("/api/finance/deadline/nonexistent")
        assert resp.status_code == 404


class TestPaymentEndpoints:
    def test_initiate_payment(self, app, client):
        from municipal.intake.models import Case

        case = Case(
            id="pay-case-1",
            session_id="test-session",
            wizard_id="permit",
            status="submitted",
            data={},
        )
        app.state.intake_store.save_case(case)

        resp = client.post("/api/finance/payment/pay-case-1", json={
            "amount": 300.0,
            "requestor": "resident",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == "pay-case-1"
        assert data["amount"] == 300.0
        assert data["status"] == "awaiting_approval"
        assert data["approval_request_id"] is not None

        # Verify payment can be retrieved
        payment_id = data["payment_id"]
        resp2 = client.get(f"/api/finance/payment/{payment_id}")
        assert resp2.status_code == 200
        assert resp2.json()["payment_id"] == payment_id

    def test_get_payment_not_found(self, client):
        resp = client.get("/api/finance/payment/nonexistent")
        assert resp.status_code == 404

    def test_payment_triggers_approval_gate(self, app, client):
        from municipal.intake.models import Case

        case = Case(
            id="pay-case-2",
            session_id="test-session",
            wizard_id="permit",
            status="submitted",
            data={},
        )
        app.state.intake_store.save_case(case)

        resp = client.post("/api/finance/payment/pay-case-2", json={
            "amount": 150.0,
        })
        assert resp.status_code == 200
        data = resp.json()

        # Verify approval request was created in the gate
        approval_id = data["approval_request_id"]
        approval_gate = app.state.approval_gate
        req = approval_gate.get_request(approval_id)
        assert req.gate_type == "payment_refund"
        assert req.resource == "payment:case:pay-case-2"
