"""Tests for finance PDF rendering (WP3)."""

from __future__ import annotations

import pytest

from municipal.export.renderer import PacketRenderer
from municipal.finance.models import (
    FeeEstimate,
    FeeLineItem,
    PaymentRecord,
    PaymentStatus,
)


@pytest.fixture
def renderer():
    return PacketRenderer()


class TestFeeEstimatePDF:
    def test_renders_pdf_bytes(self, renderer):
        estimate = FeeEstimate(
            case_id="case-pdf-1",
            wizard_type="permit",
            line_items=[
                FeeLineItem(description="Building permit - base fee", amount=200.0),
                FeeLineItem(description="Per sqft", amount=0.10, quantity=1000.0),
            ],
        )
        result = renderer.render_fee_estimate_pdf(estimate)
        assert isinstance(result, (bytes, bytearray))
        assert len(result) > 0
        # PDF starts with %PDF
        assert bytes(result[:4]) == b"%PDF"

    def test_renders_without_case_id(self, renderer):
        estimate = FeeEstimate(
            wizard_type="foia",
            line_items=[FeeLineItem(description="FOIA copies", amount=7.5)],
        )
        result = renderer.render_fee_estimate_pdf(estimate)
        assert isinstance(result, (bytes, bytearray))
        assert len(result) > 0


class TestPaymentReceiptPDF:
    def test_renders_pdf_bytes(self, renderer):
        record = PaymentRecord(
            case_id="case-pdf-2",
            amount=300.0,
            status=PaymentStatus.COMPLETED,
            approval_request_id="apr-123",
        )
        result = renderer.render_payment_receipt_pdf(record)
        assert isinstance(result, (bytes, bytearray))
        assert bytes(result[:4]) == b"%PDF"

    def test_renders_without_approval_id(self, renderer):
        record = PaymentRecord(
            case_id="case-pdf-3",
            amount=0.0,
            status=PaymentStatus.PENDING,
        )
        result = renderer.render_payment_receipt_pdf(record)
        assert isinstance(result, (bytes, bytearray))

    def test_renders_refunded_status(self, renderer):
        record = PaymentRecord(
            case_id="case-pdf-4",
            amount=150.0,
            status=PaymentStatus.REFUNDED,
        )
        result = renderer.render_payment_receipt_pdf(record)
        assert isinstance(result, (bytes, bytearray))
        assert len(result) > 0
