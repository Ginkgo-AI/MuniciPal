"""Tests for identity upgrade service."""

from __future__ import annotations

import pytest

from municipal.chat.session import SessionManager
from municipal.core.types import SessionType
from municipal.identity.upgrade import SessionUpgradeService


@pytest.fixture
def session_manager():
    return SessionManager()


@pytest.fixture
def upgrade_service(session_manager):
    return SessionUpgradeService(session_manager=session_manager)


class TestSessionUpgradeService:
    def test_request_upgrade_anonymous_to_verified(self, upgrade_service, session_manager):
        session = session_manager.create_session(SessionType.ANONYMOUS)
        result = upgrade_service.request_upgrade(session.session_id)
        assert result["current_tier"] == "anonymous"
        assert result["target_tier"] == "verified"
        assert "verification_id" in result

    def test_request_upgrade_verified_to_authenticated(self, upgrade_service, session_manager):
        session = session_manager.create_session(SessionType.VERIFIED)
        result = upgrade_service.request_upgrade(session.session_id)
        assert result["current_tier"] == "verified"
        assert result["target_tier"] == "authenticated"

    def test_request_upgrade_at_max_tier_raises(self, upgrade_service, session_manager):
        session = session_manager.create_session(SessionType.AUTHENTICATED)
        with pytest.raises(ValueError, match="maximum tier"):
            upgrade_service.request_upgrade(session.session_id)

    def test_request_upgrade_unknown_session_raises(self, upgrade_service):
        with pytest.raises(KeyError):
            upgrade_service.request_upgrade("nonexistent")

    def test_verify_upgrade_success(self, upgrade_service, session_manager):
        session = session_manager.create_session(SessionType.ANONYMOUS)
        req = upgrade_service.request_upgrade(session.session_id)
        result = upgrade_service.verify_upgrade(
            session.session_id, req["verification_id"], "123456"
        )
        assert result["success"] is True
        assert result["new_tier"] == "verified"
        # Session should be mutated
        updated = session_manager.get_session(session.session_id)
        assert updated.session_type == SessionType.VERIFIED

    def test_verify_upgrade_empty_code_raises(self, upgrade_service, session_manager):
        session = session_manager.create_session(SessionType.ANONYMOUS)
        req = upgrade_service.request_upgrade(session.session_id)
        with pytest.raises(ValueError, match="required"):
            upgrade_service.verify_upgrade(session.session_id, req["verification_id"], "")

    def test_verify_upgrade_wrong_verification_raises(self, upgrade_service, session_manager):
        session = session_manager.create_session(SessionType.ANONYMOUS)
        upgrade_service.request_upgrade(session.session_id)
        with pytest.raises(KeyError):
            upgrade_service.verify_upgrade(session.session_id, "wrong-id", "123456")

    def test_verify_upgrade_wrong_session_raises(self, upgrade_service, session_manager):
        s1 = session_manager.create_session(SessionType.ANONYMOUS)
        s2 = session_manager.create_session(SessionType.ANONYMOUS)
        req = upgrade_service.request_upgrade(s1.session_id)
        with pytest.raises(ValueError, match="does not match"):
            upgrade_service.verify_upgrade(s2.session_id, req["verification_id"], "123456")

    def test_full_upgrade_path(self, upgrade_service, session_manager):
        """Test upgrading from anonymous → verified → authenticated."""
        session = session_manager.create_session(SessionType.ANONYMOUS)

        # Upgrade to verified
        req1 = upgrade_service.request_upgrade(session.session_id)
        upgrade_service.verify_upgrade(session.session_id, req1["verification_id"], "code1")
        assert session_manager.get_session(session.session_id).session_type == SessionType.VERIFIED

        # Upgrade to authenticated
        req2 = upgrade_service.request_upgrade(session.session_id)
        upgrade_service.verify_upgrade(session.session_id, req2["verification_id"], "code2")
        assert session_manager.get_session(session.session_id).session_type == SessionType.AUTHENTICATED
