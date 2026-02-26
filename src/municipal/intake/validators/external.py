"""External validators that wrap GIS and graph services."""

from __future__ import annotations

from typing import Any

from municipal.gis.service import MockGISService


def parcel_exists_factory(gis_service: MockGISService):
    """Create a validator that checks whether a parcel exists in GIS."""
    def validate_parcel_exists(value: Any, **_kwargs: Any) -> str | None:
        if value is None or not isinstance(value, str) or not value.strip():
            return None
        parcel = gis_service.lookup_by_id(value)
        if parcel is None:
            parcel = gis_service.lookup_by_address(value)
        if parcel is None:
            return f"No parcel found for '{value}'. Please verify the address or parcel ID."
        return None
    return validate_parcel_exists


def license_valid_factory(valid_licenses: set[str] | None = None):
    """Create a validator that checks contractor license numbers.

    For Phase 2, uses a simple set lookup. Future phases could
    query an external licensing database.
    """
    known = valid_licenses or {"LIC-001", "LIC-002", "LIC-003", "LIC-12345"}

    def validate_license(value: Any, **_kwargs: Any) -> str | None:
        if value is None or not isinstance(value, str) or not value.strip():
            return None
        if value.strip() not in known:
            return f"License '{value}' could not be verified."
        return None
    return validate_license
