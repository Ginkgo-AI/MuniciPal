"""PostgreSQL intake repository for wizard states and cases."""

from __future__ import annotations

from sqlalchemy import func, select

from municipal.core.types import DataClassification
from municipal.db.engine import DatabaseManager
from municipal.db.models import CaseRow, WizardStateRow
from municipal.intake.models import Case, StepState, WizardState


class PostgresIntakeRepository:
    """Postgres-backed intake storage."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def save_wizard_state(self, state: WizardState) -> None:
        async with self._db.session() as db:
            existing = await db.get(WizardStateRow, state.id)
            if existing:
                existing.wizard_id = state.wizard_id
                existing.session_id = state.session_id
                existing.current_step_index = state.current_step_index
                existing.steps = [s.model_dump() for s in state.steps]
                existing.updated_at = state.updated_at
                existing.completed = state.completed
            else:
                row = WizardStateRow(
                    id=state.id,
                    wizard_id=state.wizard_id,
                    session_id=state.session_id,
                    current_step_index=state.current_step_index,
                    steps=[s.model_dump() for s in state.steps],
                    created_at=state.created_at,
                    updated_at=state.updated_at,
                    completed=state.completed,
                )
                db.add(row)
            await db.commit()

    async def get_wizard_state(self, state_id: str) -> WizardState | None:
        async with self._db.session() as db:
            row = await db.get(WizardStateRow, state_id)
            if row is None:
                return None
            return self._row_to_wizard_state(row)

    async def list_wizard_states(self, session_id: str) -> list[WizardState]:
        async with self._db.session() as db:
            result = await db.execute(
                select(WizardStateRow).where(WizardStateRow.session_id == session_id)
            )
            return [self._row_to_wizard_state(r) for r in result.scalars().all()]

    async def save_case(self, case: Case) -> None:
        async with self._db.session() as db:
            existing = await db.get(CaseRow, case.id)
            if existing:
                existing.wizard_id = case.wizard_id
                existing.session_id = case.session_id
                existing.data = case.data
                existing.classification = case.classification.value
                existing.approval_request_id = case.approval_request_id
                existing.status = case.status
            else:
                row = CaseRow(
                    id=case.id,
                    wizard_id=case.wizard_id,
                    session_id=case.session_id,
                    data=case.data,
                    classification=case.classification.value,
                    approval_request_id=case.approval_request_id,
                    created_at=case.created_at,
                    status=case.status,
                )
                db.add(row)
            await db.commit()

    async def get_case(self, case_id: str) -> Case | None:
        async with self._db.session() as db:
            row = await db.get(CaseRow, case_id)
            if row is None:
                return None
            return self._row_to_case(row)

    async def list_cases(self, session_id: str) -> list[Case]:
        async with self._db.session() as db:
            result = await db.execute(
                select(CaseRow).where(CaseRow.session_id == session_id)
            )
            return [self._row_to_case(r) for r in result.scalars().all()]

    async def list_all_cases(self) -> list[Case]:
        async with self._db.session() as db:
            result = await db.execute(select(CaseRow))
            return [self._row_to_case(r) for r in result.scalars().all()]

    async def list_cases_by_wizard(self, wizard_id: str) -> list[Case]:
        async with self._db.session() as db:
            result = await db.execute(
                select(CaseRow).where(CaseRow.wizard_id == wizard_id)
            )
            return [self._row_to_case(r) for r in result.scalars().all()]

    @property
    def case_count(self) -> int:
        raise NotImplementedError("Use async_case_count() instead for Postgres")

    async def async_case_count(self) -> int:
        async with self._db.session() as db:
            result = await db.execute(select(func.count()).select_from(CaseRow))
            return result.scalar_one()

    @staticmethod
    def _row_to_wizard_state(row: WizardStateRow) -> WizardState:
        return WizardState(
            id=row.id,
            wizard_id=row.wizard_id,
            session_id=row.session_id,
            current_step_index=row.current_step_index,
            steps=[StepState(**s) for s in (row.steps or [])],
            created_at=row.created_at,
            updated_at=row.updated_at,
            completed=row.completed,
        )

    @staticmethod
    def _row_to_case(row: CaseRow) -> Case:
        return Case(
            id=row.id,
            wizard_id=row.wizard_id,
            session_id=row.session_id,
            data=row.data or {},
            classification=DataClassification(row.classification),
            approval_request_id=row.approval_request_id,
            created_at=row.created_at,
            status=row.status,
        )
