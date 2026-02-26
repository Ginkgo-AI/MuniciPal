"""Mission Control v1 services: metrics, session takeover."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from municipal.bridge.models import ConnectionStatus


class MetricsSnapshot(BaseModel):
    """Live metrics dashboard snapshot."""

    total_sessions: int = 0
    active_sessions: int = 0
    total_cases: int = 0
    pending_approvals: int = 0
    approved_count: int = 0
    denied_count: int = 0
    adapter_health: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MetricsService:
    """Computes live metrics from in-memory stores."""

    def __init__(
        self,
        session_manager: Any = None,
        intake_store: Any = None,
        approval_gate: Any = None,
        adapter_registry: Any = None,
    ) -> None:
        self._sessions = session_manager
        self._intake = intake_store
        self._approval = approval_gate
        self._registry = adapter_registry

    def snapshot(self) -> MetricsSnapshot:
        sessions = self._sessions.list_active_sessions() if self._sessions else []
        total_sessions = len(sessions)

        total_cases = 0
        if self._intake:
            total_cases = len(self._intake._cases)

        pending = 0
        approved = 0
        denied = 0
        if self._approval:
            for req in self._approval._requests.values():
                if req.status == "pending":
                    pending += 1
                elif req.status == "approved":
                    approved += 1
                elif req.status == "denied":
                    denied += 1

        adapter_health: dict[str, str] = {}
        if self._registry:
            adapter_health = {
                name: status.value
                for name, status in self._registry.health_check_all().items()
            }

        return MetricsSnapshot(
            total_sessions=total_sessions,
            active_sessions=total_sessions,
            total_cases=total_cases,
            pending_approvals=pending,
            approved_count=approved,
            denied_count=denied,
            adapter_health=adapter_health,
        )


class SessionTakeoverManager:
    """Manages staff session takeovers."""

    def __init__(self) -> None:
        self._takeovers: dict[str, str] = {}  # session_id -> staff_id

    def takeover(self, session_id: str, staff_id: str) -> dict[str, Any]:
        self._takeovers[session_id] = staff_id
        return {
            "session_id": session_id,
            "staff_id": staff_id,
            "status": "taken_over",
        }

    def release(self, session_id: str) -> dict[str, Any]:
        staff_id = self._takeovers.pop(session_id, None)
        return {
            "session_id": session_id,
            "staff_id": staff_id,
            "status": "released",
        }

    def is_taken_over(self, session_id: str) -> bool:
        return session_id in self._takeovers

    def get_controller(self, session_id: str) -> str | None:
        return self._takeovers.get(session_id)

    def list_takeovers(self) -> dict[str, str]:
        return dict(self._takeovers)
