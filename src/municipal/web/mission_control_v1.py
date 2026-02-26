"""Mission Control v1 services: metrics, session takeover, LLM latency tracking."""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from municipal.bridge.models import ConnectionStatus


class LLMLatencyTracker:
    """Rolling window tracker for LLM response latencies (p50/p95)."""

    def __init__(self, window_size: int = 100) -> None:
        self._latencies: deque[float] = deque(maxlen=window_size)

    def record(self, latency_ms: float) -> None:
        self._latencies.append(latency_ms)

    def p50(self) -> float | None:
        if not self._latencies:
            return None
        return self._percentile(50)

    def p95(self) -> float | None:
        if not self._latencies:
            return None
        return self._percentile(95)

    def _percentile(self, pct: float) -> float:
        sorted_vals = sorted(self._latencies)
        n = len(sorted_vals)
        idx = (pct / 100.0) * (n - 1)
        lower = int(idx)
        upper = min(lower + 1, n - 1)
        frac = idx - lower
        return round(sorted_vals[lower] * (1 - frac) + sorted_vals[upper] * frac, 2)

    @property
    def count(self) -> int:
        return len(self._latencies)

    def clear(self) -> None:
        self._latencies.clear()


class MetricsSnapshot(BaseModel):
    """Live metrics dashboard snapshot."""

    total_sessions: int = 0
    active_sessions: int = 0
    total_cases: int = 0
    pending_approvals: int = 0
    approved_count: int = 0
    denied_count: int = 0
    adapter_health: dict[str, str] = Field(default_factory=dict)
    llm_latency_p50_ms: float | None = None
    llm_latency_p95_ms: float | None = None
    shadow_divergence_rate: float | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MetricsService:
    """Computes live metrics from in-memory stores."""

    def __init__(
        self,
        session_manager: Any = None,
        intake_store: Any = None,
        approval_gate: Any = None,
        adapter_registry: Any = None,
        llm_tracker: LLMLatencyTracker | None = None,
        comparison_store: Any = None,
    ) -> None:
        self._sessions = session_manager
        self._intake = intake_store
        self._approval = approval_gate
        self._registry = adapter_registry
        self._llm_tracker = llm_tracker
        self._comparison_store = comparison_store

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

        llm_p50 = self._llm_tracker.p50() if self._llm_tracker else None
        llm_p95 = self._llm_tracker.p95() if self._llm_tracker else None

        shadow_divergence: float | None = None
        if self._comparison_store:
            stats = self._comparison_store.stats()
            if stats["total_comparisons"] > 0:
                shadow_divergence = stats["divergence_rate"]

        return MetricsSnapshot(
            total_sessions=total_sessions,
            active_sessions=total_sessions,
            total_cases=total_cases,
            pending_approvals=pending,
            approved_count=approved,
            denied_count=denied,
            adapter_health=adapter_health,
            llm_latency_p50_ms=llm_p50,
            llm_latency_p95_ms=llm_p95,
            shadow_divergence_rate=shadow_divergence,
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
