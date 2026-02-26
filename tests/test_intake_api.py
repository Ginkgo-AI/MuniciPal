"""Tests for intake API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from municipal.core.config import Settings
from municipal.web.app import create_app


@pytest.fixture
def client():
    settings = Settings()
    app = create_app(settings=settings)
    return TestClient(app)


class TestIntakeAPI:
    def test_list_wizards(self, client):
        resp = client.get("/api/intake/wizards")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        ids = [w["id"] for w in data]
        assert "permit_application" in ids
        assert "foia_request" in ids

    def test_start_wizard(self, client):
        # Create a session first
        client.post("/api/sessions", json={"session_type": "anonymous"})
        resp = client.post("/api/intake/wizards/permit_application/start")
        assert resp.status_code == 200
        data = resp.json()
        assert data["wizard_id"] == "permit_application"
        assert "state_id" in data

    def test_start_unknown_wizard(self, client):
        client.post("/api/sessions", json={"session_type": "anonymous"})
        resp = client.post("/api/intake/wizards/nonexistent/start")
        assert resp.status_code == 404

    def test_get_wizard_state(self, client):
        client.post("/api/sessions", json={"session_type": "anonymous"})
        start = client.post("/api/intake/wizards/foia_request/start").json()
        resp = client.get(f"/api/intake/state/{start['state_id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["wizard_id"] == "foia_request"
        assert len(data["steps"]) == 3

    def test_get_wizard_state_not_found(self, client):
        resp = client.get("/api/intake/state/nonexistent")
        assert resp.status_code == 404

    def test_submit_step_and_advance(self, client):
        client.post("/api/sessions", json={"session_type": "anonymous"})
        start = client.post("/api/intake/wizards/foia_request/start").json()
        state_id = start["state_id"]

        resp = client.post(
            f"/api/intake/state/{state_id}/steps/request_details",
            json={
                "data": {
                    "requester_name": "Jane Doe",
                    "requester_email": "jane@example.com",
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["steps"][0]["status"] == "completed"
        assert data["current_step_index"] == 1

    def test_submit_step_validation_error(self, client):
        client.post("/api/sessions", json={"session_type": "anonymous"})
        start = client.post("/api/intake/wizards/foia_request/start").json()
        state_id = start["state_id"]

        resp = client.post(
            f"/api/intake/state/{state_id}/steps/request_details",
            json={
                "data": {
                    "requester_name": "",
                    "requester_email": "not-an-email",
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["steps"][0]["status"] == "in_progress"
        assert "requester_name" in data["steps"][0]["errors"]

    def test_go_back(self, client):
        client.post("/api/sessions", json={"session_type": "anonymous"})
        start = client.post("/api/intake/wizards/foia_request/start").json()
        state_id = start["state_id"]

        # Advance to step 2
        client.post(
            f"/api/intake/state/{state_id}/steps/request_details",
            json={"data": {"requester_name": "Jane", "requester_email": "j@e.com"}},
        )

        # Go back
        resp = client.post(f"/api/intake/state/{state_id}/back")
        assert resp.status_code == 200
        assert resp.json()["current_step_index"] == 0

    def test_validate_field(self, client):
        resp = client.post(
            "/api/intake/validate",
            json={
                "wizard_id": "foia_request",
                "step_id": "request_details",
                "field_id": "requester_email",
                "value": "bad-email",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_list_cases_empty(self, client):
        resp = client.get("/api/intake/cases")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGISAPI:
    def test_parcel_lookup_by_id(self, client):
        resp = client.get("/api/gis/parcel/12-34-567-001")
        assert resp.status_code == 200
        assert resp.json()["parcel_id"] == "12-34-567-001"

    def test_parcel_lookup_by_id_not_found(self, client):
        resp = client.get("/api/gis/parcel/99-99-999-999")
        assert resp.status_code == 404

    def test_parcel_lookup_by_address(self, client):
        resp = client.get(
            "/api/gis/parcel",
            params={"address": "123 Main St, Springfield, IL 62701"},
        )
        assert resp.status_code == 200
        assert resp.json()["parcel_id"] == "12-34-567-001"

    def test_parcel_lookup_by_address_missing(self, client):
        resp = client.get("/api/gis/parcel", params={"address": ""})
        assert resp.status_code == 400


class TestI18nAPI:
    def test_list_locales(self, client):
        resp = client.get("/api/i18n/locales")
        assert resp.status_code == 200
        data = resp.json()
        assert "en" in data["locales"]
        assert "es" in data["locales"]

    def test_get_bundle(self, client):
        resp = client.get("/api/i18n/bundle/en")
        assert resp.status_code == 200
        data = resp.json()
        assert "system" in data

    def test_get_bundle_not_found(self, client):
        resp = client.get("/api/i18n/bundle/zz")
        assert resp.status_code == 404


class TestUpgradeAPI:
    def test_upgrade_request_and_verify(self, client):
        # Create a session
        session_resp = client.post("/api/sessions", json={"session_type": "anonymous"})
        session_id = session_resp.json()["session_id"]

        # Request upgrade
        req_resp = client.post(f"/api/sessions/{session_id}/upgrade/request")
        assert req_resp.status_code == 200
        req_data = req_resp.json()
        assert req_data["target_tier"] == "verified"

        # Verify
        verify_resp = client.post(
            f"/api/sessions/{session_id}/upgrade/verify",
            json={
                "verification_id": req_data["verification_id"],
                "code": "123456",
            },
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["new_tier"] == "verified"

    def test_upgrade_unknown_session(self, client):
        resp = client.post("/api/sessions/nonexistent/upgrade/request")
        assert resp.status_code == 404
