"""Authentication middleware and dependencies."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from municipal.auth.provider import AuthProvider
from municipal.core.types import SessionType


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts Bearer token and enriches request.state.auth_tier."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Default to anonymous
        request.state.auth_tier = SessionType.ANONYMOUS
        request.state.auth_user_id = None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            provider = getattr(request.app.state, "auth_provider", None)
            if provider is not None:
                validation = provider.validate_token(token)
                if validation.valid:
                    request.state.auth_tier = validation.tier
                    request.state.auth_user_id = validation.user_id

        return await call_next(request)


def require_tier(minimum: SessionType):
    """FastAPI dependency that requires a minimum auth tier."""
    _tier_order = {
        SessionType.ANONYMOUS: 0,
        SessionType.VERIFIED: 1,
        SessionType.AUTHENTICATED: 2,
    }

    def dependency(request: Request) -> SessionType:
        current = getattr(request.state, "auth_tier", SessionType.ANONYMOUS)
        if _tier_order.get(current, 0) < _tier_order.get(minimum, 0):
            raise HTTPException(
                status_code=403,
                detail=f"Requires {minimum} tier, current is {current}",
            )
        return current

    return Depends(dependency)
