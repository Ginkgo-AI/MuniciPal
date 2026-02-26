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

from municipal.auth.middleware import AuthMiddleware
from municipal.auth.provider import MockAuthProvider
from municipal.bridge.adapters.permit_status import MockPermitStatusAdapter
from municipal.bridge.adapters.service311 import Mock311Adapter
from municipal.bridge.registry import AdapterRegistry
from municipal.chat.service import ChatService
from municipal.chat.session import SessionManager
from municipal.core.config import Settings
from municipal.core.types import SessionType
from municipal.export.renderer import PacketRenderer
from municipal.gis.service import MockGISService
from municipal.governance.approval import ApprovalGate
from municipal.governance.audit import AuditLogger
from municipal.graph.store import GraphStore
from municipal.i18n.engine import I18nEngine
from municipal.identity.upgrade import SessionUpgradeService
from municipal.intake.engine import WizardEngine
from municipal.intake.store import IntakeStore
from municipal.intake.validation import ValidationEngine
from municipal.notifications.engine import NotificationEngine
from municipal.notifications.service import MockNotificationService
from municipal.notifications.store import NotificationStore
from municipal.rag.pipeline import RAGPipeline, create_rag_pipeline
from municipal.web.bridge_router import router as bridge_router
from municipal.web.graph_router import router as graph_router
from municipal.web.intake_router import router as intake_router
from municipal.finance.deadlines import DeadlineEngine
from municipal.finance.fees import FeeEngine
from municipal.finance.taxes import TaxEngine
from municipal.llm.registry import ModelRegistry
from municipal.web.finance_router import PaymentStore
from municipal.web.finance_router import router as finance_router
from municipal.web.mission_control import (
    FeedbackStore,
    ShadowComparisonStore,
    ShadowModeManager,
    router as mission_control_router,
)
from municipal.web.mission_control_v1 import (
    LLMLatencyTracker,
    MetricsService,
    SessionTakeoverManager,
)
from municipal.web.notification_router import router as notification_router
from municipal.web.review_router import router as review_router
from municipal.review.redaction import RedactionEngine
from municipal.review.inconsistency import InconsistencyDetector
from municipal.review.summary import SummaryEngine
from municipal.review.sunshine import SunshineReportGenerator

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

    # Phase 5: Shadow + takeover managers (created early for ChatService)
    shadow_manager = ShadowModeManager()
    comparison_store = ShadowComparisonStore()
    takeover_manager = SessionTakeoverManager()

    chat_service = ChatService(
        rag_pipeline=rag_pipeline,
        session_manager=session_manager,
        audit_logger=audit_logger,
        shadow_manager=shadow_manager,
        comparison_store=comparison_store,
        takeover_manager=takeover_manager,
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

    # Phase 3: Graph store + notifications
    graph_store = GraphStore()
    notification_store = NotificationStore()
    notification_service = MockNotificationService(store=notification_store)
    notification_engine = NotificationEngine(
        service=notification_service,
        audit_logger=audit_logger,
    )

    wizard_engine = WizardEngine(
        store=intake_store,
        validation_engine=validation_engine,
        audit_logger=audit_logger,
        approval_gate=approval_gate,
        graph_store=graph_store,
    )

    # Phase 3: Authentication
    auth_provider = MockAuthProvider()

    upgrade_service = SessionUpgradeService(
        session_manager=session_manager,
        audit_logger=audit_logger,
        auth_provider=auth_provider,
    )

    packet_renderer = PacketRenderer()

    # Phase 3: Bridge adapters
    adapter_registry = AdapterRegistry()
    adapter_registry.register(MockPermitStatusAdapter(audit_logger=audit_logger))
    adapter_registry.register(Mock311Adapter(audit_logger=audit_logger))

    # Phase 5: Finance services
    fee_engine = FeeEngine()
    tax_engine = TaxEngine()
    deadline_engine = DeadlineEngine()
    payment_store = PaymentStore()

    # Phase 5: Model registry + LLM latency tracker
    model_registry = ModelRegistry(production=settings.llm)
    llm_tracker = LLMLatencyTracker()

    # Store on app state for access in route handlers
    app.state.chat_service = chat_service
    app.state.session_manager = session_manager
    app.state.audit_logger = audit_logger
    app.state.feedback_store = FeedbackStore()
    app.state.shadow_manager = shadow_manager
    app.state.comparison_store = comparison_store
    app.state.intake_store = intake_store
    app.state.wizard_engine = wizard_engine
    app.state.validation_engine = validation_engine
    app.state.gis_service = gis_service
    app.state.i18n_engine = i18n_engine
    app.state.upgrade_service = upgrade_service
    app.state.packet_renderer = packet_renderer
    app.state.adapter_registry = adapter_registry
    app.state.graph_store = graph_store
    app.state.notification_store = notification_store
    app.state.notification_service = notification_service
    app.state.notification_engine = notification_engine
    app.state.auth_provider = auth_provider
    app.state.approval_gate = approval_gate

    # Phase 3/5: Mission Control v1 services with enhanced metrics
    metrics_service = MetricsService(
        session_manager=session_manager,
        intake_store=intake_store,
        approval_gate=approval_gate,
        adapter_registry=adapter_registry,
        llm_tracker=llm_tracker,
        comparison_store=comparison_store,
    )
    app.state.metrics_service = metrics_service
    app.state.takeover_manager = takeover_manager
    app.state.fee_engine = fee_engine
    app.state.tax_engine = tax_engine
    app.state.deadline_engine = deadline_engine
    app.state.payment_store = payment_store
    app.state.model_registry = model_registry
    app.state.llm_tracker = llm_tracker

    # Phase 4: Review services
    redaction_engine = RedactionEngine()
    inconsistency_detector = InconsistencyDetector()
    summary_engine = SummaryEngine(
        intake_store=intake_store,
        graph_store=graph_store,
        wizard_definitions=wizard_engine.wizard_definitions,
        approval_gate=approval_gate,
    )
    sunshine_generator = SunshineReportGenerator(
        intake_store=intake_store,
        approval_gate=approval_gate,
        notification_store=notification_store,
    )
    app.state.redaction_engine = redaction_engine
    app.state.inconsistency_detector = inconsistency_detector
    app.state.summary_engine = summary_engine
    app.state.sunshine_generator = sunshine_generator

    # Phase 3: Auth middleware
    app.add_middleware(AuthMiddleware)

    # Mission Control staff dashboard
    app.include_router(mission_control_router)

    # Phase 2: Intake router
    app.include_router(intake_router)

    # Phase 3: Bridge, notification, graph routers
    app.include_router(bridge_router)
    app.include_router(notification_router)
    app.include_router(graph_router)

    # Phase 4: Review router
    app.include_router(review_router)

    # Phase 5: Finance router
    app.include_router(finance_router)

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
