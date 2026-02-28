"""Shared models for the intake wizard system."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from municipal.core.types import DataClassification, SessionType


class FieldType(str, Enum):
    """Supported field types in wizard steps."""

    TEXT = "text"
    TEXTAREA = "textarea"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    NUMBER = "number"
    SELECT = "select"
    CHECKBOX = "checkbox"
    ADDRESS = "address"
    FILE = "file"


class StepStatus(str, Enum):
    """Status of a wizard step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class FieldDefinition(BaseModel):
    """Definition of a single form field within a wizard step."""

    id: str
    label: str
    field_type: FieldType
    required: bool = False
    validators: list[str] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)
    placeholder: str = ""
    help_text: str = ""
    classification: DataClassification = DataClassification.PUBLIC
    show_if: dict[str, Any] | None = None


class StepDefinition(BaseModel):
    """Definition of a single wizard step."""

    id: str
    title: str
    description: str = ""
    fields: list[FieldDefinition] = Field(default_factory=list)
    required_session_tier: SessionType = SessionType.ANONYMOUS
    show_if: dict[str, Any] | None = None


class WizardDefinition(BaseModel):
    """Full definition of a wizard loaded from YAML."""

    id: str
    title: str
    description: str = ""
    steps: list[StepDefinition] = Field(default_factory=list)
    approval_gate: str | None = None
    classification: DataClassification = DataClassification.PUBLIC


class ValidationResult(BaseModel):
    """Result of validating a field or step."""

    valid: bool
    errors: dict[str, list[str]] = Field(default_factory=dict)


class StepState(BaseModel):
    """Runtime state of a single wizard step."""

    step_id: str
    status: StepStatus = StepStatus.PENDING
    data: dict[str, Any] = Field(default_factory=dict)
    errors: dict[str, list[str]] = Field(default_factory=dict)


class WizardState(BaseModel):
    """Runtime state of a wizard instance."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    wizard_id: str
    session_id: str
    current_step_index: int = 0
    steps: list[StepState] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed: bool = False


class Case(BaseModel):
    """A submitted case created from a completed wizard."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    wizard_id: str
    session_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    classification: DataClassification = DataClassification.PUBLIC
    approval_request_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "submitted"
