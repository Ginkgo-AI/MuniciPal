"""SQLAlchemy ORM models for all persistent tables."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from municipal.db.base import Base


def _jsonb() -> type:
    """Return JSONB for Postgres, plain JSON for SQLite."""
    return JSON().with_variant(PG_JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Sessions & Messages
# ---------------------------------------------------------------------------


class SessionRow(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_type: Mapped[str] = mapped_column(String(32), default="anonymous")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    taken_over_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    messages: Mapped[list[MessageRow]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="MessageRow.timestamp"
    )

    __table_args__ = (
        Index("ix_sessions_last_active", "last_active"),
    )


class MessageRow(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.session_id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    citations: Mapped[dict | None] = mapped_column(_jsonb(), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_confidence: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    session: Mapped[SessionRow] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_messages_session_id", "session_id"),
    )


# ---------------------------------------------------------------------------
# Intake: Wizard States & Cases
# ---------------------------------------------------------------------------


class WizardStateRow(Base):
    __tablename__ = "wizard_states"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    wizard_id: Mapped[str] = mapped_column(String(128))
    session_id: Mapped[str] = mapped_column(String(64))
    current_step_index: Mapped[int] = mapped_column(Integer, default=0)
    steps: Mapped[list] = mapped_column(_jsonb(), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


class CaseRow(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    wizard_id: Mapped[str] = mapped_column(String(128))
    session_id: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict] = mapped_column(_jsonb(), default=dict)
    classification: Mapped[str] = mapped_column(String(32), default="public")
    approval_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    status: Mapped[str] = mapped_column(String(32), default="submitted")

    __table_args__ = (
        Index("ix_cases_session_id", "session_id"),
        Index("ix_cases_wizard_id", "wizard_id"),
    )


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------


class ApprovalRequestRow(Base):
    __tablename__ = "approval_requests"

    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    gate_type: Mapped[str] = mapped_column(String(64))
    resource: Mapped[str] = mapped_column(Text)
    requestor: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    approver: Mapped[str | None] = mapped_column(String(128), nullable=True)
    deny_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approvals: Mapped[list] = mapped_column(_jsonb(), default=list)


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


class GraphNodeRow(Base):
    __tablename__ = "graph_nodes"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(256), default="")
    properties: Mapped[dict] = mapped_column(_jsonb(), default=dict)


class GraphEdgeRow(Base):
    __tablename__ = "graph_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(128))
    target_id: Mapped[str] = mapped_column(String(128))
    relationship: Mapped[str] = mapped_column(String(32))
    properties: Mapped[dict] = mapped_column(_jsonb(), default=dict)

    __table_args__ = (
        Index("ix_graph_edges_source", "source_id"),
        Index("ix_graph_edges_target", "target_id"),
    )


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class NotificationRow(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), default="")
    channel: Mapped[str] = mapped_column(String(16), default="email")
    recipient: Mapped[str] = mapped_column(String(256), default="")
    subject: Mapped[str] = mapped_column(String(512), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    template_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", _jsonb(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_notifications_session_id", "session_id"),
    )


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


class FeedbackEntryRow(Base):
    __tablename__ = "feedback_entries"

    feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    staff_id: Mapped[str] = mapped_column(String(128), default="staff")
    session_id: Mapped[str] = mapped_column(String(64))
    message_index: Mapped[int] = mapped_column(Integer)
    flag_type: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(Text, default="")


# ---------------------------------------------------------------------------
# Shadow Comparisons
# ---------------------------------------------------------------------------


class ShadowComparisonRow(Base):
    __tablename__ = "shadow_comparisons"

    comparison_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64))
    user_message: Mapped[str] = mapped_column(Text)
    production_response: Mapped[str] = mapped_column(Text)
    candidate_response: Mapped[str] = mapped_column(Text)
    diverged: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


class PaymentRecordRow(Base):
    __tablename__ = "payment_records"

    payment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(64))
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    approval_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    classification: Mapped[str] = mapped_column(String(32), default="restricted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_payment_records_case_id", "case_id"),
    )


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    session_id: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(128))
    resource: Mapped[str] = mapped_column(Text)
    classification: Mapped[str] = mapped_column(String(32))
    details: Mapped[dict] = mapped_column(_jsonb(), default=dict)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_calls: Mapped[list] = mapped_column(_jsonb(), default=list)
    data_sources: Mapped[list] = mapped_column(_jsonb(), default=list)
    approval_chain: Mapped[list] = mapped_column(_jsonb(), default=list)
    previous_hash: Mapped[str] = mapped_column(String(128), default="")
    entry_hash: Mapped[str] = mapped_column(String(128), default="")

    __table_args__ = (
        Index("ix_audit_events_session_id", "session_id"),
        Index("ix_audit_events_timestamp", "timestamp"),
    )


# ---------------------------------------------------------------------------
# Auth Tokens
# ---------------------------------------------------------------------------


class AuthTokenRow(Base):
    __tablename__ = "auth_tokens"

    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128))
    tier: Mapped[str] = mapped_column(String(32))
    display_name: Mapped[str] = mapped_column(String(256), default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_auth_tokens_expires_at", "expires_at"),
    )
