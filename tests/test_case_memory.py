"""Tests for case memory linking via graph store during wizard submission."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from municipal.core.types import SessionType
from municipal.graph.models import EntityType, RelationshipType
from municipal.graph.store import GraphStore
from municipal.intake.engine import WizardEngine
from municipal.intake.store import IntakeStore
from municipal.intake.validation import ValidationEngine

# Minimal 2-step wizard YAML for testing graph linking
_WIZARD_YAML = """
id: test_graph_wizard
title: "Test Graph Wizard"
description: "Wizard to test graph linking"
classification: public
steps:
  - id: step_one
    title: "Step One"
    required_session_tier: anonymous
    fields:
      - id: applicant_name
        label: "Name"
        type: text
        required: true
        validators: ["required"]
      - id: parcel_id
        label: "Parcel"
        type: text
        required: false
  - id: step_two
    title: "Step Two"
    required_session_tier: anonymous
    fields:
      - id: description
        label: "Description"
        type: text
        required: true
        validators: ["required"]
"""


@pytest.fixture
def engine_with_graph(tmp_path: Path) -> tuple[WizardEngine, GraphStore]:
    """Create a WizardEngine with GraphStore using a temp wizard file."""
    wizard_file = tmp_path / "test_graph_wizard.yml"
    wizard_file.write_text(_WIZARD_YAML)

    store = IntakeStore()
    graph = GraphStore()
    engine = WizardEngine(
        store=store,
        validation_engine=ValidationEngine(),
        graph_store=graph,
        wizards_dir=tmp_path,
    )
    return engine, graph


class TestCaseMemoryLinking:
    def test_case_creates_graph_nodes(
        self, engine_with_graph: tuple[WizardEngine, GraphStore]
    ) -> None:
        engine, graph = engine_with_graph

        state = engine.start_wizard("test_graph_wizard", "session-1")

        engine.submit_step(
            state.id,
            "step_one",
            {"applicant_name": "Jane Doe", "parcel_id": "P-001"},
        )
        engine.submit_step(state.id, "step_two", {"description": "Test case"})
        case = engine.submit_wizard(state.id, "session-1")

        # Verify CASE node
        case_node = graph.get_node(f"case:{case.id}")
        assert case_node is not None
        assert case_node.entity_type == EntityType.CASE

        # Verify PERSON node
        person_node = graph.get_node("person:session-1")
        assert person_node is not None
        assert person_node.entity_type == EntityType.PERSON
        assert person_node.label == "Jane Doe"

        # Verify PARCEL node
        parcel_node = graph.get_node("parcel:P-001")
        assert parcel_node is not None
        assert parcel_node.entity_type == EntityType.PARCEL

        # Verify SUBMITTED edge
        neighbors = graph.get_neighbors("person:session-1", RelationshipType.SUBMITTED)
        assert any(n.id == f"case:{case.id}" for n in neighbors)

        # Verify LOCATED_AT edge
        neighbors = graph.get_neighbors(f"case:{case.id}", RelationshipType.LOCATED_AT)
        assert any(n.id == "parcel:P-001" for n in neighbors)

    def test_case_without_parcel_skips_parcel_node(
        self, engine_with_graph: tuple[WizardEngine, GraphStore]
    ) -> None:
        engine, graph = engine_with_graph

        state = engine.start_wizard("test_graph_wizard", "session-2")
        engine.submit_step(
            state.id, "step_one", {"applicant_name": "Bob", "parcel_id": ""}
        )
        engine.submit_step(state.id, "step_two", {"description": "No parcel"})
        case = engine.submit_wizard(state.id, "session-2")

        assert graph.get_node(f"case:{case.id}") is not None
        assert graph.get_node("person:session-2") is not None
        # No parcel node should exist for empty parcel_id
        assert graph.query(entity_type=EntityType.PARCEL) == []

    def test_multiple_cases_same_person(
        self, engine_with_graph: tuple[WizardEngine, GraphStore]
    ) -> None:
        engine, graph = engine_with_graph

        # First case
        s1 = engine.start_wizard("test_graph_wizard", "session-3")
        engine.submit_step(s1.id, "step_one", {"applicant_name": "Alice"})
        engine.submit_step(s1.id, "step_two", {"description": "Case 1"})
        case1 = engine.submit_wizard(s1.id, "session-3")

        # Second case
        s2 = engine.start_wizard("test_graph_wizard", "session-3")
        engine.submit_step(s2.id, "step_one", {"applicant_name": "Alice"})
        engine.submit_step(s2.id, "step_two", {"description": "Case 2"})
        case2 = engine.submit_wizard(s2.id, "session-3")

        # Person node should exist once
        person_nodes = graph.query(entity_type=EntityType.PERSON)
        session3_persons = [n for n in person_nodes if n.id == "person:session-3"]
        assert len(session3_persons) == 1

        # Both cases linked
        neighbors = graph.get_neighbors("person:session-3", RelationshipType.SUBMITTED)
        case_ids = {n.id for n in neighbors}
        assert f"case:{case1.id}" in case_ids
        assert f"case:{case2.id}" in case_ids

    def test_engine_without_graph_works(self, tmp_path: Path) -> None:
        """WizardEngine without graph_store still works fine."""
        wizard_file = tmp_path / "test_graph_wizard.yml"
        wizard_file.write_text(_WIZARD_YAML)

        engine = WizardEngine(
            store=IntakeStore(),
            validation_engine=ValidationEngine(),
            wizards_dir=tmp_path,
        )
        state = engine.start_wizard("test_graph_wizard", "session-x")
        engine.submit_step(state.id, "step_one", {"applicant_name": "Test"})
        engine.submit_step(state.id, "step_two", {"description": "No graph"})
        case = engine.submit_wizard(state.id, "session-x")
        assert case.id  # No error
