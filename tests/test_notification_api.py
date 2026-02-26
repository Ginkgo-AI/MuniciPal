"""API tests for notification and graph endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from municipal.core.config import Settings
from municipal.web.app import create_app


@pytest.fixture
def client() -> TestClient:
    mock_rag = MagicMock()
    mock_rag.query.return_value = MagicMock(answer="test", sources=[], confidence=0.9)
    app = create_app(settings=Settings(), rag_pipeline=mock_rag)
    return TestClient(app)


class TestNotificationAPI:
    def test_send_notification_direct(self, client: TestClient) -> None:
        resp = client.post(
            "/api/notifications/send",
            json={
                "session_id": "s1",
                "recipient": "user@test.com",
                "subject": "Test",
                "body": "Hello",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "delivered"
        assert data["recipient"] == "user@test.com"

    def test_send_notification_with_template(self, client: TestClient) -> None:
        resp = client.post(
            "/api/notifications/send",
            json={
                "session_id": "s1",
                "recipient": "user@test.com",
                "subject": "",
                "body": "",
                "template_id": "case_submitted",
                "context": {"case_id": "C-100", "wizard_title": "Permit"},
            },
        )
        assert resp.status_code == 200
        assert "C-100" in resp.json()["subject"]

    def test_get_notification(self, client: TestClient) -> None:
        # First send one
        send_resp = client.post(
            "/api/notifications/send",
            json={
                "session_id": "s1",
                "recipient": "user@test.com",
                "subject": "Test",
                "body": "Body",
            },
        )
        nid = send_resp.json()["id"]
        resp = client.get(f"/api/notifications/{nid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "delivered"

    def test_get_notification_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/notifications/nonexistent")
        assert resp.status_code == 404

    def test_list_notifications(self, client: TestClient) -> None:
        client.post(
            "/api/notifications/send",
            json={"session_id": "s1", "recipient": "a@b.com", "subject": "A", "body": "X"},
        )
        resp = client.get("/api/notifications?session_id=s1")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestGraphAPI:
    def test_query_empty_graph(self, client: TestClient) -> None:
        resp = client.get("/api/graph/query")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_node_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/graph/nodes/nonexistent")
        assert resp.status_code == 404

    def test_get_neighbors_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/graph/nodes/nonexistent/neighbors")
        assert resp.status_code == 404
