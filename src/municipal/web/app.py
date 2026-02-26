"""FastAPI application for Munici-Pal Digital Librarian.

Provides REST API endpoints for chat, session management, and health
checks, plus serves the browser-based chat UI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from municipal.chat.service import ChatService
from municipal.chat.session import SessionManager
from municipal.core.config import Settings
from municipal.core.types import SessionType
from municipal.export.renderer import PacketRenderer
from municipal.gis.service import MockGISService
from municipal.governance.approval import ApprovalGate
from municipal.governance.audit import AuditLogger
from municipal.i18n.engine import I18nEngine
from municipal.identity.upgrade import SessionUpgradeService
from municipal.intake.engine import WizardEngine
from municipal.intake.store import IntakeStore
from municipal.intake.validation import ValidationEngine
from municipal.rag.pipeline import RAGPipeline, create_rag_pipeline
from municipal.web.intake_router import router as intake_router
from municipal.web.mission_control import (
    FeedbackStore,
    ShadowModeManager,
    router as mission_control_router,
)

_WEB_DIR = Path(__file__).parent
_TEMPLATES_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"


# --- Request/Response models ---


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    session_id: str
    message: str


class ChatResponse(BaseModel):
    """Response body for the chat endpoint."""

    response: str
    citations: list[dict[str, Any]]
    confidence: float
    low_confidence: bool


class SessionCreateRequest(BaseModel):
    """Request body for creating a session."""

    session_type: str = "anonymous"


class SessionInfo(BaseModel):
    """Session information returned by the API."""

    session_id: str
    session_type: str
    created_at: str
    last_active: str
    message_count: int


class SessionDetail(SessionInfo):
    """Session detail including message history."""

    messages: list[dict[str, Any]]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str = "0.1.0"


# --- Application factory ---


def create_app(
    settings: Settings | None = None,
    rag_pipeline: RAGPipeline | None = None,
    audit_logger: AuditLogger | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Uses the factory pattern so tests can create isolated app instances
    with mock dependencies.

    Args:
        settings: Application settings. Defaults to Settings().
        rag_pipeline: Optional pre-built RAGPipeline.
        audit_logger: Optional pre-built AuditLogger.

    Returns:
        A configured FastAPI instance.
    """
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="Munici-Pal Digital Librarian",
        description="AI-powered municipal information assistant",
        version="0.1.0",
    )

    # CORS for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Dependencies
    session_manager = SessionManager()

    if audit_logger is None:
        audit_logger = AuditLogger(config=settings.audit)

    if rag_pipeline is None:
        rag_pipeline = create_rag_pipeline(settings)

    chat_service = ChatService(
        rag_pipeline=rag_pipeline,
        session_manager=session_manager,
        audit_logger=audit_logger,
    )

    # Phase 2: Intake services
    intake_store = IntakeStore()
    validation_engine = ValidationEngine()
    gis_service = MockGISService()
    i18n_engine = I18nEngine()

    try:
        approval_gate = ApprovalGate()
    except Exception:
        approval_gate = None

    wizard_engine = WizardEngine(
        store=intake_store,
        validation_engine=validation_engine,
        audit_logger=audit_logger,
        approval_gate=approval_gate,
    )

    upgrade_service = SessionUpgradeService(
        session_manager=session_manager,
        audit_logger=audit_logger,
    )

    packet_renderer = PacketRenderer()

    # Store on app state for access in route handlers
    app.state.chat_service = chat_service
    app.state.session_manager = session_manager
    app.state.audit_logger = audit_logger
    app.state.feedback_store = FeedbackStore()
    app.state.shadow_manager = ShadowModeManager()
    app.state.intake_store = intake_store
    app.state.wizard_engine = wizard_engine
    app.state.validation_engine = validation_engine
    app.state.gis_service = gis_service
    app.state.i18n_engine = i18n_engine
    app.state.upgrade_service = upgrade_service
    app.state.packet_renderer = packet_renderer

    # Mission Control staff dashboard
    app.include_router(mission_control_router)

    # Phase 2: Intake router
    app.include_router(intake_router)

    # Templates and static files
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    # --- Routes ---

    @app.get("/", response_class=HTMLResponse)
    async def serve_chat_ui(request: Request) -> HTMLResponse:
        """Serve the chat UI page."""
        return templates.TemplateResponse(request, "chat.html")

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(body: ChatRequest) -> ChatResponse:
        """Process a chat message and return the assistant response."""
        try:
            msg = await chat_service.respond(
                session_id=body.session_id,
                user_message=body.message,
            )
        except KeyError:
            raise HTTPException(
                status_code=404,
                detail=f"Session {body.session_id!r} not found",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Internal error: {exc}",
            )

        return ChatResponse(
            response=msg.content,
            citations=msg.citations or [],
            confidence=msg.confidence or 0.0,
            low_confidence=msg.low_confidence or False,
        )

    @app.post("/api/sessions", response_model=SessionInfo)
    async def create_session(body: SessionCreateRequest | None = None) -> SessionInfo:
        """Create a new chat session."""
        session_type_str = body.session_type if body else "anonymous"
        try:
            session_type = SessionType(session_type_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid session type: {session_type_str!r}",
            )

        session = session_manager.create_session(session_type=session_type)
        return SessionInfo(
            session_id=session.session_id,
            session_type=session.session_type.value,
            created_at=session.created_at.isoformat(),
            last_active=session.last_active.isoformat(),
            message_count=0,
        )

    @app.get("/api/sessions/{session_id}", response_model=SessionDetail)
    async def get_session(session_id: str) -> SessionDetail:
        """Get a session with its full message history."""
        session = session_manager.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id!r} not found",
            )

        messages = [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "citations": msg.citations,
                "confidence": msg.confidence,
                "low_confidence": msg.low_confidence,
            }
            for msg in session.messages
        ]

        return SessionDetail(
            session_id=session.session_id,
            session_type=session.session_type.value,
            created_at=session.created_at.isoformat(),
            last_active=session.last_active.isoformat(),
            message_count=len(session.messages),
            messages=messages,
        )

    @app.get("/api/sessions", response_model=list[SessionInfo])
    async def list_sessions() -> list[SessionInfo]:
        """List all active sessions (for Mission Control)."""
        sessions = session_manager.list_active_sessions()
        return [
            SessionInfo(
                session_id=s.session_id,
                session_type=s.session_type.value,
                created_at=s.created_at.isoformat(),
                last_active=s.last_active.isoformat(),
                message_count=len(s.messages),
            )
            for s in sessions
        ]

    @app.get("/api/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(
            status="healthy",
            service="municipal-digital-librarian",
        )

    return app
