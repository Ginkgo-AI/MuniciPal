"""Authentication data models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from municipal.core.types import SessionType


class AuthCredentials(BaseModel):
    username: str
    code: str


class AuthResult(BaseModel):
    success: bool
    token: str | None = None
    tier: SessionType = SessionType.ANONYMOUS
    user_id: str | None = None
    display_name: str = ""
    error: str | None = None


class TokenValidation(BaseModel):
    valid: bool
    user_id: str | None = None
    tier: SessionType = SessionType.ANONYMOUS
    expires_at: datetime | None = None
