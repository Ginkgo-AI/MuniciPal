"""Finance data models for fee estimation, payments, deadlines, and taxes."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from municipal.core.types import DataClassification


class PaymentStatus(StrEnum):
    """Status of a payment transaction."""

    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    COMPLETED = "completed"
    DENIED = "denied"
    REFUNDED = "refunded"


class FeeLineItem(BaseModel):
    """A single line item in a fee estimate."""

    description: str
    amount: float
    quantity: float = 1.0
    subtotal: float = 0.0

    def model_post_init(self, __context: Any) -> None:
        if self.subtotal == 0.0:
            self.subtotal = round(self.amount * self.quantity, 2)


class FeeEstimate(BaseModel):
    """Complete fee estimate for a case or wizard submission."""

    case_id: str | None = None
    wizard_type: str
    line_items: list[FeeLineItem] = Field(default_factory=list)
    total: float = 0.0
    classification: DataClassification = DataClassification.RESTRICTED
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_post_init(self, __context: Any) -> None:
        if self.total == 0.0 and self.line_items:
            self.total = round(sum(item.subtotal for item in self.line_items), 2)


class FeeScheduleEntry(BaseModel):
    """A single entry in a fee schedule."""

    name: str
    description: str = ""
    base_fee: float = 0.0
    per_unit_fee: float = 0.0
    unit_label: str = ""
    free_units: int = 0


class PaymentRecord(BaseModel):
    """Record of a payment transaction."""

    payment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    amount: float
    status: PaymentStatus = PaymentStatus.PENDING
    approval_request_id: str | None = None
    classification: DataClassification = DataClassification.RESTRICTED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeadlineInfo(BaseModel):
    """Computed deadline for a case."""

    case_id: str
    wizard_type: str
    statutory_days: int
    business_days_only: bool
    submitted_at: datetime
    due_date: date


class TaxEstimate(BaseModel):
    """Property tax estimate."""

    property_type: str
    assessed_value: float
    annual_tax: float
    effective_rate: float
    classification: DataClassification = DataClassification.RESTRICTED
