"""Tests for the intake wizard engine."""

from __future__ import annotations

import pytest

from municipal.core.types import DataClassification, SessionType
from municipal.intake.engine import WizardEngine
from municipal.intake.models import (
    Case,
    FieldDefinition,
    FieldType,
    StepDefinition,
    StepStatus,
    WizardDefinition,
    WizardState,
)
from municipal.intake.store import IntakeStore
from municipal.intake.validation import ValidationEngine


@pytest.fixture
def store():
    return IntakeStore()


@pytest.fixture
def validation_engine():
    return ValidationEngine()


@pytest.fixture
def engine(store, validation_engine, tmp_path):
    """Engine loaded from the real config/wizards directory."""
    return WizardEngine(
        store=store,
        validation_engine=validation_engine,
    )


@pytest.fixture
def simple_engine(store, validation_engine, tmp_path):
    """Engine with a simple test wizard."""
    import yaml

    wizard_dir = tmp_path / "wizards"
    wizard_dir.mkdir()

    wizard_data = {
        "id": "test_wizard",
        "title": "Test Wizard",
        "description": "A test wizard",
        "steps": [
            {
                "id": "step_one",
                "title": "Step One",
                "fields": [
                    {
                        "id": "name",
                        "label": "Name",
                        "type": "text",
                        "required": True,
                        "validators": ["required"],
                    },
                    {
                        "id": "email",
                        "label": "Email",
                        "type": "email",
                        "required": True,
                        "validators": ["required", "email"],
                    },
                ],
            },
            {
                "id": "step_two",
                "title": "Step Two",
                "fields": [
                    {
                        "id": "age",
                        "label": "Age",
                        "type": "number",
                        "required": False,
                        "validators": ["numeric:min_val=0,max_val=150"],
                    },
                ],
            },
        ],
    }

    with open(wizard_dir / "test_wizard.yml", "w") as fh:
        yaml.dump(wizard_data, fh)

    return WizardEngine(
        store=store,
        validation_engine=validation_engine,
        wizards_dir=wizard_dir,
    )


class TestWizardEngine:
    def test_loads_wizard_definitions(self, engine):
        defns = engine.wizard_definitions
        assert "permit_application" in defns
        assert "foia_request" in defns

    def test_permit_has_five_steps(self, engine):
        defn = engine.wizard_definitions["permit_application"]
        assert len(defn.steps) == 5

    def test_foia_has_three_steps(self, engine):
        defn = engine.wizard_definitions["foia_request"]
        assert len(defn.steps) == 3

    def test_start_wizard(self, simple_engine, store):
        state = simple_engine.start_wizard("test_wizard", "session-1")
        assert state.wizard_id == "test_wizard"
        assert state.session_id == "session-1"
        assert len(state.steps) == 2
        assert state.steps[0].status == StepStatus.IN_PROGRESS
        assert state.steps[1].status == StepStatus.PENDING
        assert state.current_step_index == 0
        # Should be persisted in store
        assert store.get_wizard_state(state.id) is not None

    def test_start_unknown_wizard_raises(self, simple_engine):
        with pytest.raises(ValueError, match="Unknown wizard"):
            simple_engine.start_wizard("nonexistent", "session-1")

    def test_submit_step_valid(self, simple_engine, store):
        state = simple_engine.start_wizard("test_wizard", "session-1")
        data = {"name": "Jane Doe", "email": "jane@example.com"}
        updated = simple_engine.submit_step(state.id, "step_one", data)
        assert updated.steps[0].status == StepStatus.COMPLETED
        assert updated.steps[0].data == data
        assert updated.steps[0].errors == {}
        assert updated.current_step_index == 1
        assert updated.steps[1].status == StepStatus.IN_PROGRESS

    def test_submit_step_validation_error(self, simple_engine):
        state = simple_engine.start_wizard("test_wizard", "session-1")
        data = {"name": "", "email": "not-an-email"}
        updated = simple_engine.submit_step(state.id, "step_one", data)
        # Should stay on step one
        assert updated.steps[0].status == StepStatus.IN_PROGRESS
        assert "name" in updated.steps[0].errors
        assert updated.current_step_index == 0

    def test_submit_step_wrong_step_raises(self, simple_engine):
        state = simple_engine.start_wizard("test_wizard", "session-1")
        with pytest.raises(ValueError, match="Expected step"):
            simple_engine.submit_step(state.id, "step_two", {})

    def test_submit_step_unknown_state_raises(self, simple_engine):
        with pytest.raises(KeyError):
            simple_engine.submit_step("nonexistent", "step_one", {})

    def test_go_back(self, simple_engine):
        state = simple_engine.start_wizard("test_wizard", "session-1")
        simple_engine.submit_step(state.id, "step_one", {"name": "A", "email": "a@b.com"})
        updated = simple_engine.go_back(state.id)
        assert updated.current_step_index == 0
        assert updated.steps[0].status == StepStatus.IN_PROGRESS
        # Data should be preserved
        assert updated.steps[0].data == {"name": "A", "email": "a@b.com"}

    def test_go_back_at_first_step_raises(self, simple_engine):
        state = simple_engine.start_wizard("test_wizard", "session-1")
        with pytest.raises(ValueError, match="Already at the first step"):
            simple_engine.go_back(state.id)

    def test_submit_wizard(self, simple_engine, store):
        state = simple_engine.start_wizard("test_wizard", "session-1")
        simple_engine.submit_step(state.id, "step_one", {"name": "A", "email": "a@b.com"})
        simple_engine.submit_step(state.id, "step_two", {"age": "25"})
        case = simple_engine.submit_wizard(state.id, "session-1")
        assert isinstance(case, Case)
        assert case.wizard_id == "test_wizard"
        assert case.data == {"name": "A", "email": "a@b.com", "age": "25"}
        assert case.session_id == "session-1"
        # State should be marked completed
        updated_state = store.get_wizard_state(state.id)
        assert updated_state.completed is True
        # Case should be stored
        assert store.get_case(case.id) is not None

    def test_submit_wizard_incomplete_raises(self, simple_engine):
        state = simple_engine.start_wizard("test_wizard", "session-1")
        with pytest.raises(ValueError, match="not completed"):
            simple_engine.submit_wizard(state.id, "session-1")

    def test_session_tier_enforcement(self, simple_engine, store, validation_engine, tmp_path):
        """Steps requiring a higher tier should reject lower-tier sessions."""
        import yaml

        wizard_dir = tmp_path / "tier_wizards"
        wizard_dir.mkdir()
        wizard_data = {
            "id": "tier_test",
            "title": "Tier Test",
            "steps": [
                {
                    "id": "public_step",
                    "title": "Public",
                    "required_session_tier": "anonymous",
                    "fields": [
                        {"id": "q", "label": "Q", "type": "text", "required": True, "validators": ["required"]},
                    ],
                },
                {
                    "id": "verified_step",
                    "title": "Verified",
                    "required_session_tier": "verified",
                    "fields": [
                        {"id": "q2", "label": "Q2", "type": "text", "required": True, "validators": ["required"]},
                    ],
                },
            ],
        }
        with open(wizard_dir / "tier_test.yml", "w") as fh:
            yaml.dump(wizard_data, fh)

        eng = WizardEngine(
            store=store, validation_engine=validation_engine, wizards_dir=wizard_dir,
        )
        state = eng.start_wizard("tier_test", "s1")
        eng.submit_step(state.id, "public_step", {"q": "hi"}, SessionType.ANONYMOUS)
        with pytest.raises(ValueError, match="requires session tier"):
            eng.submit_step(state.id, "verified_step", {"q2": "hi"}, SessionType.ANONYMOUS)


