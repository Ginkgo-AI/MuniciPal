"""Data models for the review module."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RedactionSuggestion(BaseModel):
    """A single redaction suggestion for a field value."""

    field_id: str
    value_snippet: str
    reason: str
    confidence: Confidence
    classification: str


class RedactionReport(BaseModel):
    """Report of all redaction suggestions for a case."""

    case_id: str
    suggestions: list[RedactionSuggestion] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InconsistencyFinding(BaseModel):
    """A single inconsistency found in case data."""

    check_type: str
    fields: list[str]
    message: str
    severity: str = "warning"


class InconsistencyReport(BaseModel):
    """Report of all inconsistencies found in a case."""

    case_id: str
    findings: list[InconsistencyFinding] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CaseSummary(BaseModel):
    """Structured summary of a case for staff review."""

    case_id: str
    wizard_id: str
    wizard_title: str
    status: str
    classification: str
    created_at: str
    key_facts: dict[str, Any] = Field(default_factory=dict)
    timeline: list[dict[str, str]] = Field(default_factory=list)
    related_entities: list[dict[str, str]] = Field(default_factory=list)
    approval_status: str | None = None


class DepartmentReport(BaseModel):
    """Aggregate report for a department/wizard type."""

    wizard_type: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    total_cases: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    by_classification: dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SunshineReportData(BaseModel):
    """Annual transparency / Sunshine Report data."""

    title: str = "Annual Sunshine Report"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_cases: int = 0
    cases_by_type: dict[str, int] = Field(default_factory=dict)
    cases_by_status: dict[str, int] = Field(default_factory=dict)
    approval_stats: dict[str, Any] = Field(default_factory=dict)
    foia_metrics: dict[str, Any] = Field(default_factory=dict)
    service_311_stats: dict[str, Any] = Field(default_factory=dict)
    notification_summary: dict[str, Any] = Field(default_factory=dict)
