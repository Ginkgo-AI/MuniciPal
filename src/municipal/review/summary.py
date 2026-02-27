"""Deterministic case summaries and aggregate reports for staff review."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from municipal.graph.models import RelationshipType
from municipal.graph.store import GraphStore
from municipal.intake.models import Case
from municipal.intake.store import IntakeStore
from municipal.review.models import CaseSummary, DepartmentReport


class SummaryEngine:
    """Generates structured case summaries and department aggregate reports."""

    def __init__(
        self,
        intake_store: IntakeStore,
        graph_store: GraphStore | None = None,
        wizard_definitions: dict[str, Any] | None = None,
        approval_gate: Any | None = None,
    ) -> None:
        self._store = intake_store
        self._graph = graph_store
        self._wizard_defs = wizard_definitions or {}
        self._approval = approval_gate

    def summarize_case(self, case: Case) -> CaseSummary:
        """Generate a structured summary of a single case."""
        wizard_def = self._wizard_defs.get(case.wizard_id)
        wizard_title = wizard_def.title if wizard_def else case.wizard_id

        # Extract key facts from case data
        key_facts: dict[str, Any] = {}
        for key, value in case.data.items():
            if value is not None and (not isinstance(value, str) or value.strip()):
                key_facts[key] = value

        # Build timeline
        timeline = [
            {"event": "Case created", "date": case.created_at.isoformat()},
        ]

        # Check approval status
        approval_status = None
        if case.approval_request_id and self._approval:
            try:
                status = self._approval.check_status(case.approval_request_id)
                approval_status = str(status)
                timeline.append({
                    "event": f"Approval status: {status}",
                    "date": case.created_at.isoformat(),
                })
            except (KeyError, ValueError):
                pass

        # Get related entities from graph
        related_entities: list[dict[str, str]] = []
        if self._graph:
            case_node_id = f"case:{case.id}"
            neighbors = self._graph.get_neighbors(case_node_id)
            for node in neighbors:
                related_entities.append({
                    "id": node.id,
                    "type": node.entity_type.value,
                    "label": node.label,
                })

        return CaseSummary(
            case_id=case.id,
            wizard_id=case.wizard_id,
            wizard_title=wizard_title,
            status=case.status,
            classification=case.classification.value,
            created_at=case.created_at.isoformat(),
            key_facts=key_facts,
            timeline=timeline,
            related_entities=related_entities,
            approval_status=approval_status,
        )

    def generate_department_report(
        self,
        wizard_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> DepartmentReport:
        """Generate aggregate stats for cases matching filters."""
        if wizard_type:
            cases = self._store.list_cases_by_wizard(wizard_type)
        else:
            cases = self._store.list_all_cases()

        # Filter by date range (assume UTC if no timezone provided)
        if date_from:
            from_dt = datetime.fromisoformat(date_from)
            if from_dt.tzinfo is None:
                from_dt = from_dt.replace(tzinfo=timezone.utc)
            cases = [c for c in cases if c.created_at >= from_dt]
        if date_to:
            to_dt = datetime.fromisoformat(date_to)
            if to_dt.tzinfo is None:
                to_dt = to_dt.replace(tzinfo=timezone.utc)
            cases = [c for c in cases if c.created_at <= to_dt]

        by_status: dict[str, int] = {}
        by_classification: dict[str, int] = {}

        for case in cases:
            by_status[case.status] = by_status.get(case.status, 0) + 1
            cls_val = case.classification.value
            by_classification[cls_val] = by_classification.get(cls_val, 0) + 1

        return DepartmentReport(
            wizard_type=wizard_type,
            date_from=date_from,
            date_to=date_to,
            total_cases=len(cases),
            by_status=by_status,
            by_classification=by_classification,
        )
