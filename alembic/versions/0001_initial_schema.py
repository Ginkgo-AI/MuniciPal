"""Initial schema — all 13 tables.

Revision ID: 0001
Revises:
Create Date: 2026-02-26

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Sessions --
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(64), primary_key=True),
        sa.Column("session_type", sa.String(32), server_default="anonymous"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=False),
        sa.Column("taken_over_by", sa.String(128), nullable=True),
    )
    op.create_index("ix_sessions_last_active", "sessions", ["last_active"])

    # -- Messages --
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(64),
            sa.ForeignKey("sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("citations", sa.JSON, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("low_confidence", sa.Boolean, nullable=True),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])

    # -- Wizard States --
    op.create_table(
        "wizard_states",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("wizard_id", sa.String(128), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("current_step_index", sa.Integer, server_default="0"),
        sa.Column("steps", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed", sa.Boolean, server_default="false"),
    )

    # -- Cases --
    op.create_table(
        "cases",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("wizard_id", sa.String(128), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("classification", sa.String(32), server_default="public"),
        sa.Column("approval_request_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), server_default="submitted"),
    )
    op.create_index("ix_cases_session_id", "cases", ["session_id"])
    op.create_index("ix_cases_wizard_id", "cases", ["wizard_id"])

    # -- Approval Requests --
    op.create_table(
        "approval_requests",
        sa.Column("request_id", sa.String(64), primary_key=True),
        sa.Column("gate_type", sa.String(64), nullable=False),
        sa.Column("resource", sa.Text, nullable=False),
        sa.Column("requestor", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approver", sa.String(128), nullable=True),
        sa.Column("deny_reason", sa.Text, nullable=True),
        sa.Column("approvals", sa.JSON, nullable=False),
    )

    # -- Graph Nodes --
    op.create_table(
        "graph_nodes",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("label", sa.String(256), server_default=""),
        sa.Column("properties", sa.JSON, nullable=False),
    )

    # -- Graph Edges --
    op.create_table(
        "graph_edges",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("target_id", sa.String(128), nullable=False),
        sa.Column("relationship", sa.String(32), nullable=False),
        sa.Column("properties", sa.JSON, nullable=False),
    )
    op.create_index("ix_graph_edges_source", "graph_edges", ["source_id"])
    op.create_index("ix_graph_edges_target", "graph_edges", ["target_id"])

    # -- Notifications --
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), server_default=""),
        sa.Column("channel", sa.String(16), server_default="email"),
        sa.Column("recipient", sa.String(256), server_default=""),
        sa.Column("subject", sa.String(512), server_default=""),
        sa.Column("body", sa.Text, server_default=""),
        sa.Column("status", sa.String(16), server_default="pending"),
        sa.Column("priority", sa.String(16), server_default="normal"),
        sa.Column("template_id", sa.String(128), nullable=True),
        sa.Column("metadata", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notifications_session_id", "notifications", ["session_id"])

    # -- Feedback Entries --
    op.create_table(
        "feedback_entries",
        sa.Column("feedback_id", sa.String(64), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("staff_id", sa.String(128), server_default="staff"),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("message_index", sa.Integer, nullable=False),
        sa.Column("flag_type", sa.String(32), nullable=False),
        sa.Column("note", sa.Text, server_default=""),
    )

    # -- Shadow Comparisons --
    op.create_table(
        "shadow_comparisons",
        sa.Column("comparison_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("user_message", sa.Text, nullable=False),
        sa.Column("production_response", sa.Text, nullable=False),
        sa.Column("candidate_response", sa.Text, nullable=False),
        sa.Column("diverged", sa.Boolean, server_default="false"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )

    # -- Payment Records --
    op.create_table(
        "payment_records",
        sa.Column("payment_id", sa.String(64), primary_key=True),
        sa.Column("case_id", sa.String(64), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("approval_request_id", sa.String(64), nullable=True),
        sa.Column("classification", sa.String(32), server_default="restricted"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payment_records_case_id", "payment_records", ["case_id"])

    # -- Audit Events --
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource", sa.Text, nullable=False),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("details", sa.JSON, nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("tool_calls", sa.JSON, nullable=False),
        sa.Column("data_sources", sa.JSON, nullable=False),
        sa.Column("approval_chain", sa.JSON, nullable=False),
        sa.Column("previous_hash", sa.String(128), nullable=False),
        sa.Column("entry_hash", sa.String(128), nullable=False),
    )
    op.create_index("ix_audit_events_session_id", "audit_events", ["session_id"])
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"])

    # -- Auth Tokens --
    op.create_table(
        "auth_tokens",
        sa.Column("token", sa.String(128), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("tier", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(256), server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_tokens_expires_at", "auth_tokens", ["expires_at"])

    # Optional extensions (created if available, not required)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgvector"))
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis"))


def downgrade() -> None:
    op.drop_table("auth_tokens")
    op.drop_table("audit_events")
    op.drop_table("payment_records")
    op.drop_table("shadow_comparisons")
    op.drop_table("feedback_entries")
    op.drop_table("notifications")
    op.drop_table("graph_edges")
    op.drop_table("graph_nodes")
    op.drop_table("approval_requests")
    op.drop_table("cases")
    op.drop_table("wizard_states")
    op.drop_table("messages")
    op.drop_table("sessions")
