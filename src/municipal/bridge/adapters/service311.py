"""Mock 311 service request adapter with fixture data."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from municipal.bridge.base import BaseBridgeAdapter
from municipal.bridge.models import AdapterConfig, NormalizedRequest, NormalizedResponse, Operation


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ServiceCategory(StrEnum):
    POTHOLE = "pothole"
    STREETLIGHT = "streetlight"
    TRASH = "trash"
    NOISE = "noise"
    WATER = "water"
    OTHER = "other"


class TicketNote(BaseModel):
    author: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Ticket(BaseModel):
    ticket_id: str = Field(default_factory=lambda: f"SR-{uuid.uuid4().hex[:8].upper()}")
    category: str
    description: str
    location: str = ""
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.MEDIUM
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    notes: list[TicketNote] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


_FIXTURE_TICKETS: list[dict[str, Any]] = [
    {
        "ticket_id": "SR-2024-001",
        "category": "pothole",
        "description": "Large pothole on Main St near intersection with Oak Ave",
        "location": "123 Main St",
        "status": "open",
        "priority": "high",
        "contact_name": "Jane Smith",
        "contact_email": "jane@example.com",
    },
    {
        "ticket_id": "SR-2024-002",
        "category": "streetlight",
        "description": "Streetlight out on Elm St between 3rd and 4th",
        "location": "345 Elm St",
        "status": "in_progress",
        "priority": "medium",
        "contact_name": "Bob Johnson",
    },
    {
        "ticket_id": "SR-2024-003",
        "category": "trash",
        "description": "Missed trash pickup on Pine Rd",
        "location": "789 Pine Rd",
        "status": "resolved",
        "priority": "low",
        "contact_name": "Maria Garcia",
        "contact_email": "maria@example.com",
    },
    {
        "ticket_id": "SR-2024-004",
        "category": "water",
        "description": "Water main leak on Broadway",
        "location": "555 Broadway",
        "status": "open",
        "priority": "urgent",
        "contact_name": "Downtown Cafe LLC",
        "contact_phone": "555-0100",
    },
    {
        "ticket_id": "SR-2024-005",
        "category": "noise",
        "description": "Construction noise outside permitted hours",
        "location": "456 Oak Ave",
        "status": "closed",
        "priority": "medium",
        "contact_name": "Acme Corp",
    },
]


class Mock311Adapter(BaseBridgeAdapter):
    """Mock 311 service request adapter with fixture data.

    Operations: list_tickets, get_ticket, create_ticket, add_note.
    Classification: INTERNAL
    """

    def __init__(self, config: AdapterConfig | None = None, **kwargs: Any) -> None:
        if config is None:
            config = AdapterConfig(
                name="service_311",
                description="311 service request system",
                classification="internal",
            )
        super().__init__(config, **kwargs)
        self._tickets: dict[str, Ticket] = {}
        self._load_fixtures()

    def _load_fixtures(self) -> None:
        for data in _FIXTURE_TICKETS:
            ticket = Ticket(**data)
            self._tickets[ticket.ticket_id] = ticket

    def _get_operations(self) -> list[str]:
        return [
            Operation.LIST_TICKETS,
            Operation.GET_TICKET,
            Operation.CREATE_TICKET,
            Operation.ADD_NOTE,
        ]

    def _do_query(self, request: NormalizedRequest) -> NormalizedResponse:
        op = request.operation
        params = request.params

        if op == Operation.LIST_TICKETS:
            return self._list_tickets(params)
        if op == Operation.GET_TICKET:
            return self._get_ticket(params)
        if op == Operation.CREATE_TICKET:
            return self._create_ticket(params)
        if op == Operation.ADD_NOTE:
            return self._add_note(params)

        return NormalizedResponse(success=False, error=f"Unknown operation: {op}")

    def _list_tickets(self, params: dict[str, Any]) -> NormalizedResponse:
        tickets = list(self._tickets.values())
        if "status" in params:
            tickets = [t for t in tickets if t.status == params["status"]]
        if "category" in params:
            tickets = [t for t in tickets if t.category == params["category"]]
        return NormalizedResponse(
            success=True,
            data=[t.model_dump(mode="json") for t in tickets],
        )

    def _get_ticket(self, params: dict[str, Any]) -> NormalizedResponse:
        ticket_id = params.get("ticket_id", "")
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return NormalizedResponse(success=False, error=f"Ticket {ticket_id!r} not found")
        return NormalizedResponse(success=True, data=ticket.model_dump(mode="json"))

    def _create_ticket(self, params: dict[str, Any]) -> NormalizedResponse:
        ticket = Ticket(
            category=params.get("category", "other"),
            description=params.get("description", ""),
            location=params.get("location", ""),
            contact_name=params.get("contact_name", ""),
            contact_email=params.get("contact_email", ""),
            contact_phone=params.get("contact_phone", ""),
        )
        self._tickets[ticket.ticket_id] = ticket
        return NormalizedResponse(success=True, data=ticket.model_dump(mode="json"))

    def _add_note(self, params: dict[str, Any]) -> NormalizedResponse:
        ticket_id = params.get("ticket_id", "")
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return NormalizedResponse(success=False, error=f"Ticket {ticket_id!r} not found")
        note = TicketNote(
            author=params.get("author", ""),
            content=params.get("content", ""),
        )
        ticket.notes.append(note)
        ticket.updated_at = datetime.now(timezone.utc)
        return NormalizedResponse(success=True, data=ticket.model_dump(mode="json"))
