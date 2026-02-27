"""Deterministic fee calculation engine — zero LLM calls."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from municipal.finance.models import FeeEstimate, FeeLineItem, FeeScheduleEntry


_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "fee_schedules.yml"


class FeeEngine:
    """Loads fee schedules from YAML and computes fees deterministically."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config_path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._schedules: dict[str, list[FeeScheduleEntry]] = {}
        self._raw: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        with open(self._config_path) as fh:
            self._raw = yaml.safe_load(fh) or {}

        for wizard_type, entries in self._raw.get("schedules", {}).items():
            wizard_type = str(wizard_type)  # YAML may parse numeric keys as int
            self._schedules[wizard_type] = []
            for entry_data in entries:
                self._schedules[wizard_type].append(
                    FeeScheduleEntry(
                        name=entry_data["name"],
                        description=entry_data.get("description", ""),
                        base_fee=entry_data.get("base_fee", 0.0),
                        per_unit_fee=entry_data.get("per_unit_fee", 0.0),
                        unit_label=entry_data.get("unit_label", ""),
                        free_units=entry_data.get("free_units", 0),
                    )
                )

    def get_schedule(self, wizard_type: str) -> list[FeeScheduleEntry]:
        return self._schedules.get(wizard_type, [])

    def list_schedules(self) -> dict[str, list[FeeScheduleEntry]]:
        return dict(self._schedules)

    def compute_permit_fee(
        self,
        permit_type: str,
        property_type: str = "residential",
        estimated_cost: float = 0.0,
        area_sqft: float = 0.0,
    ) -> FeeEstimate:
        schedule = self._schedules.get("permit", [])
        items: list[FeeLineItem] = []

        # Find matching permit type entry
        entry = None
        for e in schedule:
            if e.name.lower() == permit_type.lower():
                entry = e
                break

        if entry is None:
            raise ValueError(
                f"No fee schedule entry for permit type {permit_type!r}. "
                f"Available: {[e.name for e in schedule]}"
            )

        # Base fee
        items.append(FeeLineItem(
            description=f"{entry.name} permit - base fee",
            amount=entry.base_fee,
        ))

        # Per-unit fee (e.g., per sqft)
        if entry.per_unit_fee > 0 and area_sqft > 0:
            items.append(FeeLineItem(
                description=f"{entry.name} permit - per {entry.unit_label}",
                amount=entry.per_unit_fee,
                quantity=area_sqft,
            ))

        return FeeEstimate(wizard_type="permit", line_items=items)

    def compute_foia_fee(self, page_count: int) -> FeeEstimate:
        schedule = self._schedules.get("foia", [])
        items: list[FeeLineItem] = []

        entry = schedule[0] if schedule else FeeScheduleEntry(
            name="FOIA copies", per_unit_fee=0.15, free_units=50, unit_label="page",
        )

        billable_pages = max(0, page_count - entry.free_units)
        if billable_pages > 0:
            items.append(FeeLineItem(
                description=f"FOIA copies ({billable_pages} pages after {entry.free_units} free)",
                amount=entry.per_unit_fee,
                quantity=billable_pages,
            ))
        else:
            items.append(FeeLineItem(
                description=f"FOIA copies ({page_count} pages, within {entry.free_units} free allowance)",
                amount=0.0,
            ))

        return FeeEstimate(wizard_type="foia", line_items=items)

    def compute_311_fee(self) -> FeeEstimate:
        return FeeEstimate(
            wizard_type="311",
            line_items=[FeeLineItem(description="311 service request - no fee", amount=0.0)],
        )

    def compute(self, wizard_type: str, data: dict[str, Any]) -> FeeEstimate:
        if wizard_type == "permit":
            return self.compute_permit_fee(
                permit_type=data.get("permit_type", "Building"),
                property_type=data.get("property_type", "residential"),
                estimated_cost=data.get("estimated_cost", 0.0),
                area_sqft=data.get("area_sqft", 0.0),
            )
        elif wizard_type == "foia":
            return self.compute_foia_fee(page_count=data.get("page_count", 0))
        elif wizard_type == "311":
            return self.compute_311_fee()
        else:
            raise ValueError(f"Unknown wizard type for fee computation: {wizard_type!r}")
