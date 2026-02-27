"""Base bridge adapter with Protocol definition and ABC implementation."""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from municipal.bridge.models import (
    AdapterConfig,
    AdapterSchema,
    ConnectionStatus,
    NormalizedRequest,
    NormalizedResponse,
)
from municipal.core.types import AuditEvent, DataClassification
from municipal.governance.audit import AuditLogger


@runtime_checkable
class BridgeAdapter(Protocol):
    """Protocol for bridge adapters per REFERENCE.md Section 5."""

    @property
    def name(self) -> str: ...

    @property
    def schema(self) -> AdapterSchema: ...

    def query(self, request: NormalizedRequest) -> NormalizedResponse: ...

    def health_check(self) -> ConnectionStatus: ...


class BaseBridgeAdapter(ABC):
    """Abstract base class for bridge adapters.

    Provides configurable timeout, at-most-1 retry, session-scoped cache,
    graceful degradation, and optional audit logging.
    """

    def __init__(
        self,
        config: AdapterConfig,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self._config = config
        self._audit = audit_logger
        self._cache: dict[str, NormalizedResponse] = {}
        self._status = ConnectionStatus.CONNECTED

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def schema(self) -> AdapterSchema:
        return AdapterSchema(
            name=self._config.name,
            description=self._config.description,
            classification=self._config.classification,
            operations=self._get_operations(),
            status=self._status,
        )

    @abstractmethod
    def _get_operations(self) -> list[str]:
        """Return list of supported operation names."""

    @abstractmethod
    def _do_query(self, request: NormalizedRequest) -> NormalizedResponse:
        """Execute the actual query. Subclasses implement this."""

    def query(self, request: NormalizedRequest) -> NormalizedResponse:
        """Execute a query with caching, retry, and graceful degradation."""
        if not self._config.enabled:
            return NormalizedResponse(
                success=False,
                error="Adapter is disabled",
                adapter_name=self.name,
            )

        # Check cache
        cache_key = self._cache_key(request)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            return NormalizedResponse(
                success=cached.success,
                data=cached.data,
                error=cached.error,
                cached=True,
                adapter_name=self.name,
            )

        # Try query with at-most-1 retry
        try:
            response = self._do_query(request)
            response.adapter_name = self.name
        except Exception:
            # Retry once
            try:
                response = self._do_query(request)
                response.adapter_name = self.name
            except Exception:
                # Graceful degradation
                self._status = ConnectionStatus.DEGRADED
                response = NormalizedResponse(
                    success=False,
                    error="System temporarily unavailable. Please contact staff for assistance.",
                    adapter_name=self.name,
                )

        # Cache successful responses
        if response.success and request.session_id:
            self._cache[cache_key] = response

        # Audit log
        self._log_audit(request, response)

        return response

    def health_check(self) -> ConnectionStatus:
        """Check adapter health."""
        return self._status

    def clear_cache(self, session_id: str | None = None) -> None:
        """Clear cache entries, optionally for a specific session."""
        if session_id is None:
            self._cache.clear()
        else:
            keys_to_remove = [k for k in self._cache if k.startswith(f"{session_id}:")]
            for k in keys_to_remove:
                del self._cache[k]

    def _cache_key(self, request: NormalizedRequest) -> str:
        params_hash = hashlib.sha256(
            json.dumps(request.params, sort_keys=True).encode()
        ).hexdigest()
        return f"{request.session_id}:{request.operation}:{params_hash}"

    def _log_audit(self, request: NormalizedRequest, response: NormalizedResponse) -> None:
        if self._audit is None:
            return
        event = AuditEvent(
            session_id=request.session_id or "system",
            actor=request.session_id or "system",
            action="bridge_query",
            resource=f"adapter:{self.name}:{request.operation}",
            classification=DataClassification(self._config.classification),
            details={
                "operation": request.operation,
                "success": response.success,
                "cached": response.cached,
            },
        )
        self._audit.log(event)
