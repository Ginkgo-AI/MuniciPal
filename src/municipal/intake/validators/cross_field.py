"""Cross-field validation for wizard state data."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[4] / "config" / "cross_field_rules.yml"


class CrossFieldValidator:
    """Validates relationships between fields across a wizard's data.

    Rule types:
    - date_order: field_a <= field_b
    - conditional_required: if field_a == value then field_b is required
    - mutual_exclusion: field_a and field_b cannot both be set
    - numeric_relationship: field_a < field_b (or <=, >, >=)
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

    def validate(self, wizard_id: str, data: dict[str, Any]) -> dict[str, list[str]]:
        """Validate cross-field rules for a wizard's merged data.

        Returns:
            Dict mapping field IDs to lists of error messages. Empty dict means valid.
        """
        rules = self._rules.get(wizard_id, [])
        errors: dict[str, list[str]] = {}

        for rule in rules:
            rule_type = rule.get("type")
            rule_errors = self._check_rule(rule_type, rule, data)
            for field_id, msgs in rule_errors.items():
                errors.setdefault(field_id, []).extend(msgs)

        return errors

    def _check_rule(
        self, rule_type: str | None, rule: dict[str, Any], data: dict[str, Any]
    ) -> dict[str, list[str]]:
        if rule_type == "date_order":
            return self._check_date_order(rule, data)
        elif rule_type == "conditional_required":
            return self._check_conditional_required(rule, data)
        elif rule_type == "mutual_exclusion":
            return self._check_mutual_exclusion(rule, data)
        elif rule_type == "numeric_relationship":
            return self._check_numeric_relationship(rule, data)
        return {}

    def _check_date_order(
        self, rule: dict[str, Any], data: dict[str, Any]
    ) -> dict[str, list[str]]:
        field_a = rule.get("field_a", "")
        field_b = rule.get("field_b", "")
        val_a = data.get(field_a)
        val_b = data.get(field_b)

        if not val_a or not val_b:
            return {}

        try:
            date_a = self._parse_date(val_a)
            date_b = self._parse_date(val_b)
        except (ValueError, TypeError):
            return {}

        if date_a > date_b:
            msg = rule.get("message", f"{field_a} must be on or before {field_b}.")
            return {field_b: [msg]}
        return {}

    def _check_conditional_required(
        self, rule: dict[str, Any], data: dict[str, Any]
    ) -> dict[str, list[str]]:
        field_a = rule.get("field_a", "")
        value = rule.get("value")
        field_b = rule.get("field_b", "")

        actual = data.get(field_a)
        if actual != value:
            return {}

        val_b = data.get(field_b)
        if val_b is None or (isinstance(val_b, str) and not val_b.strip()):
            msg = rule.get("message", f"{field_b} is required when {field_a} is {value}.")
            return {field_b: [msg]}
        return {}

    def _check_mutual_exclusion(
        self, rule: dict[str, Any], data: dict[str, Any]
    ) -> dict[str, list[str]]:
        field_a = rule.get("field_a", "")
        field_b = rule.get("field_b", "")

        val_a = data.get(field_a)
        val_b = data.get(field_b)

        a_set = val_a is not None and (not isinstance(val_a, str) or val_a.strip())
        b_set = val_b is not None and (not isinstance(val_b, str) or val_b.strip())

        if a_set and b_set:
            msg = rule.get("message", f"{field_a} and {field_b} cannot both be set.")
            return {field_b: [msg]}
        return {}

    def _check_numeric_relationship(
        self, rule: dict[str, Any], data: dict[str, Any]
    ) -> dict[str, list[str]]:
        field_a = rule.get("field_a", "")
        field_b = rule.get("field_b", "")
        operator = rule.get("operator", "<")

        val_a = data.get(field_a)
        val_b = data.get(field_b)

        if val_a is None or val_b is None:
            return {}

        try:
            num_a = float(val_a)
            num_b = float(val_b)
        except (TypeError, ValueError):
            return {}

        ops = {
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
        }
        check = ops.get(operator)
        if check and not check(num_a, num_b):
            msg = rule.get("message", f"{field_a} must be {operator} {field_b}.")
            return {field_b: [msg]}
        return {}

    @staticmethod
    def _parse_date(value: Any) -> date:
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        return datetime.strptime(str(value), "%Y-%m-%d").date()
