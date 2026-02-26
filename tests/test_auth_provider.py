"""Tests for auth provider and middleware."""

from __future__ import annotations

import pytest

from municipal.auth.models import AuthCredentials
from municipal.auth.provider import MockAuthProvider
from municipal.core.types import SessionType


class TestMockAuthProvider:
    def setup_method(self) -> None:
        self.provider = MockAuthProvider()

    def test_fixtures_loaded(self) -> None:
        assert "jane.smith" in self.provider.users
        assert "bob.johnson" in self.provider.users

    def test_authenticate_success(self) -> None:
        result = self.provider.authenticate(
            AuthCredentials(username="jane.smith", code="123456")
        )
        assert result.success
        assert result.token is not None
        assert result.tier == SessionType.AUTHENTICATED
        assert result.user_id == "jane.smith"
        assert result.display_name == "Jane Smith"

    def test_authenticate_wrong_code(self) -> None:
        result = self.provider.authenticate(
            AuthCredentials(username="jane.smith", code="wrong")
        )
        assert not result.success
        assert "Invalid" in result.error

    def test_authenticate_empty_code(self) -> None:
        result = self.provider.authenticate(
            AuthCredentials(username="jane.smith", code="")
        )
        assert not result.success

    def test_authenticate_unknown_user(self) -> None:
        result = self.provider.authenticate(
            AuthCredentials(username="nobody", code="123")
        )
        assert not result.success
        assert "not found" in result.error

    def test_validate_token(self) -> None:
        auth = self.provider.authenticate(
            AuthCredentials(username="jane.smith", code="123456")
        )
        validation = self.provider.validate_token(auth.token)
        assert validation.valid
        assert validation.user_id == "jane.smith"
        assert validation.tier == SessionType.AUTHENTICATED

    def test_validate_invalid_token(self) -> None:
        validation = self.provider.validate_token("bad-token")
        assert not validation.valid

    def test_refresh_token(self) -> None:
        auth = self.provider.authenticate(
            AuthCredentials(username="bob.johnson", code="654321")
        )
        old_token = auth.token
        refreshed = self.provider.refresh_token(old_token)
        assert refreshed.success
        assert refreshed.token != old_token

        # Old token should be invalid
        assert not self.provider.validate_token(old_token).valid
        # New token should be valid
        assert self.provider.validate_token(refreshed.token).valid

    def test_refresh_invalid_token(self) -> None:
        result = self.provider.refresh_token("bad-token")
        assert not result.success

    def test_revoke_token(self) -> None:
        auth = self.provider.authenticate(
            AuthCredentials(username="jane.smith", code="123456")
        )
        assert self.provider.revoke_token(auth.token)
        assert not self.provider.validate_token(auth.token).valid

    def test_revoke_nonexistent_token(self) -> None:
        assert not self.provider.revoke_token("nope")

    def test_verified_tier_user(self) -> None:
        result = self.provider.authenticate(
            AuthCredentials(username="bob.johnson", code="654321")
        )
        assert result.success
        assert result.tier == SessionType.VERIFIED
