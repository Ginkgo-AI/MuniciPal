"""Session upgrade service for identity verification."""

from __future__ import annotations

import uuid
from typing import Any

from municipal.chat.session import SessionManager
from municipal.core.types import AuditEvent, DataClassification, SessionType
from municipal.governance.audit import AuditLogger

# Tier ordering for upgrade validation
_TIER_ORDER: dict[SessionType, int] = {
    SessionType.ANONYMOUS: 0,
    SessionType.VERIFIED: 1,
    SessionType.AUTHENTICATED: 2,
}

_UPGRADE_PATHS: dict[SessionType, SessionType] = {
    SessionType.ANONYMOUS: SessionType.VERIFIED,
    SessionType.VERIFIED: SessionType.AUTHENTICATED,
}


class SessionUpgradeService:
    """Handles session tier upgrades with verification.

    Phase 2 implementation accepts any verification code (simulated).
    Phase 3 can optionally delegate to an AuthProvider when injected.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        audit_logger: AuditLogger | None = None,
        auth_provider: Any | None = None,
    ) -> None:
        self._sessions = session_manager
        self._audit = audit_logger
        self._auth_provider = auth_provider
        self._pending_upgrades: dict[str, dict[str, Any]] = {}

    def request_upgrade(self, session_id: str) -> dict[str, Any]:
        """Request a session tier upgrade.

        Generates a verification code and stores it for later verification.

        Returns:
            Dict with upgrade details including the verification_id.

        Raises:
            KeyError: If session not found.
            ValueError: If already at max tier.
        """
        session = self._sessions.get_session(session_id)
        if session is None:
            raise KeyError(f"Session {session_id!r} not found")

        current_tier = session.session_type
        target_tier = _UPGRADE_PATHS.get(current_tier)
        if target_tier is None:
            raise ValueError(f"Session is already at maximum tier ({current_tier}).")

        verification_id = str(uuid.uuid4())
        self._pending_upgrades[verification_id] = {
            "session_id": session_id,
            "current_tier": current_tier,
            "target_tier": target_tier,
        }

        return {
            "verification_id": verification_id,
            "current_tier": current_tier.value,
            "target_tier": target_tier.value,
            "method": "email_or_phone_verification"
            if current_tier == SessionType.ANONYMOUS
            else "government_id_verification",
            "message": f"Verification code sent. Use any code to verify (Phase 2 simulation).",
        }

    def verify_upgrade(self, session_id: str, verification_id: str, code: str) -> dict[str, Any]:
        """Verify a code and complete the session upgrade.

        Phase 2: accepts any non-empty code.

        Returns:
            Dict with upgrade result.

        Raises:
            KeyError: If session or verification not found.
            ValueError: If code is empty or verification doesn't match session.
        """
        if not code or not code.strip():
            raise ValueError("Verification code is required.")

        upgrade = self._pending_upgrades.get(verification_id)
        if upgrade is None:
            raise KeyError(f"Verification {verification_id!r} not found or expired.")

        if upgrade["session_id"] != session_id:
            raise ValueError("Verification does not match this session.")

        session = self._sessions.get_session(session_id)
        if session is None:
            raise KeyError(f"Session {session_id!r} not found")

        target_tier = upgrade["target_tier"]

        # Mutate session type
        session.session_type = target_tier

        # Clean up
        del self._pending_upgrades[verification_id]

        # Audit log
        if self._audit:
            event = AuditEvent(
                session_id=session_id,
                actor=session_id,
                action="session_upgraded",
                resource=f"session:{session_id}",
                classification=DataClassification.INTERNAL,
                details={
                    "from_tier": upgrade["current_tier"].value,
                    "to_tier": target_tier.value,
                },
            )
            self._audit.log(event)

        return {
            "success": True,
            "previous_tier": upgrade["current_tier"].value,
            "new_tier": target_tier.value,
        }
