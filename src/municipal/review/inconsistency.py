"""Rule-based inconsistency detection within a single case's data."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from municipal.review.models import InconsistencyFinding, InconsistencyReport


_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "inconsistency_rules.yml"


class InconsistencyDetector:
    """Detects contradictions and inconsistencies within a case's data.

    Check types:
    - value_range: value should fall within expected range for a given context
    - temporal_logic: date fields should be in future/past as appropriate
    - cross_reference: field format should match expectations based on other fields
    - completeness: required-for-approval fields are present
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config_path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._rules: dict[str, list[dict[str, Any]]] = {}
        self._load_config()

    def _load_config(self) -> None:
        if not self._config_path.exists():
            return
        with open(self._config_path) as fh:
            data = yaml.safe_load(fh) or {}
        self._rules = data.get("wizards", {})

    def detect(self, case_id: str, wizard_id: str, data: dict[str, Any]) -> InconsistencyReport:
        """Detect inconsistencies in a case's data.

        Returns:
            InconsistencyReport with findings.
        """
        rules = self._rules.get(wizard_id, [])
        findings: list[InconsistencyFinding] = []

        for rule in rules:
            check_type = rule.get("type")
            finding = self._run_check(check_type, rule, data)
            if finding:
                findings.append(finding)

        return InconsistencyReport(case_id=case_id, findings=findings)

    def _run_check(
        self, check_type: str | None, rule: dict[str, Any], data: dict[str, Any]
    ) -> InconsistencyFinding | None:
        if check_type == "value_range":
            return self._check_value_range(rule, data)
        elif check_type == "temporal_logic":
            return self._check_temporal_logic(rule, data)
        elif check_type == "cross_reference":
            return self._check_cross_reference(rule, data)
        elif check_type == "completeness":
            return self._check_completeness(rule, data)
        return None

    def _check_value_range(
        self, rule: dict[str, Any], data: dict[str, Any]
    ) -> InconsistencyFinding | None:
        field = rule.get("field", "")
        context_field = rule.get("context_field", "")
        context_value = rule.get("context_value", "")
        max_value = rule.get("max_value")
        min_value = rule.get("min_value")

        # Check context condition
        if context_field and data.get(context_field) != context_value:
            return None

        value = data.get(field)
        if value is None:
            return None

        try:
            num = float(value)
        except (TypeError, ValueError):
            return None

        if max_value is not None and num > float(max_value):
            return InconsistencyFinding(
                check_type="value_range",
                fields=[field, context_field] if context_field else [field],
                message=rule.get("message", f"{field} value {num} exceeds expected maximum {max_value}."),
                severity=rule.get("severity", "warning"),
            )

        if min_value is not None and num < float(min_value):
            return InconsistencyFinding(
                check_type="value_range",
                fields=[field, context_field] if context_field else [field],
                message=rule.get("message", f"{field} value {num} below expected minimum {min_value}."),
                severity=rule.get("severity", "warning"),
            )

        return None

    def _check_temporal_logic(
        self, rule: dict[str, Any], data: dict[str, Any]
    ) -> InconsistencyFinding | None:
        field = rule.get("field", "")
        expected = rule.get("expected", "future")  # "future" or "past"

        value = data.get(field)
        if not value:
            return None

        try:
            if isinstance(value, date) and not isinstance(value, datetime):
                field_date = value
            elif isinstance(value, datetime):
                field_date = value.date()
            else:
                field_date = datetime.strptime(str(value), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

        today = date.today()

        if expected == "future" and field_date < today:
            return InconsistencyFinding(
                check_type="temporal_logic",
                fields=[field],
                message=rule.get("message", f"{field} should be in the future but is {field_date}."),
                severity=rule.get("severity", "warning"),
            )

        if expected == "past" and field_date > today:
            return InconsistencyFinding(
                check_type="temporal_logic",
                fields=[field],
                message=rule.get("message", f"{field} should be in the past but is {field_date}."),
                severity=rule.get("severity", "warning"),
            )

        return None

    def _check_cross_reference(
        self, rule: dict[str, Any], data: dict[str, Any]
    ) -> InconsistencyFinding | None:
        field = rule.get("field", "")
        reference_field = rule.get("reference_field", "")
        expected_pattern = rule.get("expected_pattern", "")

        value = data.get(field)
        ref_value = data.get(reference_field)

        if not value or not ref_value:
            return None

        # Only check if reference matches the trigger value
        trigger_value = rule.get("reference_value")
        if trigger_value and str(ref_value) != str(trigger_value):
            return None

        import re
        if expected_pattern and not re.search(expected_pattern, str(value)):
            return InconsistencyFinding(
                check_type="cross_reference",
                fields=[field, reference_field],
                message=rule.get("message", f"{field} format doesn't match expectations for {reference_field}={ref_value}."),
                severity=rule.get("severity", "warning"),
            )

        return None

    def _check_completeness(
        self, rule: dict[str, Any], data: dict[str, Any]
    ) -> InconsistencyFinding | None:
        required_fields = rule.get("required_fields", [])
        missing = []

        for f in required_fields:
            val = data.get(f)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append(f)

        if missing:
            return InconsistencyFinding(
                check_type="completeness",
                fields=missing,
                message=rule.get("message", f"Missing required fields for approval: {', '.join(missing)}."),
                severity=rule.get("severity", "info"),
            )

        return None
