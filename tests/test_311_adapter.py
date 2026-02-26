"""Tests for 311 service request adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from municipal.bridge.adapters.service311 import Mock311Adapter, TicketStatus
from municipal.bridge.models import NormalizedRequest
from municipal.core.config import Settings
from municipal.web.app import create_app


class TestMock311Adapter:
    def setup_method(self) -> None:
        self.adapter = Mock311Adapter()

    def test_name(self) -> None:
        assert self.adapter.name == "service_311"

    def test_schema_operations(self) -> None:
        ops = self.adapter.schema.operations
        assert "list_tickets" in ops
        assert "get_ticket" in ops
        assert "create_ticket" in ops
        assert "add_note" in ops

    def test_list_tickets(self) -> None:
        req = NormalizedRequest(operation="list_tickets", params={})
        resp = self.adapter.query(req)
        assert resp.success
        assert len(resp.data) == 5

    def test_list_tickets_filter_status(self) -> None:
        req = NormalizedRequest(operation="list_tickets", params={"status": "open"})
        resp = self.adapter.query(req)
        assert resp.success
        assert all(t["status"] == "open" for t in resp.data)

    def test_list_tickets_filter_category(self) -> None:
        req = NormalizedRequest(operation="list_tickets", params={"category": "pothole"})
        resp = self.adapter.query(req)
        assert resp.success
        assert len(resp.data) == 1

    def test_get_ticket_found(self) -> None:
        req = NormalizedRequest(operation="get_ticket", params={"ticket_id": "SR-2024-001"})
        resp = self.adapter.query(req)
        assert resp.success
        assert resp.data["ticket_id"] == "SR-2024-001"

    def test_get_ticket_not_found(self) -> None:
        req = NormalizedRequest(operation="get_ticket", params={"ticket_id": "NOPE"})
        resp = self.adapter.query(req)
        assert resp.success
        assert resp.data is None

    def test_create_ticket(self) -> None:
        req = NormalizedRequest(
            operation="create_ticket",
            params={
                "category": "pothole",
                "description": "New pothole on 2nd St",
                "location": "200 2nd St",
                "contact_name": "Test User",
            },
        )
        resp = self.adapter.query(req)
        assert resp.success
        assert resp.data["category"] == "pothole"
        assert resp.data["description"] == "New pothole on 2nd St"
        assert resp.data["ticket_id"].startswith("SR-")

    def test_add_note(self) -> None:
        req = NormalizedRequest(
            operation="add_note",
            params={
                "ticket_id": "SR-2024-001",
                "author": "Staff",
                "content": "Scheduled for repair",
            },
        )
        resp = self.adapter.query(req)
        assert resp.success
        assert len(resp.data["notes"]) == 1
        assert resp.data["notes"][0]["content"] == "Scheduled for repair"

    def test_add_note_ticket_not_found(self) -> None:
        req = NormalizedRequest(
            operation="add_note",
            params={"ticket_id": "NOPE", "author": "Staff", "content": "test"},
        )
        resp = self.adapter.query(req)
        assert not resp.success


@pytest.fixture
def client() -> TestClient:
    mock_rag = MagicMock()
    mock_rag.query.return_value = MagicMock(answer="test", sources=[], confidence=0.9)
    app = create_app(settings=Settings(), rag_pipeline=mock_rag)
    return TestClient(app)


class Test311API:
    def test_list_tickets(self, client: TestClient) -> None:
        resp = client.get("/api/bridge/311/tickets")
        assert resp.status_code == 200
        assert len(resp.json()) >= 5

    def test_list_tickets_filter(self, client: TestClient) -> None:
        resp = client.get("/api/bridge/311/tickets?status=open")
        assert resp.status_code == 200
        assert all(t["status"] == "open" for t in resp.json())

    def test_get_ticket(self, client: TestClient) -> None:
        resp = client.get("/api/bridge/311/tickets/SR-2024-001")
        assert resp.status_code == 200
        assert resp.json()["ticket_id"] == "SR-2024-001"

    def test_get_ticket_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/bridge/311/tickets/NOPE")
        assert resp.status_code == 404

    def test_create_ticket(self, client: TestClient) -> None:
        resp = client.post(
            "/api/bridge/311/tickets",
            json={
                "category": "trash",
                "description": "Overflowing dumpster",
                "location": "100 Main St",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "trash"

    def test_add_note(self, client: TestClient) -> None:
        resp = client.post(
            "/api/bridge/311/tickets/SR-2024-001/notes",
            json={"author": "Staff", "content": "Looking into it"},
        )
        assert resp.status_code == 200
