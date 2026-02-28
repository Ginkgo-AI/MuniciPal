"""Bridge adapter data models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Operation(str, Enum):
    """Standard bridge operations."""

    LOOKUP_BY_ID = "lookup_by_id"
    LOOKUP_BY_PARCEL = "lookup_by_parcel"
    LOOKUP_BY_APPLICANT = "lookup_by_applicant"
    LIST_TICKETS = "list_tickets"
    GET_TICKET = "get_ticket"
    CREATE_TICKET = "create_ticket"
    ADD_NOTE = "add_note"


class ConnectionStatus(str, Enum):
    """Adapter connection health status."""

    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"


class AdapterConfig(BaseModel):
    """Configuration for a bridge adapter."""

    name: str
    enabled: bool = True
    provider: str = "mock"
    timeout_seconds: int = 30
    classification: str = "internal"
    description: str = ""


class NormalizedRequest(BaseModel):
    """Normalized request sent to a bridge adapter."""

    operation: str
    params: dict[str, Any] = Field(default_factory=dict)
    session_id: str = ""


class NormalizedResponse(BaseModel):
    """Normalized response from a bridge adapter."""

    success: bool
    data: Any = None
    error: str | None = None
    cached: bool = False
    adapter_name: str = ""


class AdapterSchema(BaseModel):
    """Schema describing an adapter's capabilities."""

    name: str
    description: str = ""
    classification: str = "internal"
    operations: list[str] = Field(default_factory=list)
    status: ConnectionStatus = ConnectionStatus.CONNECTED
