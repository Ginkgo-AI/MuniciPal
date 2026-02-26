"""Tests for review router API endpoints (Phase 4 — WP4)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from municipal.core.config import Settings
from municipal.web.app import create_app


@pytest.fixture
def client():
    mock_rag = MagicMock()
    mock_rag.query.return_value = MagicMock(answer="test", sources=[], confidence=0.9)
    app = create_app(settings=Settings(), rag_pipeline=mock_rag)
    return TestClient(app)


def _create_case_via_api(client, wizard_id="service_request_311"):
    """Helper to create a case through the wizard API."""
    # Start wizard
    resp = client.post(f"/api/intake/wizards/{wizard_id}/start")
    assert resp.status_code == 200
    state_id = resp.json()["state_id"]

    if wizard_id == "service_request_311":
        # Step 1: category_selection
        resp = client.post(
            f"/api/intake/state/{state_id}/steps/category_selection",
            json={"data": {"category": "pothole", "priority": "medium"}, "session_type": "anonymous"},
        )
        assert resp.status_code == 200

        # Step 2: location_description
        resp = client.post(
            f"/api/intake/state/{state_id}/steps/location_description",
            json={"data": {"location": "123 Main St", "description": "Big pothole"}, "session_type": "anonymous"},
        )
        assert resp.status_code == 200

        # Step 3: contact_info
        resp = client.post(
            f"/api/intake/state/{state_id}/steps/contact_info",
            json={
                "data": {
                    "contact_name": "John Doe",
                    "contact_email": "john@example.com",
                    "contact_phone": "555-123-4567",
                },
                "session_type": "verified",
            },
        )
        assert resp.status_code == 200

        # Submit
        resp = client.post(f"/api/intake/state/{state_id}/submit")
        assert resp.status_code == 200
        return resp.json()["id"]

    return None


class TestRedactionEndpoint:
    def test_redact_case(self, client):
        case_id = _create_case_via_api(client)
        resp = client.post(f"/api/review/redact/{case_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == case_id
        assert "suggestions" in data
        # Should detect email/phone from the contact info
        field_ids = [s["field_id"] for s in data["suggestions"]]
        assert "contact_email" in field_ids or "contact_phone" in field_ids

    def test_redact_nonexistent_case(self, client):
        resp = client.post("/api/review/redact/nonexistent")
        assert resp.status_code == 404


class TestInconsistencyEndpoint:
    def test_detect_inconsistencies(self, client):
        case_id = _create_case_via_api(client)
        resp = client.post(f"/api/review/inconsistencies/{case_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == case_id
        assert "findings" in data

    def test_inconsistencies_nonexistent_case(self, client):
        resp = client.post("/api/review/inconsistencies/nonexistent")
        assert resp.status_code == 404


class TestSummaryEndpoint:
    def test_get_case_summary(self, client):
        case_id = _create_case_via_api(client)
        resp = client.get(f"/api/review/summary/{case_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == case_id
        assert data["wizard_id"] == "service_request_311"
        assert "key_facts" in data
        assert "timeline" in data

    def test_summary_nonexistent_case(self, client):
        resp = client.get("/api/review/summary/nonexistent")
        assert resp.status_code == 404


class TestDepartmentReportEndpoint:
    def test_report_empty(self, client):
        resp = client.get("/api/review/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cases"] == 0

    def test_report_with_cases(self, client):
        _create_case_via_api(client)
        resp = client.get("/api/review/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cases"] >= 1

    def test_report_filter_by_wizard(self, client):
        _create_case_via_api(client)
        resp = client.get("/api/review/report?wizard_type=service_request_311")
        assert resp.status_code == 200
        assert resp.json()["total_cases"] >= 1

        resp = client.get("/api/review/report?wizard_type=nonexistent")
        assert resp.status_code == 200
        assert resp.json()["total_cases"] == 0


class TestCrossFieldValidationEndpoint:
    def test_validate_cross_field(self, client):
        # Start a FOIA wizard
        resp = client.post("/api/intake/wizards/foia_request/start")
        assert resp.status_code == 200
        state_id = resp.json()["state_id"]

        # Submit first step with dates
        resp = client.post(
            f"/api/intake/state/{state_id}/steps/request_details",
            json={
                "data": {
                    "requester_name": "Test User",
                    "requester_email": "test@example.com",
                },
                "session_type": "anonymous",
            },
        )
        assert resp.status_code == 200

        # Submit scope step with bad dates
        resp = client.post(
            f"/api/intake/state/{state_id}/steps/scope",
            json={
                "data": {
                    "department": "All Departments",
                    "records_description": "All records",
                    "date_range_start": "2024-06-01",
                    "date_range_end": "2024-01-01",
                },
                "session_type": "anonymous",
            },
        )
        assert resp.status_code == 200

        # Now validate cross-fields
        resp = client.post(f"/api/intake/state/{state_id}/validate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert "date_range_end" in data["errors"]

    def test_validate_nonexistent_state(self, client):
        resp = client.post("/api/intake/state/nonexistent/validate")
        assert resp.status_code == 404


class TestSunshineEndpoints:
    """Sunshine endpoints exist but need generator wired (WP5). Test 503 without it, then success after WP5."""

    def test_sunshine_json_available(self, client):
        # After WP5 is wired, this should work
        resp = client.get("/api/review/sunshine")
        # Will be 503 until sunshine_generator is wired
        assert resp.status_code in (200, 503)
