"""Approval gate engine for Munici-Pal.

Implements the approval gates defined in REFERENCE.md Section 7.
Gate definitions are loaded from YAML config. Approval requests are stored
in memory for now (future: persistent store).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from municipal.core.types import ApprovalStatus


# Default path to the approval policies config
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "approval_policies.yml"


class ApprovalRequest(BaseModel):
    """An in-flight approval request."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    gate_type: str
    resource: str
    requestor: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approver: str | None = None
    deny_reason: str | None = None
    approvals: list[dict[str, Any]] = Field(default_factory=list)


class GateDefinition(BaseModel):
    """Parsed gate definition from YAML config."""

    gate_id: str
    name: str
    description: str
    trigger: str
    required_approvers: list[dict[str, Any]]
    min_approvals: int = 1
    timeout_hours: int = 24
    escalation: dict[str, Any] = Field(default_factory=dict)
    classification_minimum: str = "sensitive"


class ApprovalGate:
    """Approval gate engine.

    Manages approval requests against gate definitions loaded from YAML config.
    Requests are stored in memory (dict keyed by request_id).
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config_path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._gates: dict[str, GateDefinition] = {}
        self._requests: dict[str, ApprovalRequest] = {}
        self._policy: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load gate definitions from YAML config."""
        with open(self._config_path) as fh:
            config = yaml.safe_load(fh)

        for gate_id, gate_data in config.get("gates", {}).items():
            self._gates[gate_id] = GateDefinition(
                gate_id=gate_id,
                name=gate_data["name"],
                description=gate_data.get("description", ""),
                trigger=gate_data.get("trigger", ""),
                required_approvers=gate_data.get("required_approvers", []),
                min_approvals=gate_data.get("min_approvals", 1),
                timeout_hours=gate_data.get("timeout_hours", 24),
                escalation=gate_data.get("escalation", {}),
                classification_minimum=gate_data.get("classification_minimum", "sensitive"),
            )

        self._policy = config.get("policy", {})

    def request_approval(
        self,
        gate_type: str,
        resource: str,
        requestor: str,
    ) -> ApprovalRequest:
        """Create a new approval request for a given gate type.

        Args:
            gate_type: The gate identifier (e.g. ``permit_decision``).
            resource: Description or ID of the resource requiring approval.
            requestor: Identity of the person requesting approval.

        Returns:
            The newly created ApprovalRequest.

        Raises:
            ValueError: If the gate_type is not defined in config.
        """
        if gate_type not in self._gates:
            raise ValueError(
                f"Unknown gate type '{gate_type}'. "
                f"Available gates: {list(self._gates.keys())}"
            )

        request = ApprovalRequest(
            gate_type=gate_type,
            resource=resource,
            requestor=requestor,
        )
        self._requests[request.request_id] = request
        return request

    def approve(self, request_id: str, approver: str) -> ApprovalRequest:
        """Approve a pending request.

        Args:
            request_id: The ID of the approval request.
            approver: Identity of the approving party.

        Returns:
            The updated ApprovalRequest.

        Raises:
            KeyError: If request_id is not found.
            ValueError: If the request is not in PENDING status.
        """
        request = self._get_request(request_id)
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Request {request_id} is '{request.status}', not pending."
            )

        gate = self._gates[request.gate_type]
        request.approvals.append({
            "approver": approver,
            "action": "approve",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Check if we have enough approvals
        if len(request.approvals) >= gate.min_approvals:
            request.status = ApprovalStatus.APPROVED
            request.approver = approver

        request.updated_at = datetime.now(timezone.utc)
        return request

    def deny(self, request_id: str, approver: str, reason: str) -> ApprovalRequest:
        """Deny a pending request.

        Args:
            request_id: The ID of the approval request.
            approver: Identity of the denying party.
            reason: Reason for denial.

        Returns:
            The updated ApprovalRequest.

        Raises:
            KeyError: If request_id is not found.
            ValueError: If the request is not in PENDING status.
        """
        request = self._get_request(request_id)
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Request {request_id} is '{request.status}', not pending."
            )

        request.status = ApprovalStatus.DENIED
        request.approver = approver
        request.deny_reason = reason
        request.updated_at = datetime.now(timezone.utc)
        return request

    def check_status(self, request_id: str) -> ApprovalStatus:
        """Check the current status of an approval request.

        Args:
            request_id: The ID of the approval request.

        Returns:
            The current ApprovalStatus.

        Raises:
            KeyError: If request_id is not found.
        """
        return self._get_request(request_id).status

    def get_request(self, request_id: str) -> ApprovalRequest:
        """Retrieve an approval request by ID.

        Raises:
            KeyError: If request_id is not found.
        """
        return self._get_request(request_id)

    def get_gate(self, gate_type: str) -> GateDefinition | None:
        """Retrieve a gate definition by ID."""
        return self._gates.get(gate_type)

    @property
    def gates(self) -> dict[str, GateDefinition]:
        """All loaded gate definitions."""
        return dict(self._gates)

    @property
    def pending_requests(self) -> list[ApprovalRequest]:
        """All requests currently in PENDING status."""
        return [r for r in self._requests.values() if r.status == ApprovalStatus.PENDING]

    def _get_request(self, request_id: str) -> ApprovalRequest:
        """Internal helper to fetch a request or raise KeyError."""
        if request_id not in self._requests:
            raise KeyError(f"Approval request '{request_id}' not found.")
        return self._requests[request_id]
