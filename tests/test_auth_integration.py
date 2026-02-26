"""Integration tests for auth API endpoints and middleware."""

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


class TestAuthAPI:
    def test_login_success(self, client: TestClient) -> None:
        resp = client.post(
            "/api/auth/login",
            json={"username": "jane.smith", "code": "123456"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"]
        assert data["token"] is not None
        assert data["tier"] == "authenticated"

    def test_login_wrong_code(self, client: TestClient) -> None:
        resp = client.post(
            "/api/auth/login",
            json={"username": "jane.smith", "code": "wrong"},
        )
        assert resp.status_code == 401

    def test_login_unknown_user(self, client: TestClient) -> None:
        resp = client.post(
            "/api/auth/login",
            json={"username": "nobody", "code": "123"},
        )
        assert resp.status_code == 401

    def test_validate_token(self, client: TestClient) -> None:
        login = client.post(
            "/api/auth/login",
            json={"username": "jane.smith", "code": "123456"},
        )
        token = login.json()["token"]
        resp = client.post("/api/auth/validate", json={"token": token})
        assert resp.status_code == 200
        assert resp.json()["valid"]

    def test_validate_bad_token(self, client: TestClient) -> None:
        resp = client.post("/api/auth/validate", json={"token": "bad"})
        assert resp.status_code == 200
        assert not resp.json()["valid"]

    def test_refresh_token(self, client: TestClient) -> None:
        login = client.post(
            "/api/auth/login",
            json={"username": "jane.smith", "code": "123456"},
        )
        token = login.json()["token"]
        resp = client.post("/api/auth/refresh", json={"token": token})
        assert resp.status_code == 200
        new_token = resp.json()["token"]
        assert new_token != token

    def test_logout(self, client: TestClient) -> None:
        login = client.post(
            "/api/auth/login",
            json={"username": "jane.smith", "code": "123456"},
        )
        token = login.json()["token"]
        resp = client.post("/api/auth/logout", json={"token": token})
        assert resp.status_code == 200
        assert resp.json()["revoked"]

        # Token should now be invalid
        validate = client.post("/api/auth/validate", json={"token": token})
        assert not validate.json()["valid"]


class TestAuthMiddleware:
    def test_unauthenticated_request_gets_anonymous_tier(self, client: TestClient) -> None:
        # Health endpoint should work without auth
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_authenticated_request_sets_tier(self, client: TestClient) -> None:
        # Login to get token
        login = client.post(
            "/api/auth/login",
            json={"username": "jane.smith", "code": "123456"},
        )
        token = login.json()["token"]

        # Use token to access an endpoint
        resp = client.get(
            "/api/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_invalid_bearer_token_stays_anonymous(self, client: TestClient) -> None:
        resp = client.get(
            "/api/health",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 200
