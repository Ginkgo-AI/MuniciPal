"""Mission Control v0 — Staff dashboard for Munici-Pal.

Provides routes for the staff-facing control plane: session viewer,
audit log viewer, feedback workflow, and shadow mode toggle.
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

_WEB_DIR = Path(__file__).parent
_TEMPLATES_DIR = _WEB_DIR / "templates"

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()


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


class ShadowModeManager:
    """In-memory tracker for shadow mode on sessions."""

    def __init__(self) -> None:
        self._shadow_sessions: set[str] = set()

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


# Module-level singleton instances (attached to app state in create_app)
_feedback_store = FeedbackStore()
_shadow_manager = ShadowModeManager()


def get_feedback_store(request: Request) -> FeedbackStore:
    """Get the FeedbackStore from app state, falling back to module-level."""
    return getattr(request.app.state, "feedback_store", _feedback_store)


def get_shadow_manager(request: Request) -> ShadowModeManager:
    """Get the ShadowModeManager from app state, falling back to module-level."""
    return getattr(request.app.state, "shadow_manager", _shadow_manager)


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
    shadow_manager = get_shadow_manager(request)
    new_state = shadow_manager.toggle(body.session_id, body.enabled)
    return {
        "session_id": body.session_id,
        "shadow_mode": new_state,
    }
