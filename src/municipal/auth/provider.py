"""Authentication provider Protocol and mock implementation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import yaml

from municipal.auth.models import AuthCredentials, AuthResult, TokenValidation
from municipal.core.types import SessionType

_DEFAULT_FIXTURES_PATH = Path(__file__).resolve().parents[3] / "config" / "auth_fixtures.yml"


@runtime_checkable
class AuthProvider(Protocol):
    """Protocol for authentication providers."""

    def authenticate(self, credentials: AuthCredentials) -> AuthResult: ...

    def validate_token(self, token: str) -> TokenValidation: ...

    def refresh_token(self, token: str) -> AuthResult: ...

    def revoke_token(self, token: str) -> bool: ...


class MockAuthProvider:
    """Mock auth provider with fixture users from YAML.

    Authenticates with code validation (any non-empty code works in mock).
    Assigns tier based on auth method.
    """

    def __init__(
        self,
        fixtures_path: str | Path | None = None,
        token_expiry_minutes: int = 60,
    ) -> None:
        self._users: dict[str, dict[str, Any]] = {}
        self._tokens: dict[str, dict[str, Any]] = {}
        self._token_expiry = timedelta(minutes=token_expiry_minutes)
        self._load_fixtures(Path(fixtures_path) if fixtures_path else _DEFAULT_FIXTURES_PATH)

    def _load_fixtures(self, path: Path) -> None:
        if not path.exists():
            return
        with open(path) as fh:
            data = yaml.safe_load(fh) or {}
        for user in data.get("users", []):
            self._users[user["username"]] = user

    @property
    def users(self) -> dict[str, dict[str, Any]]:
        return dict(self._users)

    def authenticate(self, credentials: AuthCredentials) -> AuthResult:
        user = self._users.get(credentials.username)
        if user is None:
            return AuthResult(success=False, error="User not found")

        # Mock: accept any non-empty code, or match fixture code if provided
        expected_code = user.get("code", "")
        if not credentials.code or not credentials.code.strip():
            return AuthResult(success=False, error="Verification code is required")

        if expected_code and credentials.code != expected_code:
            return AuthResult(success=False, error="Invalid verification code")

        tier = SessionType(user.get("tier", "authenticated"))
        token = str(uuid.uuid4())
        self._tokens[token] = {
            "user_id": user["username"],
            "tier": tier,
            "display_name": user.get("display_name", user["username"]),
            "expires_at": datetime.now(timezone.utc) + self._token_expiry,
        }

        return AuthResult(
            success=True,
            token=token,
            tier=tier,
            user_id=user["username"],
            display_name=user.get("display_name", user["username"]),
        )

    def validate_token(self, token: str) -> TokenValidation:
        info = self._tokens.get(token)
        if info is None:
            return TokenValidation(valid=False)

        if datetime.now(timezone.utc) > info["expires_at"]:
            del self._tokens[token]
            return TokenValidation(valid=False)

        return TokenValidation(
            valid=True,
            user_id=info["user_id"],
            tier=info["tier"],
            expires_at=info["expires_at"],
        )

    def refresh_token(self, token: str) -> AuthResult:
        info = self._tokens.get(token)
        if info is None:
            return AuthResult(success=False, error="Token not found or expired")

        # Revoke old, issue new
        del self._tokens[token]
        new_token = str(uuid.uuid4())
        self._tokens[new_token] = {
            **info,
            "expires_at": datetime.now(timezone.utc) + self._token_expiry,
        }
        return AuthResult(
            success=True,
            token=new_token,
            tier=info["tier"],
            user_id=info["user_id"],
            display_name=info["display_name"],
        )

    def revoke_token(self, token: str) -> bool:
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False
