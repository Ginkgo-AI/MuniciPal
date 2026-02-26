"""Tests for inconsistency detection (Phase 4 — WP3)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
import yaml

from municipal.review.inconsistency import InconsistencyDetector


# --- Fixtures ---


@pytest.fixture
def rules_path(tmp_path):
    config = {
        "wizards": {
            "test_wizard": [
                {
                    "type": "value_range",
                    "field": "cost",
                    "context_field": "type",
                    "context_value": "Residential",
                    "max_value": 500000,
                    "message": "Cost too high for residential.",
                    "severity": "warning",
                },
                {
                    "type": "temporal_logic",
                    "field": "start_date",
                    "expected": "future",
                    "message": "Start date should be in the future.",
                },
                {
                    "type": "cross_reference",
                    "field": "parcel_id",
                    "reference_field": "type",
                    "reference_value": "Commercial",
                    "expected_pattern": r"^COM-",
                    "message": "Commercial parcels should start with COM-.",
                },
                {
                    "type": "completeness",
                    "required_fields": ["name", "email"],
                    "message": "Missing required fields.",
                    "severity": "info",
                },
            ],
        }
    }
    path = tmp_path / "inconsistency_rules.yml"
    with open(path, "w") as fh:
        yaml.dump(config, fh)
    return path


@pytest.fixture
def detector(rules_path):
    return InconsistencyDetector(config_path=rules_path)


# --- Value range checks ---


class TestValueRange:
    def test_cost_within_range(self, detector):
        data = {"cost": "100000", "type": "Residential"}
        report = detector.detect("c1", "test_wizard", data)
        assert len(report.findings) == 0 or not any(
            f.check_type == "value_range" for f in report.findings
        )

    def test_cost_exceeds_range(self, detector):
        data = {"cost": "600000", "type": "Residential"}
        report = detector.detect("c1", "test_wizard", data)
        vr = [f for f in report.findings if f.check_type == "value_range"]
        assert len(vr) == 1
        assert "Cost too high" in vr[0].message

    def test_different_context_no_check(self, detector):
        data = {"cost": "600000", "type": "Commercial"}
        report = detector.detect("c1", "test_wizard", data)
        vr = [f for f in report.findings if f.check_type == "value_range"]
        assert len(vr) == 0

    def test_missing_value_skipped(self, detector):
        data = {"type": "Residential"}
        report = detector.detect("c1", "test_wizard", data)
        vr = [f for f in report.findings if f.check_type == "value_range"]
        assert len(vr) == 0


# --- Temporal logic checks ---


class TestTemporalLogic:
    def test_future_date_passes(self, detector):
        future = (date.today() + timedelta(days=30)).isoformat()
        data = {"start_date": future, "name": "x", "email": "x"}
        report = detector.detect("c1", "test_wizard", data)
        tl = [f for f in report.findings if f.check_type == "temporal_logic"]
        assert len(tl) == 0

    def test_past_date_fails(self, detector):
        past = (date.today() - timedelta(days=30)).isoformat()
        data = {"start_date": past}
        report = detector.detect("c1", "test_wizard", data)
        tl = [f for f in report.findings if f.check_type == "temporal_logic"]
        assert len(tl) == 1
        assert "future" in tl[0].message

    def test_missing_date_skipped(self, detector):
        report = detector.detect("c1", "test_wizard", {})
        tl = [f for f in report.findings if f.check_type == "temporal_logic"]
        assert len(tl) == 0


# --- Cross reference checks ---


class TestCrossReference:
    def test_matching_pattern_passes(self, detector):
        data = {"parcel_id": "COM-12345", "type": "Commercial", "name": "x", "email": "x"}
        report = detector.detect("c1", "test_wizard", data)
        cr = [f for f in report.findings if f.check_type == "cross_reference"]
        assert len(cr) == 0

    def test_non_matching_pattern_fails(self, detector):
        data = {"parcel_id": "RES-12345", "type": "Commercial"}
        report = detector.detect("c1", "test_wizard", data)
        cr = [f for f in report.findings if f.check_type == "cross_reference"]
        assert len(cr) == 1
        assert "Commercial" in cr[0].message

    def test_different_reference_no_check(self, detector):
        data = {"parcel_id": "RES-12345", "type": "Residential"}
        report = detector.detect("c1", "test_wizard", data)
        cr = [f for f in report.findings if f.check_type == "cross_reference"]
        assert len(cr) == 0


# --- Completeness checks ---


class TestCompleteness:
    def test_all_present_passes(self, detector):
        future = (date.today() + timedelta(days=30)).isoformat()
        data = {"name": "John", "email": "john@test.com", "start_date": future}
        report = detector.detect("c1", "test_wizard", data)
        comp = [f for f in report.findings if f.check_type == "completeness"]
        assert len(comp) == 0

    def test_missing_fields_found(self, detector):
        data = {"name": "John"}
        report = detector.detect("c1", "test_wizard", data)
        comp = [f for f in report.findings if f.check_type == "completeness"]
        assert len(comp) == 1
        assert "email" in comp[0].fields

    def test_empty_string_counts_as_missing(self, detector):
        data = {"name": "John", "email": "  "}
        report = detector.detect("c1", "test_wizard", data)
        comp = [f for f in report.findings if f.check_type == "completeness"]
        assert len(comp) == 1


# --- Edge cases ---


class TestDetectorEdgeCases:
    def test_unknown_wizard(self, detector):
        report = detector.detect("c1", "unknown", {"field": "val"})
        assert len(report.findings) == 0

    def test_missing_config(self, tmp_path):
        d = InconsistencyDetector(config_path=tmp_path / "missing.yml")
        report = d.detect("c1", "test", {})
        assert len(report.findings) == 0

    def test_production_rules_load(self):
        d = InconsistencyDetector()
        report = d.detect("c1", "permit_application", {
            "estimated_cost": "1000000",
            "property_type": "Residential",
        })
        vr = [f for f in report.findings if f.check_type == "value_range"]
        assert len(vr) >= 1
