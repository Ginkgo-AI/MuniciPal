"""Tests for WP4: PostgresIntakeRepository with SQLite async."""

from __future__ import annotations

import pytest

from municipal.core.types import DataClassification
from municipal.db.base import Base
from municipal.db.engine import DatabaseManager
from municipal.intake.models import Case, StepState, WizardState
from municipal.repositories.postgres.intake import PostgresIntakeRepository

import municipal.db.models  # noqa: F401


@pytest.fixture
async def repo():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield PostgresIntakeRepository(db)
    await db.close()


async def test_save_and_get_wizard_state(repo):
    state = WizardState(
        wizard_id="permit",
        session_id="sess-1",
        steps=[StepState(step_id="step1")],
    )
    await repo.save_wizard_state(state)
    found = await repo.get_wizard_state(state.id)
    assert found is not None
    assert found.wizard_id == "permit"
    assert len(found.steps) == 1
    assert found.steps[0].step_id == "step1"


async def test_list_wizard_states(repo):
    for i in range(3):
        state = WizardState(wizard_id="permit", session_id="sess-1")
        await repo.save_wizard_state(state)
    states = await repo.list_wizard_states("sess-1")
    assert len(states) == 3


async def test_save_and_get_case(repo):
    case = Case(
        wizard_id="permit",
        session_id="sess-1",
        data={"name": "Test"},
        classification=DataClassification.SENSITIVE,
    )
    await repo.save_case(case)
    found = await repo.get_case(case.id)
    assert found is not None
    assert found.data == {"name": "Test"}
    assert found.classification == DataClassification.SENSITIVE


async def test_list_cases(repo):
    case = Case(wizard_id="permit", session_id="sess-1")
    await repo.save_case(case)
    cases = await repo.list_cases("sess-1")
    assert len(cases) == 1


async def test_list_all_cases(repo):
    await repo.save_case(Case(wizard_id="p", session_id="s1"))
    await repo.save_case(Case(wizard_id="p", session_id="s2"))
    assert len(await repo.list_all_cases()) == 2


async def test_list_cases_by_wizard(repo):
    await repo.save_case(Case(wizard_id="permit", session_id="s1"))
    await repo.save_case(Case(wizard_id="foia", session_id="s1"))
    assert len(await repo.list_cases_by_wizard("permit")) == 1


async def test_update_wizard_state(repo):
    state = WizardState(wizard_id="permit", session_id="sess-1")
    await repo.save_wizard_state(state)
    state.completed = True
    await repo.save_wizard_state(state)
    found = await repo.get_wizard_state(state.id)
    assert found.completed is True
