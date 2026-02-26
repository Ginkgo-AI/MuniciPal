"""Tests for TaxEngine and DeadlineEngine (WP2)."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from municipal.finance.deadlines import DeadlineEngine
from municipal.finance.models import DataClassification, DeadlineInfo, TaxEstimate
from municipal.finance.taxes import TaxEngine


# ---------------------------------------------------------------------------
# TaxEngine tests
# ---------------------------------------------------------------------------


@pytest.fixture
def tax_engine():
    return TaxEngine()


class TestTaxEngine:
    def test_residential_rate(self, tax_engine):
        est = tax_engine.estimate_annual_tax("residential", 250_000.0)
        assert est.effective_rate == 1.25
        assert est.annual_tax == 3125.0
        assert est.property_type == "residential"
        assert est.assessed_value == 250_000.0

    def test_commercial_rate(self, tax_engine):
        est = tax_engine.estimate_annual_tax("commercial", 500_000.0)
        assert est.effective_rate == 2.20
        assert est.annual_tax == 11_000.0

    def test_industrial_rate(self, tax_engine):
        est = tax_engine.estimate_annual_tax("industrial", 1_000_000.0)
        assert est.effective_rate == 1.75
        assert est.annual_tax == 17_500.0

    def test_mixed_use_rate(self, tax_engine):
        est = tax_engine.estimate_annual_tax("mixed use", 400_000.0)
        assert est.effective_rate == 1.65
        assert est.annual_tax == 6_600.0

    def test_case_insensitive(self, tax_engine):
        est = tax_engine.estimate_annual_tax("Residential", 100_000.0)
        assert est.annual_tax == 1_250.0

    def test_unknown_property_type(self, tax_engine):
        with pytest.raises(ValueError, match="Unknown property type"):
            tax_engine.estimate_annual_tax("agricultural", 100_000.0)

    def test_classification_restricted(self, tax_engine):
        est = tax_engine.estimate_annual_tax("residential", 100_000.0)
        assert est.classification == DataClassification.RESTRICTED

    def test_custom_rates(self):
        engine = TaxEngine(rates={"farm": 0.5})
        est = engine.estimate_annual_tax("farm", 200_000.0)
        assert est.annual_tax == 1_000.0

    def test_rates_property(self, tax_engine):
        rates = tax_engine.rates
        assert "residential" in rates
        assert "commercial" in rates


# ---------------------------------------------------------------------------
# DeadlineEngine tests
# ---------------------------------------------------------------------------


@pytest.fixture
def deadline_engine():
    return DeadlineEngine()


class TestDeadlineEngine:
    def test_permit_30_business_days(self, deadline_engine):
        # Monday 2026-01-05
        submitted = datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc)
        info = deadline_engine.compute("case-1", "permit", submitted)
        assert info.statutory_days == 30
        assert info.business_days_only is True
        # 30 business days from Monday Jan 5 = Feb 16 (Mon)
        assert info.due_date == date(2026, 2, 16)

    def test_foia_5_business_days(self, deadline_engine):
        # Monday 2026-03-02
        submitted = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
        info = deadline_engine.compute("case-2", "foia", submitted)
        assert info.statutory_days == 5
        assert info.business_days_only is True
        # 5 business days from Mon Mar 2 = Mon Mar 9
        assert info.due_date == date(2026, 3, 9)

    def test_311_14_calendar_days(self, deadline_engine):
        submitted = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
        info = deadline_engine.compute("case-3", "311", submitted)
        assert info.statutory_days == 14
        assert info.business_days_only is False
        assert info.due_date == date(2026, 6, 15)

    def test_unknown_wizard_type(self, deadline_engine):
        submitted = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="No deadline rule"):
            deadline_engine.compute("case-x", "unknown", submitted)

    def test_add_business_days_skips_weekends(self):
        # Friday Jan 2 2026
        start = date(2026, 1, 2)
        result = DeadlineEngine._add_business_days(start, 3)
        # Fri -> Mon -> Tue -> Wed = Jan 7
        assert result == date(2026, 1, 7)

    def test_add_business_days_from_saturday(self):
        start = date(2026, 1, 3)  # Saturday
        result = DeadlineEngine._add_business_days(start, 1)
        # Sat -> Sun (skip) -> Mon = Jan 5
        assert result == date(2026, 1, 5)

    def test_get_rules(self, deadline_engine):
        rules = deadline_engine.get_rules()
        assert "permit" in rules
        assert "foia" in rules
        assert "311" in rules
