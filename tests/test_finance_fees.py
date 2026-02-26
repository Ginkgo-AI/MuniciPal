"""Tests for the Finance/Fee engine (WP1)."""

from __future__ import annotations

import pytest

from municipal.finance.fees import FeeEngine
from municipal.finance.models import (
    DataClassification,
    FeeEstimate,
    FeeLineItem,
    FeeScheduleEntry,
)


@pytest.fixture
def fee_engine():
    return FeeEngine()


class TestFeeLineItem:
    def test_subtotal_auto_calculated(self):
        item = FeeLineItem(description="Test", amount=10.0, quantity=3.0)
        assert item.subtotal == 30.0

    def test_subtotal_single_quantity(self):
        item = FeeLineItem(description="Flat", amount=200.0)
        assert item.subtotal == 200.0


class TestFeeEstimate:
    def test_total_auto_calculated(self):
        items = [
            FeeLineItem(description="A", amount=100.0),
            FeeLineItem(description="B", amount=50.0, quantity=2.0),
        ]
        est = FeeEstimate(wizard_type="permit", line_items=items)
        assert est.total == 200.0

    def test_classification_is_restricted(self):
        est = FeeEstimate(wizard_type="permit")
        assert est.classification == DataClassification.RESTRICTED


class TestFeeEngine:
    def test_load_schedules(self, fee_engine):
        schedules = fee_engine.list_schedules()
        assert "permit" in schedules
        assert "foia" in schedules
        assert "311" in schedules

    def test_get_schedule_permit(self, fee_engine):
        entries = fee_engine.get_schedule("permit")
        assert len(entries) > 0
        names = [e.name for e in entries]
        assert "Building" in names
        assert "Electrical" in names

    def test_get_schedule_empty(self, fee_engine):
        entries = fee_engine.get_schedule("nonexistent")
        assert entries == []

    def test_compute_permit_fee_building(self, fee_engine):
        est = fee_engine.compute_permit_fee(
            permit_type="Building", area_sqft=1000.0
        )
        assert est.wizard_type == "permit"
        assert len(est.line_items) == 2  # base + per-sqft
        assert est.line_items[0].subtotal == 200.0
        assert est.line_items[1].subtotal == 100.0  # 0.10 * 1000
        assert est.total == 300.0

    def test_compute_permit_fee_electrical_flat(self, fee_engine):
        est = fee_engine.compute_permit_fee(permit_type="Electrical")
        assert len(est.line_items) == 1
        assert est.total == 150.0

    def test_compute_foia_fee_under_free(self, fee_engine):
        est = fee_engine.compute_foia_fee(page_count=30)
        assert est.total == 0.0

    def test_compute_foia_fee_over_free(self, fee_engine):
        est = fee_engine.compute_foia_fee(page_count=100)
        # 100 - 50 free = 50 billable @ $0.15
        assert est.total == 7.5

    def test_compute_311_free(self, fee_engine):
        est = fee_engine.compute_311_fee()
        assert est.total == 0.0

    def test_compute_dispatch_permit(self, fee_engine):
        est = fee_engine.compute("permit", {"permit_type": "Building", "area_sqft": 500})
        assert est.wizard_type == "permit"
        assert est.total == 250.0  # 200 + 0.10*500

    def test_compute_dispatch_foia(self, fee_engine):
        est = fee_engine.compute("foia", {"page_count": 60})
        assert est.total == 1.5  # 10 pages * 0.15

    def test_compute_dispatch_unknown_raises(self, fee_engine):
        with pytest.raises(ValueError, match="Unknown wizard type"):
            fee_engine.compute("unknown_type", {})
