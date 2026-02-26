"""FastAPI router for bridge adapter endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from municipal.bridge.models import NormalizedRequest

router = APIRouter()


class QueryRequest(BaseModel):
    operation: str
    params: dict[str, Any] = Field(default_factory=dict)
    session_id: str = ""


# --- Generic bridge endpoints ---


@router.get("/api/bridge/adapters")
async def list_adapters(request: Request) -> list[dict[str, Any]]:
    """List all registered adapters with health status."""
    registry = request.app.state.adapter_registry
    schemas = registry.list_adapters()
    return [s.model_dump() for s in schemas]


@router.get("/api/bridge/adapters/{name}/health")
async def adapter_health(name: str, request: Request) -> dict[str, Any]:
    """Check health of a specific adapter."""
    registry = request.app.state.adapter_registry
    adapter = registry.get(name)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Adapter {name!r} not found")
    return {"name": name, "status": adapter.health_check()}


@router.get("/api/bridge/adapters/{name}/schema")
async def adapter_schema(name: str, request: Request) -> dict[str, Any]:
    """Get adapter schema and operations."""
    registry = request.app.state.adapter_registry
    adapter = registry.get(name)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Adapter {name!r} not found")
    return adapter.schema.model_dump()


@router.post("/api/bridge/adapters/{name}/query")
async def adapter_query(name: str, body: QueryRequest, request: Request) -> dict[str, Any]:
    """Execute a normalized query against an adapter."""
    registry = request.app.state.adapter_registry
    adapter = registry.get(name)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Adapter {name!r} not found")

    normalized = NormalizedRequest(
        operation=body.operation,
        params=body.params,
        session_id=body.session_id,
    )
    response = adapter.query(normalized)
    return response.model_dump()


# --- Permit convenience endpoints ---


@router.get("/api/bridge/permits/{permit_id}")
async def get_permit(permit_id: str, request: Request) -> dict[str, Any]:
    """Look up a permit by ID."""
    registry = request.app.state.adapter_registry
    adapter = registry.get("permit_status")
    if adapter is None:
        raise HTTPException(status_code=404, detail="Permit status adapter not available")

    normalized = NormalizedRequest(
        operation="lookup_by_id",
        params={"permit_id": permit_id},
    )
    response = adapter.query(normalized)
    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)
    if response.data is None:
        raise HTTPException(status_code=404, detail=f"Permit {permit_id!r} not found")
    return response.data


@router.get("/api/bridge/permits")
async def search_permits(
    request: Request,
    parcel_id: str | None = None,
    applicant: str | None = None,
) -> list[dict[str, Any]]:
    """Search permits by parcel ID or applicant name."""
    registry = request.app.state.adapter_registry
    adapter = registry.get("permit_status")
    if adapter is None:
        raise HTTPException(status_code=404, detail="Permit status adapter not available")

    if parcel_id:
        normalized = NormalizedRequest(
            operation="lookup_by_parcel",
            params={"parcel_id": parcel_id},
        )
    elif applicant:
        normalized = NormalizedRequest(
            operation="lookup_by_applicant",
            params={"applicant": applicant},
        )
    else:
        raise HTTPException(status_code=400, detail="Provide parcel_id or applicant query param")

    response = adapter.query(normalized)
    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)
    return response.data or []


# --- 311 convenience endpoints (added in WP2) ---


@router.get("/api/bridge/311/tickets")
async def list_311_tickets(
    request: Request,
    status: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """List 311 tickets with optional filters."""
    registry = request.app.state.adapter_registry
    adapter = registry.get("service_311")
    if adapter is None:
        raise HTTPException(status_code=404, detail="311 service adapter not available")

    params: dict[str, Any] = {}
    if status:
        params["status"] = status
    if category:
        params["category"] = category

    normalized = NormalizedRequest(operation="list_tickets", params=params)
    response = adapter.query(normalized)
    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)
    return response.data or []


@router.get("/api/bridge/311/tickets/{ticket_id}")
async def get_311_ticket(ticket_id: str, request: Request) -> dict[str, Any]:
    """Get a specific 311 ticket."""
    registry = request.app.state.adapter_registry
    adapter = registry.get("service_311")
    if adapter is None:
        raise HTTPException(status_code=404, detail="311 service adapter not available")

    normalized = NormalizedRequest(
        operation="get_ticket",
        params={"ticket_id": ticket_id},
    )
    response = adapter.query(normalized)
    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)
    if response.data is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id!r} not found")
    return response.data


class CreateTicketRequest(BaseModel):
    category: str
    description: str
    location: str = ""
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    session_id: str = ""


@router.post("/api/bridge/311/tickets")
async def create_311_ticket(body: CreateTicketRequest, request: Request) -> dict[str, Any]:
    """Create a new 311 service request ticket."""
    registry = request.app.state.adapter_registry
    adapter = registry.get("service_311")
    if adapter is None:
        raise HTTPException(status_code=404, detail="311 service adapter not available")

    normalized = NormalizedRequest(
        operation="create_ticket",
        params=body.model_dump(exclude={"session_id"}),
        session_id=body.session_id,
    )
    response = adapter.query(normalized)
    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)
    return response.data


class AddNoteRequest(BaseModel):
    author: str
    content: str
    session_id: str = ""


@router.post("/api/bridge/311/tickets/{ticket_id}/notes")
async def add_311_note(ticket_id: str, body: AddNoteRequest, request: Request) -> dict[str, Any]:
    """Add a note to a 311 ticket."""
    registry = request.app.state.adapter_registry
    adapter = registry.get("service_311")
    if adapter is None:
        raise HTTPException(status_code=404, detail="311 service adapter not available")

    normalized = NormalizedRequest(
        operation="add_note",
        params={"ticket_id": ticket_id, "author": body.author, "content": body.content},
        session_id=body.session_id,
    )
    response = adapter.query(normalized)
    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)
    return response.data
