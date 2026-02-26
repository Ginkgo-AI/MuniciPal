"""Config-driven wizard state machine engine."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from municipal.core.types import AuditEvent, DataClassification, SessionType
from municipal.governance.approval import ApprovalGate
from municipal.governance.audit import AuditLogger
from municipal.intake.models import (
    Case,
    FieldDefinition,
    FieldType,
    StepDefinition,
    StepState,
    StepStatus,
    WizardDefinition,
    WizardState,
)
from municipal.intake.store import IntakeStore
from municipal.intake.validation import ValidationEngine

_DEFAULT_WIZARDS_DIR = Path(__file__).resolve().parents[3] / "config" / "wizards"

# Map SessionType to a numeric tier for comparison
_SESSION_TIER_ORDER: dict[SessionType, int] = {
    SessionType.ANONYMOUS: 0,
    SessionType.VERIFIED: 1,
    SessionType.AUTHENTICATED: 2,
}


def _parse_field(data: dict[str, Any]) -> FieldDefinition:
    return FieldDefinition(
        id=data["id"],
        label=data.get("label", data["id"]),
        field_type=FieldType(data.get("type", "text")),
        required=data.get("required", False),
        validators=data.get("validators", []),
        options=data.get("options", []),
        placeholder=data.get("placeholder", ""),
        help_text=data.get("help_text", ""),
        classification=DataClassification(data.get("classification", "public")),
        show_if=data.get("show_if"),
    )


def _parse_step(data: dict[str, Any]) -> StepDefinition:
    fields = [_parse_field(f) for f in data.get("fields", [])]
    return StepDefinition(
        id=data["id"],
        title=data.get("title", data["id"]),
        description=data.get("description", ""),
        fields=fields,
        required_session_tier=SessionType(data.get("required_session_tier", "anonymous")),
        show_if=data.get("show_if"),
    )


def _load_wizard(path: Path) -> WizardDefinition:
    with open(path) as fh:
        data = yaml.safe_load(fh)
    steps = [_parse_step(s) for s in data.get("steps", [])]
    return WizardDefinition(
        id=data["id"],
        title=data.get("title", data["id"]),
        description=data.get("description", ""),
        steps=steps,
        approval_gate=data.get("approval_gate"),
        classification=DataClassification(data.get("classification", "public")),
    )


class WizardEngine:
    """Config-driven wizard state machine.

    Loads wizard definitions from YAML files in the wizards directory.
    Manages wizard lifecycle: start, step submission, navigation, and final submission.
    """

    def __init__(
        self,
        store: IntakeStore,
        validation_engine: ValidationEngine,
        audit_logger: AuditLogger | None = None,
        approval_gate: ApprovalGate | None = None,
        wizards_dir: str | Path | None = None,
    ) -> None:
        self._store = store
        self._validation = validation_engine
        self._audit = audit_logger
        self._approval = approval_gate
        self._wizards: dict[str, WizardDefinition] = {}
        self._load_wizards(Path(wizards_dir) if wizards_dir else _DEFAULT_WIZARDS_DIR)

    def _load_wizards(self, wizards_dir: Path) -> None:
        if not wizards_dir.exists():
            return
        for path in sorted(wizards_dir.glob("*.yml")):
            defn = _load_wizard(path)
            self._wizards[defn.id] = defn

    @property
    def wizard_definitions(self) -> dict[str, WizardDefinition]:
        return dict(self._wizards)

    def start_wizard(
        self, wizard_id: str, session_id: str, session_type: SessionType = SessionType.ANONYMOUS
    ) -> WizardState:
        """Start a new wizard instance.

        Returns:
            The initial WizardState with step states initialized.

        Raises:
            ValueError: If wizard_id is not found.
        """
        defn = self._wizards.get(wizard_id)
        if defn is None:
            raise ValueError(f"Unknown wizard: {wizard_id!r}")

        steps = []
        for i, step_def in enumerate(defn.steps):
            status = StepStatus.IN_PROGRESS if i == 0 else StepStatus.PENDING
            # Check show_if condition — auto-skip steps that don't apply
            steps.append(StepState(step_id=step_def.id, status=status))

        state = WizardState(
            wizard_id=wizard_id,
            session_id=session_id,
            current_step_index=0,
            steps=steps,
        )
        self._store.save_wizard_state(state)

        self._log_audit(session_id, "wizard_started", wizard_id, {"wizard_id": wizard_id})
        return state

    def submit_step(
        self,
        state_id: str,
        step_id: str,
        data: dict[str, Any],
        session_type: SessionType = SessionType.ANONYMOUS,
    ) -> WizardState:
        """Submit data for a wizard step.

        Validates data, saves if valid, and advances to the next step.

        Returns:
            Updated WizardState.

        Raises:
            KeyError: If state_id not found.
            ValueError: If step_id doesn't match current step or session tier insufficient.
        """
        state = self._store.get_wizard_state(state_id)
        if state is None:
            raise KeyError(f"Wizard state {state_id!r} not found")

        defn = self._wizards[state.wizard_id]
        current_step_state = state.steps[state.current_step_index]

        if current_step_state.step_id != step_id:
            raise ValueError(
                f"Expected step {current_step_state.step_id!r}, got {step_id!r}"
            )

        step_def = defn.steps[state.current_step_index]

        # Check session tier requirement
        required_tier = _SESSION_TIER_ORDER.get(step_def.required_session_tier, 0)
        current_tier = _SESSION_TIER_ORDER.get(session_type, 0)
        if current_tier < required_tier:
            raise ValueError(
                f"Step {step_id!r} requires session tier "
                f"{step_def.required_session_tier!r}, current is {session_type!r}"
            )

        # Validate
        result = self._validation.validate_step(step_def, data)
        if not result.valid:
            current_step_state.errors = result.errors
            current_step_state.data = data
            state.updated_at = datetime.now(timezone.utc)
            self._store.save_wizard_state(state)
            return state

        # Success — save data and advance
        current_step_state.data = data
        current_step_state.errors = {}
        current_step_state.status = StepStatus.COMPLETED
        state.updated_at = datetime.now(timezone.utc)

        self._log_audit(
            state.session_id, "step_completed", state.wizard_id,
            {"wizard_id": state.wizard_id, "step_id": step_id},
        )

        # Advance to next non-skipped step
        next_index = state.current_step_index + 1
        while next_index < len(state.steps):
            next_step_def = defn.steps[next_index]
            if self._should_skip_step(next_step_def, state):
                state.steps[next_index].status = StepStatus.SKIPPED
                next_index += 1
            else:
                break

        if next_index < len(state.steps):
            state.current_step_index = next_index
            state.steps[next_index].status = StepStatus.IN_PROGRESS
        else:
            state.current_step_index = len(state.steps) - 1

        self._store.save_wizard_state(state)
        return state

    def go_back(self, state_id: str) -> WizardState:
        """Go back to the previous step, preserving entered data.

        Raises:
            KeyError: If state_id not found.
            ValueError: If already at the first step.
        """
        state = self._store.get_wizard_state(state_id)
        if state is None:
            raise KeyError(f"Wizard state {state_id!r} not found")

        if state.current_step_index <= 0:
            raise ValueError("Already at the first step.")

        # Move back, skipping any skipped steps
        prev = state.current_step_index - 1
        while prev >= 0 and state.steps[prev].status == StepStatus.SKIPPED:
            prev -= 1

        if prev < 0:
            raise ValueError("No previous step to go back to.")

        state.steps[state.current_step_index].status = StepStatus.PENDING
        state.current_step_index = prev
        state.steps[prev].status = StepStatus.IN_PROGRESS
        state.updated_at = datetime.now(timezone.utc)
        self._store.save_wizard_state(state)
        return state

    def submit_wizard(
        self, state_id: str, session_id: str
    ) -> Case:
        """Submit a completed wizard, creating a Case.

        Merges all step data, determines classification, triggers approval gate,
        and logs audit event.

        Raises:
            KeyError: If state_id not found.
            ValueError: If wizard has uncompleted steps.
        """
        state = self._store.get_wizard_state(state_id)
        if state is None:
            raise KeyError(f"Wizard state {state_id!r} not found")

        defn = self._wizards[state.wizard_id]

        # Check all non-skipped steps are completed
        for step_state in state.steps:
            if step_state.status not in (StepStatus.COMPLETED, StepStatus.SKIPPED):
                raise ValueError(
                    f"Step {step_state.step_id!r} is not completed (status: {step_state.status})."
                )

        # Merge all step data
        merged_data: dict[str, Any] = {}
        for step_state in state.steps:
            merged_data.update(step_state.data)

        # Determine case classification (max of all field classifications)
        classification = self._compute_classification(defn)

        # Create case
        case = Case(
            wizard_id=state.wizard_id,
            session_id=session_id,
            data=merged_data,
            classification=classification,
        )

        # Trigger approval gate if configured
        if defn.approval_gate and self._approval:
            try:
                request = self._approval.request_approval(
                    gate_type=defn.approval_gate,
                    resource=f"case:{case.id}",
                    requestor=session_id,
                )
                case.approval_request_id = request.request_id
            except ValueError:
                pass  # Gate not configured — skip

        state.completed = True
        state.updated_at = datetime.now(timezone.utc)
        self._store.save_wizard_state(state)
        self._store.save_case(case)

        self._log_audit(
            session_id, "wizard_submitted", state.wizard_id,
            {"wizard_id": state.wizard_id, "case_id": case.id},
        )

        return case

    def _should_skip_step(self, step_def: StepDefinition, state: WizardState) -> bool:
        """Evaluate show_if condition for a step."""
        if step_def.show_if is None:
            return False

        # Gather all submitted data so far
        all_data: dict[str, Any] = {}
        for s in state.steps:
            all_data.update(s.data)

        field = step_def.show_if.get("field")
        expected = step_def.show_if.get("equals")
        if field and expected is not None:
            return all_data.get(field) != expected

        return False

    def _compute_classification(self, defn: WizardDefinition) -> DataClassification:
        """Compute max classification across all fields in the wizard."""
        order = {
            DataClassification.PUBLIC: 0,
            DataClassification.INTERNAL: 1,
            DataClassification.SENSITIVE: 2,
            DataClassification.RESTRICTED: 3,
        }
        max_level = order.get(defn.classification, 0)
        for step in defn.steps:
            for field in step.fields:
                level = order.get(field.classification, 0)
                if level > max_level:
                    max_level = level

        reverse = {v: k for k, v in order.items()}
        return reverse[max_level]

    def _log_audit(
        self, session_id: str, action: str, resource: str, details: dict[str, Any]
    ) -> None:
        if self._audit is None:
            return
        event = AuditEvent(
            session_id=session_id,
            actor=session_id,
            action=action,
            resource=resource,
            classification=DataClassification.INTERNAL,
            details=details,
        )
        self._audit.log(event)
