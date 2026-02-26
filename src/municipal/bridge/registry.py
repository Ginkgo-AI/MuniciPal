"""Adapter registry for managing bridge adapters."""

from __future__ import annotations

from municipal.bridge.base import BridgeAdapter
from municipal.bridge.models import AdapterSchema, ConnectionStatus


class AdapterRegistry:
    """Registry for bridge adapters. Provides register/get/list and health checking."""

    def __init__(self) -> None:
        self._adapters: dict[str, BridgeAdapter] = {}

    def register(self, adapter: BridgeAdapter) -> None:
        """Register a bridge adapter."""
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> BridgeAdapter | None:
        """Get an adapter by name."""
        return self._adapters.get(name)

    def list_adapters(self) -> list[AdapterSchema]:
        """List all registered adapters with their schemas."""
        return [adapter.schema for adapter in self._adapters.values()]

    def health_check_all(self) -> dict[str, ConnectionStatus]:
        """Run health checks on all adapters."""
        return {name: adapter.health_check() for name, adapter in self._adapters.items()}

    @property
    def adapter_names(self) -> list[str]:
        return list(self._adapters.keys())
