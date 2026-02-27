"""Tests for bridge framework: base adapter, registry, permit status adapter."""

from __future__ import annotations

import pytest

from municipal.bridge.base import BaseBridgeAdapter
from municipal.bridge.models import (
    AdapterConfig,
    ConnectionStatus,
    NormalizedRequest,
    NormalizedResponse,
    Operation,
)
from municipal.bridge.registry import AdapterRegistry
from municipal.bridge.adapters.permit_status import MockPermitStatusAdapter


class TestMockPermitStatusAdapter:
    def setup_method(self) -> None:
        self.adapter = MockPermitStatusAdapter()

    def test_name(self) -> None:
        assert self.adapter.name == "permit_status"

    def test_schema(self) -> None:
        schema = self.adapter.schema
        assert schema.name == "permit_status"
        assert schema.classification == "sensitive"
        assert Operation.LOOKUP_BY_ID in schema.operations

    def test_health_check(self) -> None:
        assert self.adapter.health_check() == ConnectionStatus.CONNECTED

    def test_lookup_by_id_found(self) -> None:
        req = NormalizedRequest(operation="lookup_by_id", params={"permit_id": "BP-2024-001"})
        resp = self.adapter.query(req)
        assert resp.success
        assert resp.data["permit_id"] == "BP-2024-001"
        assert resp.data["applicant"] == "Jane Smith"

    def test_lookup_by_id_not_found(self) -> None:
        req = NormalizedRequest(operation="lookup_by_id", params={"permit_id": "NONEXISTENT"})
        resp = self.adapter.query(req)
        assert not resp.success
        assert "not found" in resp.error.lower()

    def test_lookup_by_parcel(self) -> None:
        req = NormalizedRequest(
            operation="lookup_by_parcel",
            params={"parcel_id": "12-34-100-001"},
        )
        resp = self.adapter.query(req)
        assert resp.success
        assert len(resp.data) == 2  # Jane Smith has 2 permits on this parcel

    def test_lookup_by_applicant(self) -> None:
        req = NormalizedRequest(
            operation="lookup_by_applicant",
            params={"applicant": "jane"},
        )
        resp = self.adapter.query(req)
        assert resp.success
        assert len(resp.data) == 2

    def test_unknown_operation(self) -> None:
        req = NormalizedRequest(operation="nonexistent", params={})
        resp = self.adapter.query(req)
        assert not resp.success
        assert "Unknown operation" in resp.error

    def test_disabled_adapter(self) -> None:
        config = AdapterConfig(name="permit_status", enabled=False, classification="sensitive")
        adapter = MockPermitStatusAdapter(config=config)
        req = NormalizedRequest(operation="lookup_by_id", params={"permit_id": "BP-2024-001"})
        resp = adapter.query(req)
        assert not resp.success
        assert "disabled" in resp.error

    def test_session_cache(self) -> None:
        req = NormalizedRequest(
            operation="lookup_by_id",
            params={"permit_id": "BP-2024-001"},
            session_id="sess-1",
        )
        resp1 = self.adapter.query(req)
        assert resp1.success
        assert not resp1.cached

        resp2 = self.adapter.query(req)
        assert resp2.success
        assert resp2.cached

    def test_clear_cache(self) -> None:
        req = NormalizedRequest(
            operation="lookup_by_id",
            params={"permit_id": "BP-2024-001"},
            session_id="sess-1",
        )
        self.adapter.query(req)
        self.adapter.clear_cache("sess-1")

        resp = self.adapter.query(req)
        assert not resp.cached


class TestAdapterRegistry:
    def setup_method(self) -> None:
        self.registry = AdapterRegistry()

    def test_register_and_get(self) -> None:
        adapter = MockPermitStatusAdapter()
        self.registry.register(adapter)
        assert self.registry.get("permit_status") is adapter

    def test_get_nonexistent(self) -> None:
        assert self.registry.get("nope") is None

    def test_list_adapters(self) -> None:
        self.registry.register(MockPermitStatusAdapter())
        schemas = self.registry.list_adapters()
        assert len(schemas) == 1
        assert schemas[0].name == "permit_status"

    def test_health_check_all(self) -> None:
        self.registry.register(MockPermitStatusAdapter())
        health = self.registry.health_check_all()
        assert health["permit_status"] == ConnectionStatus.CONNECTED

    def test_adapter_names(self) -> None:
        self.registry.register(MockPermitStatusAdapter())
        assert "permit_status" in self.registry.adapter_names


class TestGracefulDegradation:
    """Test that adapter gracefully degrades on errors."""

    def test_retry_and_fallback(self) -> None:
        """Adapter with _do_query that always fails should return fallback."""

        class FailingAdapter(BaseBridgeAdapter):
            def _get_operations(self) -> list[str]:
                return ["test"]

            def _do_query(self, request: NormalizedRequest) -> NormalizedResponse:
                raise ConnectionError("System down")

        config = AdapterConfig(name="failing", classification="internal")
        adapter = FailingAdapter(config)
        req = NormalizedRequest(operation="test", params={})
        resp = adapter.query(req)
        assert not resp.success
        assert "contact staff" in resp.error.lower()
        assert adapter.health_check() == ConnectionStatus.DEGRADED
