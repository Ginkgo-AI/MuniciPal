"""API tests for bridge router endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from municipal.core.config import Settings
from municipal.web.app import create_app


@pytest.fixture
def client() -> TestClient:
    mock_rag = MagicMock()
    mock_rag.query.return_value = MagicMock(
        answer="test", sources=[], confidence=0.9
    )
    app = create_app(
        settings=Settings(),
        rag_pipeline=mock_rag,
    )
    return TestClient(app)


class TestBridgeAdaptersAPI:
    def test_list_adapters(self, client: TestClient) -> None:
        resp = client.get("/api/bridge/adapters")
        assert resp.status_code == 200
        data = resp.json()
        names = [a["name"] for a in data]
        assert "permit_status" in names

    def test_adapter_health(self, client: TestClient) -> None:
        resp = client.get("/api/bridge/adapters/permit_status/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "connected"

    def test_adapter_health_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/bridge/adapters/nonexistent/health")
        assert resp.status_code == 404

    def test_adapter_schema(self, client: TestClient) -> None:
        resp = client.get("/api/bridge/adapters/permit_status/schema")
        assert resp.status_code == 200
        data = resp.json()
        assert "lookup_by_id" in data["operations"]

    def test_adapter_query(self, client: TestClient) -> None:
        resp = client.post(
            "/api/bridge/adapters/permit_status/query",
            json={"operation": "lookup_by_id", "params": {"permit_id": "BP-2024-001"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"]
        assert data["data"]["permit_id"] == "BP-2024-001"


class TestPermitEndpoints:
    def test_get_permit(self, client: TestClient) -> None:
        resp = client.get("/api/bridge/permits/BP-2024-001")
        assert resp.status_code == 200
        assert resp.json()["permit_id"] == "BP-2024-001"

    def test_get_permit_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/bridge/permits/NONEXISTENT")
        assert resp.status_code == 404

    def test_search_by_parcel(self, client: TestClient) -> None:
        resp = client.get("/api/bridge/permits?parcel_id=12-34-100-001")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_search_by_applicant(self, client: TestClient) -> None:
        resp = client.get("/api/bridge/permits?applicant=jane")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_search_no_params(self, client: TestClient) -> None:
        resp = client.get("/api/bridge/permits")
        assert resp.status_code == 400
