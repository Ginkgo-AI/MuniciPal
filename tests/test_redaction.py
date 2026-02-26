"""Tests for redaction suggestions (Phase 4 — WP2)."""

from __future__ import annotations

import pytest
import yaml

from municipal.review.redaction import RedactionEngine
from municipal.review.models import Confidence


# --- Fixtures ---


@pytest.fixture
def rules_path(tmp_path):
    config = {
        "classification_threshold": "sensitive",
        "pattern_rules": [
            {
                "pattern": r"\d{3}-\d{2}-\d{4}",
                "reason": "SSN detected",
                "confidence": "high",
                "classification": "restricted",
            },
            {
                "pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "reason": "Email detected",
                "confidence": "high",
                "classification": "sensitive",
            },
            {
                "pattern": r"\d{3}-\d{3}-\d{4}",
                "reason": "Phone detected",
                "confidence": "medium",
                "classification": "sensitive",
            },
        ],
        "field_rules": [
            {
                "field_pattern": "(ssn|social_security)",
                "reason": "SSN field",
                "confidence": "high",
                "classification": "restricted",
            },
            {
                "field_pattern": "(phone|mobile)",
                "reason": "Phone field",
                "confidence": "medium",
                "classification": "sensitive",
            },
        ],
    }
    path = tmp_path / "redaction_rules.yml"
    with open(path, "w") as fh:
        yaml.dump(config, fh)
    return path


@pytest.fixture
def engine(rules_path):
    return RedactionEngine(config_path=rules_path)


# --- Pattern-based detection ---


class TestPatternDetection:
    def test_ssn_detected(self, engine):
        report = engine.scan("case-1", {"ssn_field": "123-45-6789"})
        assert len(report.suggestions) >= 1
        ssn_sug = [s for s in report.suggestions if "SSN" in s.reason]
        assert len(ssn_sug) >= 1
        assert ssn_sug[0].confidence == Confidence.HIGH

    def test_email_detected(self, engine):
        report = engine.scan("case-1", {"contact": "user@example.com"})
        assert len(report.suggestions) >= 1
        assert any("Email" in s.reason for s in report.suggestions)

    def test_phone_detected(self, engine):
        report = engine.scan("case-1", {"info": "Call 555-123-4567"})
        assert len(report.suggestions) >= 1
        assert any("Phone" in s.reason for s in report.suggestions)

    def test_no_pii_no_suggestions(self, engine):
        report = engine.scan("case-1", {"description": "Fix the pothole on Main St"})
        assert len(report.suggestions) == 0

    def test_empty_values_skipped(self, engine):
        report = engine.scan("case-1", {"field": "", "field2": None})
        assert len(report.suggestions) == 0

    def test_multiple_pii_in_different_fields(self, engine):
        report = engine.scan("case-1", {
            "ssn": "123-45-6789",
            "email": "test@example.com",
        })
        assert len(report.suggestions) >= 2


# --- Classification-based detection ---


class TestClassificationDetection:
    def test_sensitive_field_flagged(self, engine):
        report = engine.scan(
            "case-1",
            {"name": "John Doe"},
            field_classifications={"name": "sensitive"},
        )
        assert len(report.suggestions) >= 1
        assert any(s.field_id == "name" for s in report.suggestions)

    def test_public_field_not_flagged(self, engine):
        report = engine.scan(
            "case-1",
            {"category": "pothole"},
            field_classifications={"category": "public"},
        )
        assert len(report.suggestions) == 0

    def test_restricted_field_flagged(self, engine):
        report = engine.scan(
            "case-1",
            {"secret_data": "classified info"},
            field_classifications={"secret_data": "restricted"},
        )
        assert len(report.suggestions) >= 1

    def test_no_duplicate_when_pattern_already_flagged(self, engine):
        report = engine.scan(
            "case-1",
            {"email_field": "user@example.com"},
            field_classifications={"email_field": "sensitive"},
        )
        # Should flag by pattern; classification should not duplicate
        email_suggestions = [s for s in report.suggestions if s.field_id == "email_field"]
        assert len(email_suggestions) == 1


# --- Field name rules ---


class TestFieldNameRules:
    def test_ssn_field_name_flagged(self, engine):
        report = engine.scan("case-1", {"social_security_number": "not-a-pattern"})
        assert any(s.field_id == "social_security_number" for s in report.suggestions)

    def test_phone_field_name_flagged(self, engine):
        report = engine.scan("case-1", {"home_phone": "not-a-pattern-match"})
        assert any(s.field_id == "home_phone" for s in report.suggestions)

    def test_normal_field_name_not_flagged(self, engine):
        report = engine.scan("case-1", {"description": "just a description"})
        assert len(report.suggestions) == 0


# --- Report structure ---


class TestReportStructure:
    def test_report_has_case_id(self, engine):
        report = engine.scan("my-case-123", {})
        assert report.case_id == "my-case-123"

    def test_report_has_generated_at(self, engine):
        report = engine.scan("case-1", {})
        assert report.generated_at is not None

    def test_snippet_truncation(self, engine):
        long_value = "123-45-6789 " * 20
        report = engine.scan("case-1", {"field": long_value})
        for s in report.suggestions:
            assert len(s.value_snippet) <= 53  # 50 + "..."


# --- Edge cases ---


class TestEdgeCases:
    def test_missing_config_file(self, tmp_path):
        engine = RedactionEngine(config_path=tmp_path / "nonexistent.yml")
        report = engine.scan("case-1", {"ssn": "123-45-6789"})
        assert len(report.suggestions) == 0

    def test_production_rules_load(self):
        engine = RedactionEngine()
        report = engine.scan("case-1", {"field": "123-45-6789"})
        assert len(report.suggestions) >= 1
