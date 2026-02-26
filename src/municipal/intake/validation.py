"""Validation engine for intake wizard steps."""

from __future__ import annotations

from typing import Any, Callable

from municipal.intake.models import FieldDefinition, StepDefinition, ValidationResult
from municipal.intake.validators.common import VALIDATORS


class ValidationEngine:
    """Registry-based validation engine.

    Runs all validators for a step's fields against submitted data.
    Supports both sync and async validators for external lookups.
    """

    def __init__(self) -> None:
        self._validators: dict[str, Callable[..., str | None]] = dict(VALIDATORS)

    def register(self, name: str, fn: Callable[..., str | None]) -> None:
        self._validators[name] = fn

    def validate_field(
        self, field: FieldDefinition, value: Any, params: dict[str, Any] | None = None
    ) -> list[str]:
        """Validate a single field value. Returns list of error messages."""
        errors: list[str] = []
        params = params or {}

        # Always check required first
        if field.required:
            fn = self._validators.get("required")
            if fn:
                err = fn(value)
                if err:
                    errors.append(err)
                    return errors  # No point running other validators on empty

        for validator_name in field.validators:
            # Validator name may include params like "numeric:min_val=0"
            parts = validator_name.split(":", 1)
            name = parts[0]
            extra_params: dict[str, Any] = {}
            if len(parts) > 1:
                for pair in parts[1].split(","):
                    k, _, v = pair.partition("=")
                    extra_params[k.strip()] = v.strip()

            fn = self._validators.get(name)
            if fn is None:
                continue

            merged = {**params, **extra_params}
            err = fn(value, **merged)
            if err:
                errors.append(err)

        return errors

    def validate_step(
        self, step: StepDefinition, data: dict[str, Any]
    ) -> ValidationResult:
        """Validate all fields in a step against submitted data."""
        all_errors: dict[str, list[str]] = {}

        for field in step.fields:
            value = data.get(field.id)
            field_errors = self.validate_field(field, value)
            if field_errors:
                all_errors[field.id] = field_errors

        return ValidationResult(
            valid=len(all_errors) == 0,
            errors=all_errors,
        )

    def validate_cross_field(
        self, wizard_id: str, data: dict[str, Any]
    ) -> ValidationResult:
        """Run cross-field validation rules for a wizard's merged data."""
        from municipal.intake.validators.cross_field import CrossFieldValidator

        if not hasattr(self, "_cross_field_validator"):
            self._cross_field_validator = CrossFieldValidator()

        errors = self._cross_field_validator.validate(wizard_id, data)
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
        )
