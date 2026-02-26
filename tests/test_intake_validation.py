"""Tests for intake validation engine and common validators."""

from __future__ import annotations

import pytest

from municipal.intake.models import FieldDefinition, FieldType, StepDefinition
from municipal.intake.validation import ValidationEngine
from municipal.intake.validators.common import (
    validate_date,
    validate_email,
    validate_numeric,
    validate_phone,
    validate_regex,
    validate_required,
)


class TestCommonValidators:
    def test_required_empty(self):
        assert validate_required(None) is not None
        assert validate_required("") is not None
        assert validate_required("   ") is not None

    def test_required_ok(self):
        assert validate_required("hello") is None
        assert validate_required(0) is None

    def test_email_valid(self):
        assert validate_email("user@example.com") is None
        assert validate_email("a@b.co") is None

    def test_email_invalid(self):
        assert validate_email("not-an-email") is not None
        assert validate_email("@no-local.com") is not None

    def test_email_empty_ok(self):
        assert validate_email(None) is None
        assert validate_email("") is None

    def test_phone_valid(self):
        assert validate_phone("555-123-4567") is None
        assert validate_phone("(555) 123-4567") is None
        assert validate_phone("+1 555 123 4567") is None

    def test_phone_invalid(self):
        assert validate_phone("123") is not None
        assert validate_phone("abcdefghij") is not None

    def test_phone_empty_ok(self):
        assert validate_phone(None) is None

    def test_date_valid(self):
        assert validate_date("2024-01-15") is None

    def test_date_invalid(self):
        assert validate_date("01/15/2024") is not None
        assert validate_date("not-a-date") is not None

    def test_numeric_valid(self):
        assert validate_numeric("42") is None
        assert validate_numeric("3.14") is None
        assert validate_numeric("0", min_val=0) is None
        assert validate_numeric("100", max_val=100) is None

    def test_numeric_invalid(self):
        assert validate_numeric("abc") is not None

    def test_numeric_out_of_range(self):
        assert validate_numeric("-1", min_val=0) is not None
        assert validate_numeric("101", max_val=100) is not None

    def test_regex_match(self):
        assert validate_regex("ABC-123", pattern=r"[A-Z]+-\d+") is None

    def test_regex_no_match(self):
        assert validate_regex("abc", pattern=r"\d+") is not None


class TestValidationEngine:
    def test_validate_step_all_valid(self):
        engine = ValidationEngine()
        step = StepDefinition(
            id="s1",
            title="Step",
            fields=[
                FieldDefinition(
                    id="name", label="Name", field_type=FieldType.TEXT,
                    required=True, validators=["required"],
                ),
                FieldDefinition(
                    id="email", label="Email", field_type=FieldType.EMAIL,
                    required=True, validators=["required", "email"],
                ),
            ],
        )
        result = engine.validate_step(step, {"name": "Jane", "email": "jane@ex.com"})
        assert result.valid
        assert result.errors == {}

    def test_validate_step_with_errors(self):
        engine = ValidationEngine()
        step = StepDefinition(
            id="s1",
            title="Step",
            fields=[
                FieldDefinition(
                    id="name", label="Name", field_type=FieldType.TEXT,
                    required=True, validators=["required"],
                ),
                FieldDefinition(
                    id="email", label="Email", field_type=FieldType.EMAIL,
                    required=True, validators=["required", "email"],
                ),
            ],
        )
        result = engine.validate_step(step, {"name": "", "email": "bad"})
        assert not result.valid
        assert "name" in result.errors
        assert "email" in result.errors

    def test_validate_field_with_params(self):
        engine = ValidationEngine()
        field = FieldDefinition(
            id="cost", label="Cost", field_type=FieldType.NUMBER,
            validators=["numeric:min_val=0"],
        )
        errors = engine.validate_field(field, "-5")
        assert len(errors) > 0
        errors2 = engine.validate_field(field, "10")
        assert len(errors2) == 0

    def test_custom_validator_registration(self):
        engine = ValidationEngine()

        def custom_check(value, **kwargs):
            if value == "bad":
                return "Value is bad"
            return None

        engine.register("custom_check", custom_check)
        field = FieldDefinition(
            id="f", label="F", field_type=FieldType.TEXT, validators=["custom_check"],
        )
        assert engine.validate_field(field, "bad") == ["Value is bad"]
        assert engine.validate_field(field, "good") == []
