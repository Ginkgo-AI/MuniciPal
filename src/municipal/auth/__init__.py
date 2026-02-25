"""Authentication strategy module for Munici-Pal.

Defines the three session tiers (Anonymous, Verified, Authenticated) and
their capabilities as code-based strategy/config.
"""

from municipal.auth.strategy import (
    AnonymousSession,
    AuthenticatedSession,
    SessionTier,
    VerifiedSession,
)

__all__ = [
    "AnonymousSession",
    "AuthenticatedSession",
    "SessionTier",
    "VerifiedSession",
]
