"""PostgreSQL approval repository.

The ApprovalGate retains business logic and YAML config.
This repository handles CRUD for approval requests only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from municipal.core.types import ApprovalStatus
from municipal.db.engine import DatabaseManager
from municipal.db.models import ApprovalRequestRow
from municipal.governance.approval import ApprovalGate, ApprovalRequest, GateDefinition


class PostgresApprovalRepository:
    """Postgres-backed approval request storage.

    Wraps an ApprovalGate for gate definitions (YAML config) while
    persisting requests to PostgreSQL.
    """

    def __init__(self, db: DatabaseManager, config_path: str | Path | None = None) -> None:
        self._db = db
        self._gate = ApprovalGate(config_path=config_path)

    def request_approval(
        self, gate_type: str, resource: str, requestor: str
    ) -> Any:
        async def _inner():
            if self._gate.get_gate(gate_type) is None:
                raise ValueError(
                    f"Unknown gate type '{gate_type}'. "
                    f"Available gates: {list(self._gate.gates.keys())}"
                )
            request = ApprovalRequest(
                gate_type=gate_type, resource=resource, requestor=requestor
            )
            async with self._db.session() as db:
                row = ApprovalRequestRow(
                    request_id=request.request_id,
                    gate_type=request.gate_type,
                    resource=request.resource,
                    requestor=request.requestor,
                    status=request.status.value,
                    created_at=request.created_at,
                    updated_at=request.updated_at,
                    approvals=[],
                )
                db.add(row)
                await db.commit()
            return request

        return _inner()

    def approve(self, request_id: str, approver: str) -> Any:
        async def _inner():
            async with self._db.session() as db:
                row = await db.get(ApprovalRequestRow, request_id)
                if row is None:
                    raise KeyError(f"Approval request '{request_id}' not found.")
                if row.status != ApprovalStatus.PENDING:
                    raise ValueError(
                        f"Request {request_id} is '{row.status}', not pending."
                    )
                gate = self._gate.get_gate(row.gate_type)
                if gate is None:
                    raise ValueError(
                        f"Gate type '{row.gate_type}' no longer exists in configuration."
                    )
                approvals = list(row.approvals or [])
                approvals.append({
                    "approver": approver,
                    "action": "approve",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                row.approvals = approvals
                if len(approvals) >= gate.min_approvals:
                    row.status = ApprovalStatus.APPROVED.value
                    row.approver = approver
                row.updated_at = datetime.now(timezone.utc)
                await db.commit()
                return self._row_to_request(row)

        return _inner()

    def deny(self, request_id: str, approver: str, reason: str) -> Any:
        async def _inner():
            async with self._db.session() as db:
                row = await db.get(ApprovalRequestRow, request_id)
                if row is None:
                    raise KeyError(f"Approval request '{request_id}' not found.")
                if row.status != ApprovalStatus.PENDING:
                    raise ValueError(
                        f"Request {request_id} is '{row.status}', not pending."
                    )
                row.status = ApprovalStatus.DENIED.value
                row.approver = approver
                row.deny_reason = reason
                row.updated_at = datetime.now(timezone.utc)
                await db.commit()
                return self._row_to_request(row)

        return _inner()

    def check_status(self, request_id: str) -> Any:
        async def _inner():
            async with self._db.session() as db:
                row = await db.get(ApprovalRequestRow, request_id)
                if row is None:
                    raise KeyError(f"Approval request '{request_id}' not found.")
                return ApprovalStatus(row.status)

        return _inner()

    def get_request(self, request_id: str) -> Any:
        async def _inner():
            async with self._db.session() as db:
                row = await db.get(ApprovalRequestRow, request_id)
                if row is None:
                    raise KeyError(f"Approval request '{request_id}' not found.")
                return self._row_to_request(row)

        return _inner()

    def get_gate(self, gate_type: str) -> GateDefinition | None:
        return self._gate.get_gate(gate_type)

    @property
    def gates(self) -> dict[str, GateDefinition]:
        return self._gate.gates

    @property
    def pending_requests(self) -> Any:
        async def _inner():
            async with self._db.session() as db:
                result = await db.execute(
                    select(ApprovalRequestRow).where(
                        ApprovalRequestRow.status == ApprovalStatus.PENDING.value
                    )
                )
                return [self._row_to_request(r) for r in result.scalars().all()]

        return _inner()

    def list_all_requests(self) -> Any:
        async def _inner():
            async with self._db.session() as db:
                result = await db.execute(select(ApprovalRequestRow))
                return [self._row_to_request(r) for r in result.scalars().all()]

        return _inner()

    @staticmethod
    def _row_to_request(row: ApprovalRequestRow) -> ApprovalRequest:
        return ApprovalRequest(
            request_id=row.request_id,
            gate_type=row.gate_type,
            resource=row.resource,
            requestor=row.requestor,
            status=ApprovalStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
            approver=row.approver,
            deny_reason=row.deny_reason,
            approvals=row.approvals or [],
        )
