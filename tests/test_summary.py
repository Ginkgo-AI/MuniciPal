"""Tests for case summaries and department reports (Phase 4 — WP4)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from municipal.core.types import DataClassification
from municipal.graph.models import Edge, EntityType, Node, RelationshipType
from municipal.graph.store import GraphStore
from municipal.intake.models import Case
from municipal.intake.store import IntakeStore
from municipal.review.summary import SummaryEngine


@pytest.fixture
def store():
    return IntakeStore()


@pytest.fixture
def graph_store():
    return GraphStore()


@pytest.fixture
def engine(store, graph_store):
    wizard_defs = {
        "permit_application": type("Def", (), {"title": "Permit Application"})(),
        "foia_request": type("Def", (), {"title": "FOIA Request"})(),
    }
    return SummaryEngine(
        intake_store=store,
        graph_store=graph_store,
        wizard_definitions=wizard_defs,
    )


def _make_case(wizard_id="permit_application", status="submitted", **data_kw) -> Case:
    return Case(
        wizard_id=wizard_id,
        session_id="session-1",
        data=data_kw or {"applicant_name": "Jane", "property_address": "123 Main"},
        classification=DataClassification.SENSITIVE,
        status=status,
    )


class TestCaseSummary:
    def test_basic_summary(self, engine, store):
        case = _make_case()
        store.save_case(case)
        summary = engine.summarize_case(case)

        assert summary.case_id == case.id
        assert summary.wizard_id == "permit_application"
        assert summary.wizard_title == "Permit Application"
        assert summary.status == "submitted"
        assert summary.classification == "sensitive"
        assert "applicant_name" in summary.key_facts

    def test_summary_includes_timeline(self, engine, store):
        case = _make_case()
        store.save_case(case)
        summary = engine.summarize_case(case)
        assert len(summary.timeline) >= 1
        assert summary.timeline[0]["event"] == "Case created"

    def test_summary_with_graph_entities(self, engine, store, graph_store):
        case = _make_case()
        store.save_case(case)

        case_node = Node(
            id=f"case:{case.id}",
            entity_type=EntityType.CASE,
            label=f"Case {case.id}",
        )
        person_node = Node(
            id="person:session-1",
            entity_type=EntityType.PERSON,
            label="Jane",
        )
        graph_store.add_node(case_node)
        graph_store.add_node(person_node)
        graph_store.add_edge(Edge(
            source_id=person_node.id,
            target_id=case_node.id,
            relationship=RelationshipType.SUBMITTED,
        ))

        summary = engine.summarize_case(case)
        assert len(summary.related_entities) >= 1
        assert any(e["type"] == "person" for e in summary.related_entities)

    def test_summary_without_graph(self, store):
        engine = SummaryEngine(intake_store=store)
        case = _make_case()
        store.save_case(case)
        summary = engine.summarize_case(case)
        assert summary.related_entities == []

    def test_summary_unknown_wizard(self, store):
        engine = SummaryEngine(intake_store=store)
        case = _make_case(wizard_id="unknown")
        summary = engine.summarize_case(case)
        assert summary.wizard_title == "unknown"

    def test_empty_data_excluded_from_key_facts(self, engine, store):
        case = _make_case(name="John", empty_field="", none_field=None)
        # Override data to include empty
        case.data = {"name": "John", "empty_field": "", "none_field": None}
        store.save_case(case)
        summary = engine.summarize_case(case)
        assert "name" in summary.key_facts
        assert "empty_field" not in summary.key_facts
        assert "none_field" not in summary.key_facts


class TestDepartmentReport:
    def test_report_all_cases(self, engine, store):
        store.save_case(_make_case())
        store.save_case(_make_case(wizard_id="foia_request"))
        report = engine.generate_department_report()
        assert report.total_cases == 2

    def test_report_filter_by_wizard(self, engine, store):
        store.save_case(_make_case())
        store.save_case(_make_case(wizard_id="foia_request"))
        report = engine.generate_department_report(wizard_type="permit_application")
        assert report.total_cases == 1
        assert report.wizard_type == "permit_application"

    def test_report_by_status(self, engine, store):
        store.save_case(_make_case(status="submitted"))
        store.save_case(_make_case(status="approved"))
        store.save_case(_make_case(status="submitted"))
        report = engine.generate_department_report()
        assert report.by_status["submitted"] == 2
        assert report.by_status["approved"] == 1

    def test_report_empty_store(self, engine):
        report = engine.generate_department_report()
        assert report.total_cases == 0
        assert report.by_status == {}

    def test_report_by_classification(self, engine, store):
        store.save_case(_make_case())
        report = engine.generate_department_report()
        assert "sensitive" in report.by_classification

    def test_report_date_filter(self, engine, store):
        case = _make_case()
        store.save_case(case)
        # Filter with a future date_from should exclude all
        report = engine.generate_department_report(date_from="2099-01-01T00:00:00+00:00")
        assert report.total_cases == 0
