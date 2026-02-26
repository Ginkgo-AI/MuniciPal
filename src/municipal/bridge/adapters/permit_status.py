"""Mock permit status adapter with fixture data."""

from __future__ import annotations

from typing import Any

from municipal.bridge.base import BaseBridgeAdapter
from municipal.bridge.models import AdapterConfig, NormalizedRequest, NormalizedResponse, Operation

_FIXTURE_PERMITS: list[dict[str, Any]] = [
    {
        "permit_id": "BP-2024-001",
        "parcel_id": "12-34-100-001",
        "applicant": "Jane Smith",
        "type": "Building",
        "status": "approved",
        "description": "Single-family home addition",
        "submitted_date": "2024-01-15",
        "decision_date": "2024-02-10",
        "address": "123 Main St",
    },
    {
        "permit_id": "BP-2024-002",
        "parcel_id": "12-34-100-002",
        "applicant": "Acme Corp",
        "type": "Commercial",
        "status": "pending",
        "description": "Office renovation",
        "submitted_date": "2024-03-01",
        "decision_date": None,
        "address": "456 Oak Ave",
    },
    {
        "permit_id": "EP-2024-003",
        "parcel_id": "12-34-100-001",
        "applicant": "Jane Smith",
        "type": "Electrical",
        "status": "approved",
        "description": "Panel upgrade 100A to 200A",
        "submitted_date": "2024-02-20",
        "decision_date": "2024-03-05",
        "address": "123 Main St",
    },
    {
        "permit_id": "DP-2024-004",
        "parcel_id": "12-34-100-003",
        "applicant": "Bob Johnson",
        "type": "Demolition",
        "status": "denied",
        "description": "Garage demolition",
        "submitted_date": "2024-01-10",
        "decision_date": "2024-01-25",
        "address": "789 Elm St",
    },
    {
        "permit_id": "FP-2024-005",
        "parcel_id": "12-34-100-004",
        "applicant": "Maria Garcia",
        "type": "Fence",
        "status": "approved",
        "description": "6-foot privacy fence",
        "submitted_date": "2024-04-01",
        "decision_date": "2024-04-10",
        "address": "321 Pine Rd",
    },
    {
        "permit_id": "SP-2024-006",
        "parcel_id": "12-34-100-005",
        "applicant": "Downtown Cafe LLC",
        "type": "Sign",
        "status": "pending",
        "description": "Illuminated business sign",
        "submitted_date": "2024-04-15",
        "decision_date": None,
        "address": "555 Broadway",
    },
    {
        "permit_id": "PP-2024-007",
        "parcel_id": "12-34-100-002",
        "applicant": "Acme Corp",
        "type": "Plumbing",
        "status": "approved",
        "description": "Bathroom remodel plumbing",
        "submitted_date": "2024-03-10",
        "decision_date": "2024-03-25",
        "address": "456 Oak Ave",
    },
]


class MockPermitStatusAdapter(BaseBridgeAdapter):
    """Mock permit status adapter with fixture data.

    Operations: lookup_by_id, lookup_by_parcel, lookup_by_applicant.
    Classification: SENSITIVE
    """

    def __init__(self, config: AdapterConfig | None = None, **kwargs: Any) -> None:
        if config is None:
            config = AdapterConfig(
                name="permit_status",
                description="Municipal permit status lookup",
                classification="sensitive",
            )
        super().__init__(config, **kwargs)
        self._permits = list(_FIXTURE_PERMITS)

    def _get_operations(self) -> list[str]:
        return [
            Operation.LOOKUP_BY_ID,
            Operation.LOOKUP_BY_PARCEL,
            Operation.LOOKUP_BY_APPLICANT,
        ]

    def _do_query(self, request: NormalizedRequest) -> NormalizedResponse:
        op = request.operation
        params = request.params

        if op == Operation.LOOKUP_BY_ID:
            permit_id = params.get("permit_id", "")
            result = [p for p in self._permits if p["permit_id"] == permit_id]
            if result:
                return NormalizedResponse(success=True, data=result[0])
            return NormalizedResponse(success=True, data=None)

        if op == Operation.LOOKUP_BY_PARCEL:
            parcel_id = params.get("parcel_id", "")
            results = [p for p in self._permits if p["parcel_id"] == parcel_id]
            return NormalizedResponse(success=True, data=results)

        if op == Operation.LOOKUP_BY_APPLICANT:
            applicant = params.get("applicant", "").lower()
            results = [p for p in self._permits if applicant in p["applicant"].lower()]
            return NormalizedResponse(success=True, data=results)

        return NormalizedResponse(
            success=False,
            error=f"Unknown operation: {op}",
        )
