"""Sunshine Report generator — annual transparency report."""

from __future__ import annotations

from typing import Any

from municipal.core.types import ApprovalStatus
from municipal.intake.store import IntakeStore
from municipal.review.models import SunshineReportData


class SunshineReportGenerator:
    """Collects stats from stores and produces a Sunshine Report.

    Deterministic aggregation only — no LLM dependency.
    """

    def __init__(
        self,
        intake_store: IntakeStore,
        approval_gate: Any | None = None,
        notification_store: Any | None = None,
    ) -> None:
        self._store = intake_store
        self._approval = approval_gate
        self._notifications = notification_store

    def generate(self) -> SunshineReportData:
        """Generate the Sunshine Report data."""
        cases = self._store.list_all_cases()

        # Cases by type
        cases_by_type: dict[str, int] = {}
        cases_by_status: dict[str, int] = {}
        foia_count = 0
        service_311_count = 0
        service_311_categories: dict[str, int] = {}

        for case in cases:
            cases_by_type[case.wizard_id] = cases_by_type.get(case.wizard_id, 0) + 1
            cases_by_status[case.status] = cases_by_status.get(case.status, 0) + 1

            if case.wizard_id == "foia_request":
                foia_count += 1
            elif case.wizard_id == "service_request_311":
                service_311_count += 1
                cat = case.data.get("category", "unknown")
                service_311_categories[cat] = service_311_categories.get(cat, 0) + 1

        # Approval stats
        approval_stats: dict[str, Any] = {}
        if self._approval:
            try:
                pending = self._approval.pending_requests
                all_requests = list(self._approval._requests.values())
                approved = [r for r in all_requests if r.status == ApprovalStatus.APPROVED]
                denied = [r for r in all_requests if r.status == ApprovalStatus.DENIED]
                approval_stats = {
                    "total_requests": len(all_requests),
                    "pending": len(pending),
                    "approved": len(approved),
                    "denied": len(denied),
                }
            except Exception:
                pass

        # FOIA metrics
        foia_metrics: dict[str, Any] = {
            "total_requests": foia_count,
        }

        # 311 stats
        service_311_stats: dict[str, Any] = {
            "total_tickets": service_311_count,
            "by_category": service_311_categories,
        }

        # Notification summary
        notification_summary: dict[str, Any] = {}
        if self._notifications:
            try:
                all_notifs = self._notifications.list_all()
                notification_summary = {
                    "total_sent": len(all_notifs),
                    "by_channel": self._count_by_attr(all_notifs, "channel"),
                    "by_status": self._count_by_attr(all_notifs, "status"),
                }
            except Exception:
                pass

        return SunshineReportData(
            total_cases=len(cases),
            cases_by_type=cases_by_type,
            cases_by_status=cases_by_status,
            approval_stats=approval_stats,
            foia_metrics=foia_metrics,
            service_311_stats=service_311_stats,
            notification_summary=notification_summary,
        )

    @staticmethod
    def _count_by_attr(items: list, attr: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in items:
            val = str(getattr(item, attr, "unknown"))
            counts[val] = counts.get(val, 0) + 1
        return counts
