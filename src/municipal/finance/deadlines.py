"""Deterministic deadline computation engine — zero LLM calls."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from municipal.finance.models import DeadlineInfo


_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "deadline_rules.yml"


class DeadlineEngine:
    """Computes statutory deadlines based on wizard type and submission date."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config_path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._rules: dict[str, dict[str, Any]] = {}
        self._load_config()

    def _load_config(self) -> None:
        with open(self._config_path) as fh:
            raw = yaml.safe_load(fh) or {}

        for wizard_type, rule_data in raw.get("deadlines", {}).items():
            wizard_type = str(wizard_type)  # YAML may parse numeric keys as int
            self._rules[wizard_type] = {
                "statutory_days": rule_data["statutory_days"],
                "business_days_only": rule_data.get("business_days_only", False),
            }

    def get_rules(self) -> dict[str, dict[str, Any]]:
        return dict(self._rules)

    def compute(
        self,
        case_id: str,
        wizard_type: str,
        submitted_at: datetime,
    ) -> DeadlineInfo:
        if wizard_type not in self._rules:
            raise ValueError(
                f"No deadline rule for wizard type {wizard_type!r}. "
                f"Available: {list(self._rules.keys())}"
            )

        rule = self._rules[wizard_type]
        statutory_days = rule["statutory_days"]
        business_days_only = rule["business_days_only"]

        start_date = submitted_at.date()
        if business_days_only:
            due = self._add_business_days(start_date, statutory_days)
        else:
            due = start_date + timedelta(days=statutory_days)

        return DeadlineInfo(
            case_id=case_id,
            wizard_type=wizard_type,
            statutory_days=statutory_days,
            business_days_only=business_days_only,
            submitted_at=submitted_at,
            due_date=due,
        )

    @staticmethod
    def _add_business_days(start: date, days: int) -> date:
        """Add business days (skipping weekends) to a start date."""
        current = start
        added = 0
        while added < days:
            current += timedelta(days=1)
            # Monday=0 ... Friday=4 are business days
            if current.weekday() < 5:
                added += 1
        return current