class TestIntakeStore:
    def test_wizard_state_crud(self, store):
        state = WizardState(wizard_id="w1", session_id="s1")
        store.save_wizard_state(state)
        assert store.get_wizard_state(state.id) is state
        assert store.get_wizard_state("nonexistent") is None
        assert len(store.list_wizard_states("s1")) == 1
        assert len(store.list_wizard_states("s2")) == 0

    def test_case_crud(self, store):
        case = Case(wizard_id="w1", session_id="s1", data={"x": 1})
        store.save_case(case)
        assert store.get_case(case.id) is case
        assert store.get_case("nonexistent") is None
        assert len(store.list_cases("s1")) == 1
        assert len(store.list_cases("s2")) == 0


class TestShowIfCondition:
    def test_step_skipped_when_condition_not_met(self, store, validation_engine, tmp_path):
        import yaml

        wizard_dir = tmp_path / "skip_wizards"
        wizard_dir.mkdir()
        wizard_data = {
            "id": "skip_test",
            "title": "Skip Test",
            "steps": [
                {
                    "id": "step1",
                    "title": "Step 1",
                    "fields": [
                        {
                            "id": "type",
                            "label": "Type",
                            "type": "select",
                            "required": True,
                            "validators": ["required"],
                            "options": ["A", "B"],
                        },
                    ],
                },
                {
                    "id": "step2",
                    "title": "Step 2 (only for A)",
                    "show_if": {"field": "type", "equals": "A"},
                    "fields": [
                        {"id": "extra", "label": "Extra", "type": "text"},
                    ],
                },
                {
                    "id": "step3",
                    "title": "Step 3",
                    "fields": [
                        {"id": "done", "label": "Done", "type": "text"},
                    ],
                },
            ],
        }
        with open(wizard_dir / "skip_test.yml", "w") as fh:
            yaml.dump(wizard_data, fh)

        eng = WizardEngine(store=store, validation_engine=validation_engine, wizards_dir=wizard_dir)
        state = eng.start_wizard("skip_test", "s1")

        # Submit step1 with type=B — step2 should be skipped
        updated = eng.submit_step(state.id, "step1", {"type": "B"})
        assert updated.steps[1].status == StepStatus.SKIPPED
        assert updated.current_step_index == 2
        assert updated.steps[2].status == StepStatus.IN_PROGRESS
