"""Mission Control v0 — Staff dashboard for Munici-Pal.

Provides routes for the staff-facing control plane: session viewer,
audit log viewer, feedback workflow, shadow mode toggle, shadow
comparisons, model promotion, and staff messaging.
Per ROADMAP.md Section 5.1.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from municipal.core.config import LLMConfig
from municipal.core.types import SessionType

_WEB_DIR = Path(__file__).parent
_TEMPLATES_DIR = _WEB_DIR / "templates"

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()


def _require_staff(request: Request) -> None:
    """Verify the request comes from an authenticated user (staff)."""
    auth_tier = getattr(request.state, "auth_tier", SessionType.ANONYMOUS)
    if auth_tier != SessionType.AUTHENTICATED:
        raise HTTPException(status_code=403, detail="Staff authentication required")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class FlagType(StrEnum):
    """Types of flags staff can apply to messages."""

    INACCURATE = "inaccurate"
    INAPPROPRIATE = "inappropriate"
    MISSING_INFO = "missing_info"
    OTHER = "other"


class FeedbackEntry(BaseModel):
    """A single feedback/flag entry submitted by staff."""

    feedback_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    staff_id: str = "staff"
    session_id: str
    message_index: int
    flag_type: FlagType
    note: str = ""


class FeedbackRequest(BaseModel):
    """Request body for submitting feedback."""

    session_id: str
    message_index: int
    flag_type: str
    note: str = ""
    staff_id: str = "staff"


class ShadowToggleRequest(BaseModel):
    """Request body for toggling shadow mode."""

    session_id: str
    enabled: bool


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------


class FeedbackStore:
    """In-memory store for staff feedback entries."""

    def __init__(self) -> None:
        self._entries: list[FeedbackEntry] = []

    def add(self, entry: FeedbackEntry) -> FeedbackEntry:
        """Add a feedback entry and return it."""
        self._entries.append(entry)
        return entry

    def list_all(self) -> list[FeedbackEntry]:
        """Return all feedback entries, newest first."""
        return sorted(self._entries, key=lambda e: e.timestamp, reverse=True)

    def get_for_session(self, session_id: str) -> list[FeedbackEntry]:
        """Return feedback entries for a specific session."""
        return [e for e in self._entries if e.session_id == session_id]

    def get_by_id(self, feedback_id: str) -> FeedbackEntry | None:
        """Return a single feedback entry by ID."""
        for e in self._entries:
            if e.feedback_id == feedback_id:
                return e
        return None

    def count(self) -> int:
        """Return the number of feedback entries."""
        return len(self._entries)

    def clear(self) -> None:
        """Remove all entries (useful for testing)."""
        self._entries.clear()


class ShadowComparisonResult(BaseModel):
    """Result of a shadow mode comparison between production and candidate models."""

    comparison_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_message: str
    production_response: str
    candidate_response: str
    diverged: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ShadowComparisonStore:
    """In-memory store for shadow comparison results."""

    def __init__(self) -> None:
        self._comparisons: list[ShadowComparisonResult] = []

    def add(self, result: ShadowComparisonResult) -> ShadowComparisonResult:
        self._comparisons.append(result)
        return result

    def list_all(self) -> list[ShadowComparisonResult]:
        return sorted(self._comparisons, key=lambda c: c.timestamp, reverse=True)

    def get_for_session(self, session_id: str) -> list[ShadowComparisonResult]:
        return [c for c in self._comparisons if c.session_id == session_id]

    def stats(self) -> dict[str, Any]:
        total = len(self._comparisons)
        diverged = sum(1 for c in self._comparisons if c.diverged)
        return {
            "total_comparisons": total,
            "diverged_count": diverged,
            "divergence_rate": round(diverged / total, 4) if total > 0 else 0.0,
        }

    def clear(self) -> None:
        self._comparisons.clear()


class ShadowModeManager:
    """In-memory tracker for shadow mode on sessions."""

    def __init__(self) -> None:
        self._shadow_sessions: set[str] = set()
        self.shadow_llm_config: LLMConfig | None = None

    def enable(self, session_id: str) -> None:
        """Enable shadow mode for a session."""
        self._shadow_sessions.add(session_id)

    def disable(self, session_id: str) -> None:
        """Disable shadow mode for a session."""
        self._shadow_sessions.discard(session_id)

    def toggle(self, session_id: str, enabled: bool) -> bool:
        """Set shadow mode state. Returns the new state."""
        if enabled:
            self.enable(session_id)
        else:
            self.disable(session_id)
        return enabled

    def is_active(self, session_id: str) -> bool:
        """Check if shadow mode is active for a session."""
        return session_id in self._shadow_sessions

    def list_active(self) -> list[str]:
        """Return all session IDs with active shadow mode."""
        return list(self._shadow_sessions)

    def clear(self) -> None:
        """Remove all shadow mode state (useful for testing)."""
        self._shadow_sessions.clear()


def get_feedback_store(request: Request) -> FeedbackStore:
    """Get the FeedbackStore from app state."""
    store = getattr(request.app.state, "feedback_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Feedback store not available")
    return store


def get_shadow_manager(request: Request) -> ShadowModeManager:
    """Get the ShadowModeManager from app state."""
    manager = getattr(request.app.state, "shadow_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="Shadow manager not available")
    return manager


# ---------------------------------------------------------------------------
# Template routes (HTML pages)
# ---------------------------------------------------------------------------


@router.get("/staff/", response_class=HTMLResponse)
async def staff_dashboard(request: Request) -> HTMLResponse:
    """Render the Mission Control dashboard."""
    return templates.TemplateResponse(request, "mission_control.html")


@router.get("/staff/sessions", response_class=HTMLResponse)
async def staff_sessions_page(request: Request) -> HTMLResponse:
    """Render the sessions list page (redirects to dashboard)."""
    return templates.TemplateResponse(request, "mission_control.html")


@router.get("/staff/sessions/{session_id}", response_class=HTMLResponse)
async def staff_session_detail_page(request: Request, session_id: str) -> HTMLResponse:
    """Render the session detail page (redirects to dashboard with session pre-selected)."""
    return templates.TemplateResponse(
        request, "mission_control.html", {"selected_session_id": session_id}
    )


@router.get("/staff/audit", response_class=HTMLResponse)
async def staff_audit_page(request: Request) -> HTMLResponse:
    """Render the audit log viewer page."""
    return templates.TemplateResponse(request, "mission_control.html")


# ---------------------------------------------------------------------------
# JSON API routes
# ---------------------------------------------------------------------------


@router.get("/api/staff/sessions")
async def api_staff_sessions(request: Request) -> list[dict[str, Any]]:
    """Return all active sessions with shadow mode status."""
    _require_staff(request)
    session_manager = request.app.state.session_manager
    shadow_manager = get_shadow_manager(request)
    sessions = session_manager.list_active_sessions()

    return [
        {
            "session_id": s.session_id,
            "session_type": s.session_type.value,
            "created_at": s.created_at.isoformat(),
            "last_active": s.last_active.isoformat(),
            "message_count": len(s.messages),
            "shadow_mode": shadow_manager.is_active(s.session_id),
        }
        for s in sessions
    ]


@router.get("/api/staff/audit")
async def api_staff_audit(
    request: Request,
    actor: str | None = None,
    action: str | None = None,
    classification: str | None = None,
    after: str | None = None,
    before: str | None = None,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """Query audit log entries with optional filters."""
    _require_staff(request)
    audit_logger = getattr(request.app.state, "audit_logger", None)
    if audit_logger is None:
        return []

    filters: dict[str, Any] = {}
    if actor:
        filters["actor"] = actor
    if action:
        filters["action"] = action
    if classification:
        filters["classification"] = classification
    if after:
        filters["after"] = after
    if before:
        filters["before"] = before
    if session_id:
        filters["session_id"] = session_id

    events = audit_logger.query(filters)
    return [
        {
            "event_id": e.event_id,
            "timestamp": e.timestamp.isoformat(),
            "session_id": e.session_id,
            "actor": e.actor,
            "action": e.action,
            "resource": e.resource,
            "classification": e.classification.value,
            "details": e.details,
        }
        for e in events
    ]


@router.post("/api/staff/feedback")
async def api_submit_feedback(request: Request, body: FeedbackRequest) -> dict[str, Any]:
    """Submit feedback/flag on a message."""
    _require_staff(request)
    # Validate flag_type
    try:
        flag_type = FlagType(body.flag_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid flag_type: {body.flag_type!r}. "
            f"Must be one of: {', '.join(f.value for f in FlagType)}",
        )

    # Validate session exists
    session_manager = request.app.state.session_manager
    session = session_manager.get_session(body.session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {body.session_id!r} not found",
        )

    # Validate message_index
    if body.message_index < 0 or body.message_index >= len(session.messages):
        raise HTTPException(
            status_code=400,
            detail=f"message_index {body.message_index} out of range "
            f"(session has {len(session.messages)} messages)",
        )

    feedback_store = get_feedback_store(request)
    entry = FeedbackEntry(
        session_id=body.session_id,
        message_index=body.message_index,
        flag_type=flag_type,
        note=body.note,
        staff_id=body.staff_id,
    )
    feedback_store.add(entry)

    return {
        "status": "created",
        "feedback_id": entry.feedback_id,
        "timestamp": entry.timestamp.isoformat(),
    }


@router.get("/api/staff/feedback")
async def api_list_feedback(
    request: Request,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """List all feedback entries, optionally filtered by session."""
    _require_staff(request)
    feedback_store = get_feedback_store(request)

    if session_id:
        entries = feedback_store.get_for_session(session_id)
    else:
        entries = feedback_store.list_all()

    return [
        {
            "feedback_id": e.feedback_id,
            "timestamp": e.timestamp.isoformat(),
            "staff_id": e.staff_id,
            "session_id": e.session_id,
            "message_index": e.message_index,
            "flag_type": e.flag_type.value,
            "note": e.note,
        }
        for e in entries
    ]


@router.post("/api/staff/shadow")
async def api_toggle_shadow(request: Request, body: ShadowToggleRequest) -> dict[str, Any]:
    """Toggle shadow mode for a session."""
    _require_staff(request)
    shadow_manager = get_shadow_manager(request)
    new_state = shadow_manager.toggle(body.session_id, body.enabled)
    return {
        "session_id": body.session_id,
        "shadow_mode": new_state,
    }


# ---------------------------------------------------------------------------
# Phase 3: Approval queue, Metrics, Session takeover
# ---------------------------------------------------------------------------


@router.get("/api/staff/approvals")
async def api_list_approvals(request: Request) -> list[dict[str, Any]]:
    """List pending approval requests."""
    _require_staff(request)
    approval_gate = getattr(request.app.state, "approval_gate", None)
    if approval_gate is None:
        return []
    from municipal.core.types import ApprovalStatus
    requests = approval_gate.list_all_requests()
    return [
        {
            "request_id": r.request_id,
            "gate_type": r.gate_type,
            "resource": r.resource,
            "requestor": r.requestor,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "approver": r.approver,
            "deny_reason": r.deny_reason,
        }
        for r in requests
    ]


@router.get("/api/staff/approvals/{request_id}")
async def api_get_approval(request_id: str, request: Request) -> dict[str, Any]:
    """Get approval request detail."""
    _require_staff(request)
    approval_gate = getattr(request.app.state, "approval_gate", None)
    if approval_gate is None:
        raise HTTPException(status_code=503, detail="Approval gate not available")
    try:
        r = approval_gate.get_request(request_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Approval request {request_id!r} not found")
    return {
        "request_id": r.request_id,
        "gate_type": r.gate_type,
        "resource": r.resource,
        "requestor": r.requestor,
        "status": r.status,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
        "approver": r.approver,
        "deny_reason": r.deny_reason,
        "approvals": r.approvals,
    }


class ApprovalActionRequest(BaseModel):
    """Request body for approve/deny actions."""
    approver: str = "staff"
    reason: str = ""


@router.post("/api/staff/approvals/{request_id}/approve")
async def api_approve_request(
    request_id: str, request: Request, body: ApprovalActionRequest | None = None
) -> dict[str, Any]:
    """Approve an approval request."""
    _require_staff(request)
    approval_gate = getattr(request.app.state, "approval_gate", None)
    if approval_gate is None:
        raise HTTPException(status_code=503, detail="Approval gate not available")
    approver = body.approver if body else "staff"
    try:
        r = approval_gate.approve(request_id, approver)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Approval request {request_id!r} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"request_id": r.request_id, "status": r.status, "approver": r.approver}


@router.post("/api/staff/approvals/{request_id}/deny")
async def api_deny_request(
    request_id: str, body: ApprovalActionRequest, request: Request
) -> dict[str, Any]:
    """Deny an approval request."""
    _require_staff(request)
    approval_gate = getattr(request.app.state, "approval_gate", None)
    if approval_gate is None:
        raise HTTPException(status_code=503, detail="Approval gate not available")
    try:
        r = approval_gate.deny(request_id, body.approver, body.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Approval request {request_id!r} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"request_id": r.request_id, "status": r.status, "deny_reason": r.deny_reason}


@router.get("/api/staff/metrics")
async def api_metrics(request: Request) -> dict[str, Any]:
    """Metrics dashboard snapshot."""
    _require_staff(request)
    metrics_service = getattr(request.app.state, "metrics_service", None)
    if metrics_service is None:
        return {"error": "Metrics service not available"}
    snapshot = metrics_service.snapshot()
    return snapshot.model_dump(mode="json")


@router.get("/api/staff/metrics/adapters")
async def api_adapter_metrics(request: Request) -> dict[str, Any]:
    """Adapter health and usage metrics."""
    _require_staff(request)
    registry = getattr(request.app.state, "adapter_registry", None)
    if registry is None:
        return {"adapters": []}
    health = registry.health_check_all()
    return {
        "adapters": [
            {"name": name, "status": status.value}
            for name, status in health.items()
        ]
    }


class TakeoverRequest(BaseModel):
    staff_id: str = "staff"


@router.post("/api/staff/sessions/{session_id}/takeover")
async def api_takeover_session(
    session_id: str, request: Request, body: TakeoverRequest | None = None
) -> dict[str, Any]:
    """Staff takes over a session."""
    _require_staff(request)
    takeover_mgr = getattr(request.app.state, "takeover_manager", None)
    if takeover_mgr is None:
        raise HTTPException(status_code=503, detail="Takeover manager not available")
    staff_id = body.staff_id if body else "staff"
    return takeover_mgr.takeover(session_id, staff_id)


@router.post("/api/staff/sessions/{session_id}/release")
async def api_release_session(session_id: str, request: Request) -> dict[str, Any]:
    """Release a taken-over session."""
    _require_staff(request)
    takeover_mgr = getattr(request.app.state, "takeover_manager", None)
    if takeover_mgr is None:
        raise HTTPException(status_code=503, detail="Takeover manager not available")
    return takeover_mgr.release(session_id)


# ---------------------------------------------------------------------------
# Phase 5: Shadow comparisons
# ---------------------------------------------------------------------------


def _get_comparison_store(request: Request) -> ShadowComparisonStore:
    store = getattr(request.app.state, "comparison_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Comparison store not available")
    return store


@router.get("/api/staff/shadow/comparisons")
async def api_shadow_comparisons(request: Request) -> list[dict[str, Any]]:
    """List all shadow comparison results."""
    _require_staff(request)
    store = _get_comparison_store(request)
    return [c.model_dump(mode="json") for c in store.list_all()]


@router.get("/api/staff/shadow/stats")
async def api_shadow_stats(request: Request) -> dict[str, Any]:
    """Get shadow mode divergence statistics."""
    _require_staff(request)
    store = _get_comparison_store(request)
    return store.stats()


# ---------------------------------------------------------------------------
# Phase 5: Model promotion
# ---------------------------------------------------------------------------


class CandidateModelRequest(BaseModel):
    """Request body for registering a candidate model."""

    provider: str = "vllm"
    base_url: str
    model: str
    api_key: str | None = None
    max_tokens: int = 2048


@router.post("/api/staff/models/candidate")
async def api_set_candidate(body: CandidateModelRequest, request: Request) -> dict[str, Any]:
    """Register a candidate model for shadow testing."""
    _require_staff(request)
    model_registry = getattr(request.app.state, "model_registry", None)
    if model_registry is None:
        raise HTTPException(status_code=503, detail="Model registry not available")

    config = LLMConfig(
        provider=body.provider,
        base_url=body.base_url,
        model=body.model,
        api_key=body.api_key,
        max_tokens=body.max_tokens,
    )
    model_registry.set_candidate(config)

    # Also update shadow manager's LLM config
    shadow_manager = get_shadow_manager(request)
    shadow_manager.shadow_llm_config = config

    return {"status": "candidate_registered", "model": body.model, "base_url": body.base_url}


@router.get("/api/staff/models")
async def api_list_models(request: Request) -> dict[str, Any]:
    """List production and candidate model configurations."""
    _require_staff(request)
    model_registry = getattr(request.app.state, "model_registry", None)
    if model_registry is None:
        raise HTTPException(status_code=503, detail="Model registry not available")
    return model_registry.summary()


@router.post("/api/staff/models/promote")
async def api_promote_candidate(request: Request) -> dict[str, Any]:
    """Promote the candidate model to production."""
    _require_staff(request)
    model_registry = getattr(request.app.state, "model_registry", None)
    if model_registry is None:
        raise HTTPException(status_code=503, detail="Model registry not available")
    try:
        promoted = model_registry.promote_candidate()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "promoted", "production": promoted.model_dump(exclude={"api_key"})}


# ---------------------------------------------------------------------------
# Phase 5: Staff sends message to session
# ---------------------------------------------------------------------------


class StaffMessageRequest(BaseModel):
    """Request body for staff sending a message to a session."""

    staff_id: str = "staff"
    message: str


@router.post("/api/staff/sessions/{session_id}/message")
async def api_staff_message(
    session_id: str, body: StaffMessageRequest, request: Request
) -> dict[str, Any]:
    """Staff sends a direct message to a session."""
    _require_staff(request)
    session_manager = request.app.state.session_manager
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    from municipal.chat.session import ChatMessage, MessageRole

    msg = ChatMessage(
        role=MessageRole.ASSISTANT,
        content=f"[Staff: {body.staff_id}] {body.message}",
    )
    session_manager.add_message(session_id, msg)

    return {
        "session_id": session_id,
        "staff_id": body.staff_id,
        "message": body.message,
        "timestamp": msg.timestamp.isoformat(),
    }
