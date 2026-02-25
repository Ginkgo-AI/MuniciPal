"""Core type definitions shared across all Munici-Pal modules."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DataClassification(StrEnum):
    """Data classification levels per REFERENCE.md Section 3."""

    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class SessionType(StrEnum):
    """Resident session types per ROADMAP.md Section 1.3."""

    ANONYMOUS = "anonymous"
    VERIFIED = "verified"
    AUTHENTICATED = "authenticated"


class ApprovalStatus(StrEnum):
    """Status of an approval gate request."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class AuditEvent(BaseModel):
    """Immutable audit log entry per ROADMAP.md Section 6.4."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str
    actor: str
    action: str
    resource: str
    classification: DataClassification
    details: dict[str, Any] = Field(default_factory=dict)
    prompt_version: str | None = None
    tool_calls: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    approval_chain: list[str] = Field(default_factory=list)


class HealthStatus(BaseModel):
    """Health check response for any service."""

    service: str
    healthy: bool
    latency_ms: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """Tool registry entry per REFERENCE.md Section 6."""

    id: str
    name: str
    description: str
    version: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    required_roles: list[str] = Field(default_factory=list)
    classification_max: DataClassification = DataClassification.PUBLIC
    approval_required: bool = False
    approval_roles: list[str] = Field(default_factory=list)
    dry_run_supported: bool = False
    idempotent: bool = False
    rate_limit: int | None = None
    timeout_ms: int = 10_000
    log_input: bool = True
    log_output: bool = True
    redact_fields: list[str] = Field(default_factory=list)


class EvalEntry(BaseModel):
    """Golden dataset entry per REFERENCE.md Section 8.1."""

    id: str
    department: str
    category: str
    question: str
    expected_answer: str
    expected_sources: list[str] = Field(default_factory=list)
    difficulty: str = "medium"
    last_verified: str | None = None


class EvalResult(BaseModel):
    """Result of evaluating a single golden dataset entry."""

    entry_id: str
    question: str
    generated_answer: str
    expected_answer: str
    cited_sources: list[str] = Field(default_factory=list)
    expected_sources: list[str] = Field(default_factory=list)
    answer_accurate: bool = False
    citation_precision: float = 0.0
    citation_recall: float = 0.0
    contains_hallucination: bool = False
    correctly_refused: bool = False
    latency_ms: float = 0.0
