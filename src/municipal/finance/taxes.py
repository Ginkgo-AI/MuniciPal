"""Deterministic property tax estimation engine — zero LLM calls."""

from __future__ import annotations


from municipal.finance.models import TaxEstimate


# Hardcoded tax rates per property type (percentage of assessed value)
_TAX_RATES: dict[str, float] = {
    "residential": 1.25,
    "commercial": 2.20,
    "industrial": 1.75,
    "mixed use": 1.65,
}


class TaxEngine:
    """Estimates annual property tax based on property type and assessed value."""

    def __init__(self, rates: dict[str, float] | None = None) -> None:
        self._rates = rates if rates is not None else dict(_TAX_RATES)

    @property
    def rates(self) -> dict[str, float]:
        return dict(self._rates)

    def estimate_annual_tax(
        self,
        property_type: str,
        assessed_value: float,
    ) -> TaxEstimate:
        key = property_type.lower()
        if key not in self._rates:
            raise ValueError(
                f"Unknown property type {property_type!r}. "
                f"Available: {list(self._rates.keys())}"
            )

        rate_pct = self._rates[key]
        annual_tax = round(assessed_value * rate_pct / 100.0, 2)

        return TaxEstimate(
            property_type=property_type,
            assessed_value=assessed_value,
            annual_tax=annual_tax,
            effective_rate=rate_pct,
        )
