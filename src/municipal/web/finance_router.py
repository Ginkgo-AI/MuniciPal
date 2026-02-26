"""Finance API router for fee estimation, payments, and deadlines."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from municipal.finance.models import PaymentRecord, PaymentStatus


router = APIRouter()


# ---------------------------------------------------------------------------
# In-memory payment store
# ---------------------------------------------------------------------------


class PaymentStore:
    """In-memory store for payment records."""

    def __init__(self) -> None:
        self._payments: dict[str, PaymentRecord] = {}

    def save(self, record: PaymentRecord) -> PaymentRecord:
        self._payments[record.payment_id] = record
        return record

    def get(self, payment_id: str) -> PaymentRecord | None:
        return self._payments.get(payment_id)

    def get_for_case(self, case_id: str) -> list[PaymentRecord]:
        return [p for p in self._payments.values() if p.case_id == case_id]

    def list_all(self) -> list[PaymentRecord]:
        return list(self._payments.values())


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class FeeEstimateRequest(BaseModel):
    """Request body for fee estimation."""

    case_id: str | None = None
    wizard_type: str
    data: dict[str, Any] = Field(default_factory=dict)


class PaymentInitiateRequest(BaseModel):
    """Request body for initiating a payment."""

    amount: float
    requestor: str = "resident"


# ---------------------------------------------------------------------------
# Helper to get services from app state
# ---------------------------------------------------------------------------


def _get_fee_engine(request: Request):
    engine = getattr(request.app.state, "fee_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Fee engine not available")
    return engine


def _get_tax_engine(request: Request):
    engine = getattr(request.app.state, "tax_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Tax engine not available")
    return engine


def _get_deadline_engine(request: Request):
    engine = getattr(request.app.state, "deadline_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Deadline engine not available")
    return engine


def _get_payment_store(request: Request):
    store = getattr(request.app.state, "payment_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Payment store not available")
    return store


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/api/finance/schedule")
async def api_list_schedules(request: Request) -> dict[str, Any]:
    """List all fee schedules."""
    fee_engine = _get_fee_engine(request)
    schedules = fee_engine.list_schedules()
    return {
        str(wizard_type): [entry.model_dump() for entry in entries]
        for wizard_type, entries in schedules.items()
    }


@router.get("/api/finance/schedule/{wizard_type}")
async def api_get_schedule(wizard_type: str, request: Request) -> list[dict[str, Any]]:
    """Get fee schedule for a specific wizard type."""
    fee_engine = _get_fee_engine(request)
    entries = fee_engine.get_schedule(wizard_type)
    if not entries:
        raise HTTPException(status_code=404, detail=f"No fee schedule for {wizard_type!r}")
    return [entry.model_dump() for entry in entries]


@router.post("/api/finance/estimate")
async def api_compute_estimate(
    body: FeeEstimateRequest, request: Request
) -> dict[str, Any]:
    """Compute a fee estimate for a wizard submission."""
    fee_engine = _get_fee_engine(request)
    try:
        estimate = fee_engine.compute(body.wizard_type, body.data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if body.case_id:
        estimate.case_id = body.case_id

    return estimate.model_dump(mode="json")


@router.get("/api/finance/deadline/{case_id}")
async def api_get_deadline(case_id: str, request: Request) -> dict[str, Any]:
    """Compute the deadline for a case."""
    deadline_engine = _get_deadline_engine(request)
    intake_store = getattr(request.app.state, "intake_store", None)

    if intake_store is None:
        raise HTTPException(status_code=503, detail="Intake store not available")

    case = intake_store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found")

    try:
        deadline = deadline_engine.compute(
            case_id=case_id,
            wizard_type=case.wizard_id,
            submitted_at=case.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return deadline.model_dump(mode="json")


@router.post("/api/finance/payment/{case_id}")
async def api_initiate_payment(
    case_id: str, body: PaymentInitiateRequest, request: Request
) -> dict[str, Any]:
    """Initiate a payment for a case, triggering the payment_refund approval gate."""
    payment_store = _get_payment_store(request)
    approval_gate = getattr(request.app.state, "approval_gate", None)

    if approval_gate is None:
        raise HTTPException(status_code=503, detail="Approval gate not available")

    # Create approval request via payment_refund gate
    try:
        approval_req = approval_gate.request_approval(
            gate_type="payment_refund",
            resource=f"payment:case:{case_id}",
            requestor=body.requestor,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    record = PaymentRecord(
        case_id=case_id,
        amount=body.amount,
        status=PaymentStatus.AWAITING_APPROVAL,
        approval_request_id=approval_req.request_id,
    )
    payment_store.save(record)

    return {
        "payment_id": record.payment_id,
        "case_id": record.case_id,
        "amount": record.amount,
        "status": record.status.value,
        "approval_request_id": record.approval_request_id,
        "created_at": record.created_at.isoformat(),
    }


@router.get("/api/finance/payment/{payment_id}")
async def api_get_payment(payment_id: str, request: Request) -> dict[str, Any]:
    """Get payment status."""
    payment_store = _get_payment_store(request)
    record = payment_store.get(payment_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id!r} not found")

    return {
        "payment_id": record.payment_id,
        "case_id": record.case_id,
        "amount": record.amount,
        "status": record.status.value,
        "approval_request_id": record.approval_request_id,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }
