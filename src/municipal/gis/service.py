"""GIS service protocol and mock implementation."""

from __future__ import annotations

from typing import Protocol

from municipal.gis.models import Parcel


class GISService(Protocol):
    """Protocol for GIS parcel lookup services."""

    def lookup_by_address(self, address: str) -> Parcel | None: ...
    def lookup_by_id(self, parcel_id: str) -> Parcel | None: ...


class MockGISService:
    """Mock GIS service with fixture parcels for development/testing."""

    def __init__(self) -> None:
        self._parcels: dict[str, Parcel] = {}
        self._address_index: dict[str, str] = {}
        self._load_fixtures()

    def _load_fixtures(self) -> None:
        fixtures = [
            Parcel(
                parcel_id="12-34-567-001",
                address="123 Main St, Springfield, IL 62701",
                owner="Jane Doe",
                acreage=0.25,
                zoning="R-1",
                land_use="Single Family Residential",
                assessed_value=185000.0,
                coordinates={"lat": 39.7817, "lng": -89.6501},
            ),
            Parcel(
                parcel_id="12-34-567-002",
                address="456 Oak Ave, Springfield, IL 62702",
                owner="Acme Corp",
                acreage=1.5,
                zoning="C-2",
                land_use="Commercial",
                assessed_value=520000.0,
                coordinates={"lat": 39.7900, "lng": -89.6440},
            ),
            Parcel(
                parcel_id="12-34-567-003",
                address="789 Industrial Blvd, Springfield, IL 62703",
                owner="Springfield Manufacturing LLC",
                acreage=5.0,
                zoning="I-1",
                land_use="Light Industrial",
                assessed_value=890000.0,
                coordinates={"lat": 39.7750, "lng": -89.6600},
            ),
            Parcel(
                parcel_id="12-34-567-004",
                address="321 Elm St, Springfield, IL 62701",
                owner="John Smith",
                acreage=0.18,
                zoning="R-2",
                land_use="Multi Family Residential",
                assessed_value=210000.0,
                coordinates={"lat": 39.7830, "lng": -89.6520},
            ),
            Parcel(
                parcel_id="12-34-567-005",
                address="100 City Hall Plaza, Springfield, IL 62701",
                owner="City of Springfield",
                acreage=2.0,
                zoning="PF",
                land_use="Public Facility",
                assessed_value=0.0,
                coordinates={"lat": 39.7990, "lng": -89.6440},
            ),
        ]
        for parcel in fixtures:
            self._parcels[parcel.parcel_id] = parcel
            self._address_index[parcel.address.lower()] = parcel.parcel_id

    def lookup_by_address(self, address: str) -> Parcel | None:
        parcel_id = self._address_index.get(address.lower())
        if parcel_id:
            return self._parcels.get(parcel_id)
        # Partial match fallback
        addr_lower = address.lower()
        for key, pid in self._address_index.items():
            if addr_lower in key or key in addr_lower:
                return self._parcels.get(pid)
        return None

    def lookup_by_id(self, parcel_id: str) -> Parcel | None:
        return self._parcels.get(parcel_id)
