"""Tests for cross-field validation (Phase 4 — WP1)."""

from __future__ import annotations

import pytest
import yaml
from pathlib import Path

from municipal.intake.validators.cross_field import CrossFieldValidator
from municipal.intake.validation import ValidationEngine


# --- Fixtures ---


@pytest.fixture
def rules_dir(tmp_path):
    """Create a temp config with cross-field rules."""
    config = {
        "wizards": {
            "test_wizard": [
                {
                    "type": "date_order",
                    "field_a": "start_date",
                    "field_b": "end_date",
                    "message": "End date must be on or after start date.",
                },
                {
                    "type": "conditional_required",
                    "field_a": "property_type",
                    "value": "Commercial",
                    "field_b": "contractor_name",
                    "message": "Contractor is required for commercial properties.",
                },
                {
                    "type": "mutual_exclusion",
                    "field_a": "option_a",
                    "field_b": "option_b",
                    "message": "Cannot select both option A and option B.",
                },
                {
                    "type": "numeric_relationship",
                    "field_a": "min_budget",
                    "field_b": "max_budget",
                    "operator": "<=",
                    "message": "Min budget must be <= max budget.",
                },
            ],
        }
    }
    config_path = tmp_path / "cross_field_rules.yml"
    with open(config_path, "w") as fh:
        yaml.dump(config, fh)
    return config_path


@pytest.fixture
def validator(rules_dir):
    return CrossFieldValidator(config_path=rules_dir)


# --- CrossFieldValidator unit tests ---


class TestDateOrderRule:
    def test_valid_date_order(self, validator):
        data = {"start_date": "2024-01-01", "end_date": "2024-06-01"}
        errors = validator.validate("test_wizard", data)
        assert errors == {}

    def test_same_dates_valid(self, validator):
        data = {"start_date": "2024-03-15", "end_date": "2024-03-15"}
        errors = validator.validate("test_wizard", data)
        assert errors == {}

    def test_invalid_date_order(self, validator):
        data = {"start_date": "2024-06-01", "end_date": "2024-01-01"}
        errors = validator.validate("test_wizard", data)
        assert "end_date" in errors
        assert "End date must be on or after start date." in errors["end_date"]

    def test_missing_dates_skipped(self, validator):
        data = {"start_date": "2024-01-01"}
        errors = validator.validate("test_wizard", data)
        assert errors == {}

    def test_empty_dates_skipped(self, validator):
        data = {"start_date": "", "end_date": ""}
        errors = validator.validate("test_wizard", data)
        assert errors == {}

    def test_invalid_date_format_skipped(self, validator):
        data = {"start_date": "not-a-date", "end_date": "2024-01-01"}
        errors = validator.validate("test_wizard", data)
        assert errors == {}


class TestConditionalRequiredRule:
    def test_condition_met_field_present(self, validator):
        data = {"property_type": "Commercial", "contractor_name": "Bob's Building"}
        errors = validator.validate("test_wizard", data)
        # Should have no conditional_required error
        assert "contractor_name" not in errors

    def test_condition_met_field_missing(self, validator):
        data = {"property_type": "Commercial"}
        errors = validator.validate("test_wizard", data)
        assert "contractor_name" in errors
        assert "Contractor is required for commercial properties." in errors["contractor_name"]

    def test_condition_met_field_empty_string(self, validator):
        data = {"property_type": "Commercial", "contractor_name": "   "}
        errors = validator.validate("test_wizard", data)
        assert "contractor_name" in errors

    def test_condition_not_met(self, validator):
        data = {"property_type": "Residential"}
        errors = validator.validate("test_wizard", data)
        assert "contractor_name" not in errors


class TestMutualExclusionRule:
    def test_neither_set(self, validator):
        errors = validator.validate("test_wizard", {})
        assert "option_b" not in errors

    def test_only_a_set(self, validator):
        data = {"option_a": "yes"}
        errors = validator.validate("test_wizard", data)
        assert "option_b" not in errors

    def test_only_b_set(self, validator):
        data = {"option_b": "yes"}
        errors = validator.validate("test_wizard", data)
        assert "option_b" not in errors

    def test_both_set(self, validator):
        data = {"option_a": "yes", "option_b": "yes"}
        errors = validator.validate("test_wizard", data)
        assert "option_b" in errors
        assert "Cannot select both option A and option B." in errors["option_b"]


