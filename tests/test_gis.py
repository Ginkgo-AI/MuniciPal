"""Tests for GIS service."""

from __future__ import annotations

import pytest

from municipal.gis.models import Parcel
from municipal.gis.service import MockGISService


@pytest.fixture
def gis():
    return MockGISService()


class TestMockGISService:
    def test_lookup_by_id(self, gis):
        parcel = gis.lookup_by_id("12-34-567-001")
        assert parcel is not None
        assert parcel.parcel_id == "12-34-567-001"
        assert "Main St" in parcel.address

    def test_lookup_by_id_not_found(self, gis):
        assert gis.lookup_by_id("99-99-999-999") is None

    def test_lookup_by_address_exact(self, gis):
        parcel = gis.lookup_by_address("123 Main St, Springfield, IL 62701")
        assert parcel is not None
        assert parcel.parcel_id == "12-34-567-001"

    def test_lookup_by_address_case_insensitive(self, gis):
        parcel = gis.lookup_by_address("123 MAIN ST, SPRINGFIELD, IL 62701")
        assert parcel is not None

    def test_lookup_by_address_partial(self, gis):
        parcel = gis.lookup_by_address("456 Oak Ave")
        assert parcel is not None
        assert parcel.zoning == "C-2"

    def test_lookup_by_address_not_found(self, gis):
        assert gis.lookup_by_address("999 Nowhere Ln") is None

    def test_all_fixture_parcels_accessible(self, gis):
        ids = [
            "12-34-567-001",
            "12-34-567-002",
            "12-34-567-003",
            "12-34-567-004",
            "12-34-567-005",
        ]
        for pid in ids:
            assert gis.lookup_by_id(pid) is not None

    def test_parcel_model_fields(self, gis):
        parcel = gis.lookup_by_id("12-34-567-002")
        assert parcel.owner == "Acme Corp"
        assert parcel.acreage == 1.5
        assert parcel.zoning == "C-2"
        assert parcel.assessed_value == 520000.0
        assert "lat" in parcel.coordinates
