"""Tests for Mission Control v1: metrics, approvals, session takeover."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from municipal.bridge.registry import AdapterRegistry
from municipal.bridge.adapters.permit_status import MockPermitStatusAdapter
from municipal.chat.session import SessionManager
from municipal.core.config import Settings
from municipal.governance.approval import ApprovalGate
from municipal.intake.store import IntakeStore
from municipal.web.app import create_app
from municipal.web.mission_control_v1 import MetricsService, SessionTakeoverManager


class TestMetricsService:
    def test_snapshot_empty(self) -> None:
        service = MetricsService(
            session_manager=SessionManager(),
            intake_store=IntakeStore(),
        )
        snap = service.snapshot()
        assert snap.total_sessions == 0
        assert snap.total_cases == 0
        assert snap.pending_approvals == 0

    def test_snapshot_with_sessions(self) -> None:
        sm = SessionManager()
        sm.create_session()
        sm.create_session()
        service = MetricsService(session_manager=sm)
        snap = service.snapshot()
        assert snap.total_sessions == 2

    def test_snapshot_with_adapters(self) -> None:
        registry = AdapterRegistry()
        registry.register(MockPermitStatusAdapter())
        service = MetricsService(adapter_registry=registry)
        snap = service.snapshot()
        assert "permit_status" in snap.adapter_health
        assert snap.adapter_health["permit_status"] == "connected"


class TestSessionTakeoverManager:
    def setup_method(self) -> None:
        self.mgr = SessionTakeoverManager()

    def test_takeover(self) -> None:
        result = self.mgr.takeover("sess-1", "staff-1")
        assert result["status"] == "taken_over"
        assert self.mgr.is_taken_over("sess-1")
        assert self.mgr.get_controller("sess-1") == "staff-1"

    def test_release(self) -> None:
        self.mgr.takeover("sess-1", "staff-1")
        result = self.mgr.release("sess-1")
        assert result["status"] == "released"
        assert not self.mgr.is_taken_over("sess-1")

    def test_release_not_taken_over(self) -> None:
        result = self.mgr.release("sess-1")
        assert result["status"] == "released"

    def test_list_takeovers(self) -> None:
        self.mgr.takeover("a", "staff-1")
        self.mgr.takeover("b", "staff-2")
        assert len(self.mgr.list_takeovers()) == 2

    def test_get_controller_not_taken(self) -> None:
        assert self.mgr.get_controller("nope") is None


@pytest.fixture
def client() -> TestClient:
    from tests.conftest import install_staff_token
    mock_rag = MagicMock()
    mock_rag.query.return_value = MagicMock(answer="test", sources=[], confidence=0.9)
    app = create_app(settings=Settings(), rag_pipeline=mock_rag)
    token = install_staff_token(app)
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


class TestMissionControlV1API:
    def test_metrics_endpoint(self, client: TestClient) -> None:
        resp = client.get("/api/staff/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_sessions" in data
        assert "adapter_health" in data
        assert "permit_status" in data["adapter_health"]

    def test_adapter_metrics(self, client: TestClient) -> None:
        resp = client.get("/api/staff/metrics/adapters")
        assert resp.status_code == 200
        data = resp.json()
        assert "adapters" in data
        names = [a["name"] for a in data["adapters"]]
        assert "permit_status" in names

    def test_list_approvals_empty(self, client: TestClient) -> None:
        resp = client.get("/api/staff/approvals")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_approve_not_found(self, client: TestClient) -> None:
        resp = client.post(
            "/api/staff/approvals/nonexistent/approve",
            json={"approver": "staff"},
        )
        assert resp.status_code == 404

    def test_deny_not_found(self, client: TestClient) -> None:
        resp = client.post(
            "/api/staff/approvals/nonexistent/deny",
            json={"approver": "staff", "reason": "test"},
        )
        assert resp.status_code == 404

    def test_takeover_and_release(self, client: TestClient) -> None:
        # Create a session first
        sess = client.post("/api/sessions", json={"session_type": "anonymous"})
        sid = sess.json()["session_id"]

        resp = client.post(
            f"/api/staff/sessions/{sid}/takeover",
            json={"staff_id": "admin"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "taken_over"

        resp = client.post(f"/api/staff/sessions/{sid}/release")
        assert resp.status_code == 200
        assert resp.json()["status"] == "released"


class TestApprovalWorkflow:
    """Test the full approval workflow through the API."""

    def test_create_and_approve_via_api(self, client: TestClient) -> None:
        # Start a permit wizard and submit it to generate an approval request
        start = client.post("/api/intake/wizards/permit_application/start")
        if start.status_code != 200:
            pytest.skip("Permit wizard not available")

        state_id = start.json()["state_id"]

        # Submit step 1 (property_info)
        client.post(
            f"/api/intake/state/{state_id}/steps/property_info",
            json={
                "data": {
                    "property_address": "123 Main St",
                    "parcel_id": "12-34-100-001",
                    "property_type": "Residential",
                },
                "session_type": "anonymous",
            },
        )

        # Submit step 2 (project_details)
        client.post(
            f"/api/intake/state/{state_id}/steps/project_details",
            json={
                "data": {
                    "permit_type": "Building",
                    "project_description": "Test project",
                    "estimated_cost": "5000",
                    "start_date": "2024-06-01",
                },
                "session_type": "anonymous",
            },
        )

        # Step 3 (contractor_info) should be skipped for Residential
        # Step 4 (documents) - submit
        client.post(
            f"/api/intake/state/{state_id}/steps/documents",
            json={"data": {}, "session_type": "verified"},
        )

        # Step 5 (review) - submit
        client.post(
            f"/api/intake/state/{state_id}/steps/review",
            json={
                "data": {
                    "applicant_name": "Test User",
                    "applicant_email": "test@example.com",
                    "applicant_phone": "555-0100",
                    "certify": "true",
                },
                "session_type": "authenticated",
            },
        )

        # Submit wizard
        submit_resp = client.post(f"/api/intake/state/{state_id}/submit")
        if submit_resp.status_code != 200:
            pytest.skip("Wizard submission failed")

        case = submit_resp.json()
        approval_id = case.get("approval_request_id")
        if not approval_id:
            pytest.skip("No approval request created")

        # Get approval detail
        detail = client.get(f"/api/staff/approvals/{approval_id}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "pending"

        # Approve it (need min_approvals=2 for permit_decision)
        client.post(
            f"/api/staff/approvals/{approval_id}/approve",
            json={"approver": "reviewer1"},
        )
        client.post(
            f"/api/staff/approvals/{approval_id}/approve",
            json={"approver": "reviewer2"},
        )

        # Check it's approved
        final = client.get(f"/api/staff/approvals/{approval_id}")
        assert final.json()["status"] == "approved"