class TestNumericRelationshipRule:
    def test_valid_relationship(self, validator):
        data = {"min_budget": "1000", "max_budget": "5000"}
        errors = validator.validate("test_wizard", data)
        assert "max_budget" not in errors

    def test_equal_values_valid_for_lte(self, validator):
        data = {"min_budget": "1000", "max_budget": "1000"}
        errors = validator.validate("test_wizard", data)
        assert "max_budget" not in errors

    def test_invalid_relationship(self, validator):
        data = {"min_budget": "5000", "max_budget": "1000"}
        errors = validator.validate("test_wizard", data)
        assert "max_budget" in errors
        assert "Min budget must be <= max budget." in errors["max_budget"]

    def test_missing_values_skipped(self, validator):
        data = {"min_budget": "1000"}
        errors = validator.validate("test_wizard", data)
        assert errors == {}

    def test_non_numeric_skipped(self, validator):
        data = {"min_budget": "abc", "max_budget": "1000"}
        errors = validator.validate("test_wizard", data)
        assert errors == {}


class TestValidatorMisc:
    def test_unknown_wizard_returns_no_errors(self, validator):
        errors = validator.validate("nonexistent_wizard", {"start_date": "2025-01-01"})
        assert errors == {}

    def test_unknown_rule_type_ignored(self, tmp_path):
        config = {
            "wizards": {
                "w": [{"type": "unknown_type", "field_a": "x", "field_b": "y"}]
            }
        }
        config_path = tmp_path / "rules.yml"
        with open(config_path, "w") as fh:
            yaml.dump(config, fh)
        v = CrossFieldValidator(config_path=config_path)
        assert v.validate("w", {"x": "1", "y": "2"}) == {}

    def test_missing_config_file(self, tmp_path):
        v = CrossFieldValidator(config_path=tmp_path / "nonexistent.yml")
        assert v.validate("any", {}) == {}


class TestValidationEngineIntegration:
    def test_validate_cross_field_delegates(self, tmp_path):
        config = {
            "wizards": {
                "test": [
                    {
                        "type": "date_order",
                        "field_a": "start",
                        "field_b": "end",
                    }
                ]
            }
        }
        config_path = tmp_path / "cross_field_rules.yml"
        with open(config_path, "w") as fh:
            yaml.dump(config, fh)

        engine = ValidationEngine()
        # Inject a cross-field validator with our config
        from municipal.intake.validators.cross_field import CrossFieldValidator
        engine._cross_field_validator = CrossFieldValidator(config_path=config_path)

        result = engine.validate_cross_field("test", {"start": "2024-06-01", "end": "2024-01-01"})
        assert not result.valid
        assert "end" in result.errors

    def test_validate_cross_field_valid(self, tmp_path):
        config = {"wizards": {"test": []}}
        config_path = tmp_path / "cross_field_rules.yml"
        with open(config_path, "w") as fh:
            yaml.dump(config, fh)

        engine = ValidationEngine()
        from municipal.intake.validators.cross_field import CrossFieldValidator
        engine._cross_field_validator = CrossFieldValidator(config_path=config_path)

        result = engine.validate_cross_field("test", {"start": "2024-01-01"})
        assert result.valid


class TestProductionRules:
    """Test the actual production cross_field_rules.yml."""

    @pytest.fixture
    def prod_validator(self):
        return CrossFieldValidator()

    def test_foia_date_order_invalid(self, prod_validator):
        errors = prod_validator.validate(
            "foia_request",
            {"date_range_start": "2024-06-01", "date_range_end": "2024-01-01"},
        )
        assert "date_range_end" in errors

    def test_foia_date_order_valid(self, prod_validator):
        errors = prod_validator.validate(
            "foia_request",
            {"date_range_start": "2024-01-01", "date_range_end": "2024-06-01"},
        )
        assert errors == {}

    def test_permit_commercial_requires_contractor(self, prod_validator):
        errors = prod_validator.validate(
            "permit_application",
            {"property_type": "Commercial"},
        )
        assert "contractor_name" in errors

    def test_permit_residential_no_contractor_needed(self, prod_validator):
        errors = prod_validator.validate(
            "permit_application",
            {"property_type": "Residential"},
        )
        assert "contractor_name" not in errors
