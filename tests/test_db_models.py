"""Tests for WP2: SQLAlchemy ORM model definitions."""

from __future__ import annotations

from municipal.db.base import Base
from municipal.db.models import (
    ApprovalRequestRow,
    AuditEventRow,
    AuthTokenRow,
    CaseRow,
    FeedbackEntryRow,
    GraphEdgeRow,
    GraphNodeRow,
    MessageRow,
    NotificationRow,
    PaymentRecordRow,
    SessionRow,
    ShadowComparisonRow,
    WizardStateRow,
)


EXPECTED_TABLES = {
    "sessions",
    "messages",
    "wizard_states",
    "cases",
    "approval_requests",
    "graph_nodes",
    "graph_edges",
    "notifications",
    "feedback_entries",
    "shadow_comparisons",
    "payment_records",
    "audit_events",
    "auth_tokens",
}


def test_all_tables_registered():
    """All 13 tables should be registered in Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    assert EXPECTED_TABLES == table_names


def test_model_classes_importable():
    """All ORM model classes should be importable."""
    models = [
        SessionRow,
        MessageRow,
        WizardStateRow,
        CaseRow,
        ApprovalRequestRow,
        GraphNodeRow,
        GraphEdgeRow,
        NotificationRow,
        FeedbackEntryRow,
        ShadowComparisonRow,
        PaymentRecordRow,
        AuditEventRow,
        AuthTokenRow,
    ]
    assert len(models) == 13


def test_session_has_messages_relationship():
    """SessionRow should have a messages relationship."""
    mapper = SessionRow.__mapper__
    assert "messages" in mapper.relationships


def test_indexes_exist():
    """Key indexes should be defined."""
    tables = Base.metadata.tables
    session_indexes = {idx.name for idx in tables["sessions"].indexes}
    assert "ix_sessions_last_active" in session_indexes

    msg_indexes = {idx.name for idx in tables["messages"].indexes}
    assert "ix_messages_session_id" in msg_indexes

    case_indexes = {idx.name for idx in tables["cases"].indexes}
    assert "ix_cases_session_id" in case_indexes
    assert "ix_cases_wizard_id" in case_indexes

    audit_indexes = {idx.name for idx in tables["audit_events"].indexes}
    assert "ix_audit_events_session_id" in audit_indexes
    assert "ix_audit_events_timestamp" in audit_indexes

    payment_indexes = {idx.name for idx in tables["payment_records"].indexes}
    assert "ix_payment_records_case_id" in payment_indexes

    notif_indexes = {idx.name for idx in tables["notifications"].indexes}
    assert "ix_notifications_session_id" in notif_indexes

    token_indexes = {idx.name for idx in tables["auth_tokens"].indexes}
    assert "ix_auth_tokens_expires_at" in token_indexes
