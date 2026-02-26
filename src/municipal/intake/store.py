"""In-memory store for wizard states and cases."""

from __future__ import annotations

from municipal.intake.models import Case, WizardState


class IntakeStore:
    """In-memory dict store for wizard states and cases.

    Same pattern as SessionManager — suitable for single-instance deployment.
    """

    def __init__(self) -> None:
        self._wizard_states: dict[str, WizardState] = {}
        self._cases: dict[str, Case] = {}

    # -- Wizard states --

    def save_wizard_state(self, state: WizardState) -> None:
        self._wizard_states[state.id] = state

    def get_wizard_state(self, state_id: str) -> WizardState | None:
        return self._wizard_states.get(state_id)

    def list_wizard_states(self, session_id: str) -> list[WizardState]:
        return [
            s for s in self._wizard_states.values()
            if s.session_id == session_id
        ]

    # -- Cases --

    def save_case(self, case: Case) -> None:
        self._cases[case.id] = case

    def get_case(self, case_id: str) -> Case | None:
        return self._cases.get(case_id)

    def list_cases(self, session_id: str) -> list[Case]:
        return [
            c for c in self._cases.values()
            if c.session_id == session_id
        ]

    def list_all_cases(self) -> list[Case]:
        return list(self._cases.values())

    def list_cases_by_wizard(self, wizard_id: str) -> list[Case]:
        return [
            c for c in self._cases.values()
            if c.wizard_id == wizard_id
        ]
