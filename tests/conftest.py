"""Shared test fixtures and helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from municipal.core.types import SessionType


STAFF_TOKEN = "test-staff-token-for-tests"


def install_staff_token(app) -> str:
    """Register a staff auth token on the app's auth provider.

    Returns the token string for use in Authorization headers.
    """
    provider = app.state.auth_provider
    provider._tokens[STAFF_TOKEN] = {
        "user_id": "test-staff",
        "tier": SessionType.AUTHENTICATED,
        "display_name": "Test Staff",
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return STAFF_TOKEN
