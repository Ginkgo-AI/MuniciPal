"""Tests for governance module: approval gates and audit logger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from municipal.core.config import AuditConfig
from municipal.core.types import ApprovalStatus, AuditEvent, DataClassification
from municipal.governance.approval import ApprovalGate
from municipal.governance.audit import AuditLogger


# ---------------------------------------------------------------------------
# Approval Gate tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def approval_config_path(tmp_path: Path) -> Path:
    """Write a minimal approval config and return its path."""
    config = {
        "gates": {
            "permit_decision": {
                "name": "Permit Decision",
                "description": "Issuance or denial of any permit",
                "trigger": "permit_issuance_or_denial",
                "required_approvers": [
                    {"role": "department_reviewer", "required": True},
                    {"role": "supervisor", "required": True},
                ],
                "min_approvals": 2,
                "timeout_hours": 48,
                "escalation": {"role": "department_head", "auto_escalate": True},
                "classification_minimum": "sensitive",
            },
            "data_export": {
                "name": "Data Export",
                "description": "Bulk data export",
                "trigger": "bulk_data_export",
                "required_approvers": [
                    {"role": "data_steward", "required": True},
                ],
                "min_approvals": 1,
                "timeout_hours": 24,
                "escalation": {"role": "it_director"},
                "classification_minimum": "sensitive",
            },
        },
        "policy": {
            "require_justification": True,
            "audit_all_actions": True,
        },
    }
    path = tmp_path / "approval_policies.yml"
    path.write_text(yaml.dump(config))
    return path


@pytest.fixture()
def gate(approval_config_path: Path) -> ApprovalGate:
    return ApprovalGate(config_path=approval_config_path)


class TestApprovalGate:
    def test_request_approval_creates_pending(self, gate: ApprovalGate) -> None:
        req = gate.request_approval("permit_decision", "permit-123", "jane@city.gov")
        assert req.status == ApprovalStatus.PENDING
        assert req.gate_type == "permit_decision"
        assert req.resource == "permit-123"
        assert req.requestor == "jane@city.gov"

    def test_check_status(self, gate: ApprovalGate) -> None:
        req = gate.request_approval("permit_decision", "permit-456", "jane@city.gov")
        assert gate.check_status(req.request_id) == ApprovalStatus.PENDING

    def test_single_approval_not_enough_for_two_required(self, gate: ApprovalGate) -> None:
        req = gate.request_approval("permit_decision", "permit-789", "jane@city.gov")
        updated = gate.approve(req.request_id, "reviewer@city.gov")
        # permit_decision requires min_approvals=2, so one isn't enough
        assert updated.status == ApprovalStatus.PENDING
        assert len(updated.approvals) == 1

    def test_two_approvals_approve_request(self, gate: ApprovalGate) -> None:
        req = gate.request_approval("permit_decision", "permit-101", "jane@city.gov")
        gate.approve(req.request_id, "reviewer@city.gov")
        updated = gate.approve(req.request_id, "supervisor@city.gov")
        assert updated.status == ApprovalStatus.APPROVED
        assert updated.approver == "supervisor@city.gov"

    def test_single_approval_enough_for_data_export(self, gate: ApprovalGate) -> None:
        req = gate.request_approval("data_export", "report-2024", "analyst@city.gov")
        updated = gate.approve(req.request_id, "steward@city.gov")
        assert updated.status == ApprovalStatus.APPROVED

    def test_deny_request(self, gate: ApprovalGate) -> None:
        req = gate.request_approval("permit_decision", "permit-202", "jane@city.gov")
        updated = gate.deny(req.request_id, "supervisor@city.gov", "Incomplete documentation")
        assert updated.status == ApprovalStatus.DENIED
        assert updated.deny_reason == "Incomplete documentation"

    def test_approve_non_pending_raises(self, gate: ApprovalGate) -> None:
        req = gate.request_approval("data_export", "report-x", "analyst@city.gov")
        gate.approve(req.request_id, "steward@city.gov")
        with pytest.raises(ValueError, match="not pending"):
            gate.approve(req.request_id, "another@city.gov")

    def test_deny_non_pending_raises(self, gate: ApprovalGate) -> None:
        req = gate.request_approval("data_export", "report-y", "analyst@city.gov")
        gate.approve(req.request_id, "steward@city.gov")
        with pytest.raises(ValueError, match="not pending"):
            gate.deny(req.request_id, "boss@city.gov", "changed mind")

    def test_unknown_gate_raises(self, gate: ApprovalGate) -> None:
        with pytest.raises(ValueError, match="Unknown gate type"):
            gate.request_approval("nonexistent_gate", "res", "user@city.gov")

    def test_unknown_request_id_raises(self, gate: ApprovalGate) -> None:
        with pytest.raises(KeyError):
            gate.check_status("nonexistent-id")

    def test_pending_requests_list(self, gate: ApprovalGate) -> None:
        gate.request_approval("data_export", "r1", "a@city.gov")
        gate.request_approval("data_export", "r2", "b@city.gov")
        assert len(gate.pending_requests) == 2

    def test_gates_property(self, gate: ApprovalGate) -> None:
        gates = gate.gates
        assert "permit_decision" in gates
        assert "data_export" in gates
        assert gates["permit_decision"].min_approvals == 2


# ---------------------------------------------------------------------------
# Audit Logger tests
# ---------------------------------------------------------------------------


def _make_event(**overrides) -> AuditEvent:
    """Helper to build an AuditEvent with sensible defaults."""
    defaults = {
        "session_id": "sess-001",
        "actor": "staff@city.gov",
        "action": "query",
        "resource": "ordinances",
        "classification": DataClassification.PUBLIC,
    }
    defaults.update(overrides)
    return AuditEvent(**defaults)


@pytest.fixture()
def audit_dir(tmp_path: Path) -> Path:
    d = tmp_path / "audit"
    d.mkdir()
    return d


@pytest.fixture()
def logger(audit_dir: Path) -> AuditLogger:
    config = AuditConfig(log_dir=str(audit_dir))
    return AuditLogger(config=config)


class TestAuditLogger:
    def test_log_creates_file(self, logger: AuditLogger) -> None:
        event = _make_event()
        logger.log(event)
        assert logger.log_path.exists()

    def test_log_returns_entry_with_hash(self, logger: AuditLogger) -> None:
        event = _make_event()
        entry = logger.log(event)
        assert entry.entry_hash
        assert entry.previous_hash
        assert entry.entry_hash != entry.previous_hash

    def test_verify_chain_empty(self, logger: AuditLogger) -> None:
        assert logger.verify_chain() is True

    def test_verify_chain_single_entry(self, logger: AuditLogger) -> None:
        logger.log(_make_event())
        assert logger.verify_chain() is True

    def test_verify_chain_multiple_entries(self, logger: AuditLogger) -> None:
        for i in range(5):
            logger.log(_make_event(action=f"action_{i}"))
        assert logger.verify_chain() is True

    def test_hash_chain_links_entries(self, logger: AuditLogger) -> None:
        e1 = logger.log(_make_event(action="first"))
        e2 = logger.log(_make_event(action="second"))
        # Second entry's previous_hash should equal first entry's hash
        assert e2.previous_hash == e1.entry_hash

    def test_tampered_entry_breaks_chain(self, logger: AuditLogger) -> None:
        logger.log(_make_event(action="original_1"))
        logger.log(_make_event(action="original_2"))
        logger.log(_make_event(action="original_3"))
        assert logger.verify_chain() is True

        # Tamper with the second line
        lines = logger.log_path.read_text().strip().split("\n")
        data = json.loads(lines[1])
        data["event"]["action"] = "TAMPERED"
        lines[1] = json.dumps(data)
        logger.log_path.write_text("\n".join(lines) + "\n")

        assert logger.verify_chain() is False

    def test_tampered_hash_breaks_chain(self, logger: AuditLogger) -> None:
        logger.log(_make_event(action="a"))
        logger.log(_make_event(action="b"))

        lines = logger.log_path.read_text().strip().split("\n")
        data = json.loads(lines[0])
        data["entry_hash"] = "0" * 64  # fake hash
        lines[0] = json.dumps(data)
        logger.log_path.write_text("\n".join(lines) + "\n")

        assert logger.verify_chain() is False

    def test_query_no_filters(self, logger: AuditLogger) -> None:
        logger.log(_make_event(action="a"))
        logger.log(_make_event(action="b"))
        results = logger.query()
        assert len(results) == 2

    def test_query_filter_by_actor(self, logger: AuditLogger) -> None:
        logger.log(_make_event(actor="alice@city.gov", action="x"))
        logger.log(_make_event(actor="bob@city.gov", action="y"))
        results = logger.query({"actor": "alice@city.gov"})
        assert len(results) == 1
        assert results[0].actor == "alice@city.gov"

    def test_query_filter_by_action(self, logger: AuditLogger) -> None:
        logger.log(_make_event(action="read"))
        logger.log(_make_event(action="write"))
        logger.log(_make_event(action="read"))
        results = logger.query({"action": "read"})
        assert len(results) == 2

    def test_query_filter_by_classification(self, logger: AuditLogger) -> None:
        logger.log(_make_event(classification=DataClassification.PUBLIC))
        logger.log(_make_event(classification=DataClassification.SENSITIVE))
        results = logger.query({"classification": "sensitive"})
        assert len(results) == 1

    def test_recover_last_hash_on_reopen(self, audit_dir: Path) -> None:
        config = AuditConfig(log_dir=str(audit_dir))
        logger1 = AuditLogger(config=config)
        e1 = logger1.log(_make_event(action="first"))

        # Create a new logger instance pointing to the same file
        logger2 = AuditLogger(config=config)
        assert logger2.last_hash == e1.entry_hash

        # Continue logging with the new instance
        e2 = logger2.log(_make_event(action="second"))
        assert e2.previous_hash == e1.entry_hash

        # Verify the combined chain
        assert logger2.verify_chain() is True


class TestProductionApprovalConfig:
    """Test that the production approval YAML config loads correctly."""

    def test_production_config_loads(self) -> None:
        config_path = (
            Path(__file__).resolve().parents[1] / "config" / "approval_policies.yml"
        )
        if not config_path.exists():
            pytest.skip("Production config not found")

        gate = ApprovalGate(config_path=config_path)
        gates = gate.gates
        assert "permit_decision" in gates
        assert "foia_release" in gates
        assert "payment_refund" in gates
        assert "legal_correspondence" in gates
        assert "record_modification" in gates
        assert "data_export" in gates
