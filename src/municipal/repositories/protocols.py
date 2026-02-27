"""Protocol definitions for all repository interfaces.

Each protocol mirrors the public methods of the corresponding in-memory
store class exactly, enabling both sync (in-memory) and async (Postgres)
implementations to satisfy the same interface.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from municipal.chat.session import ChatMessage, ChatSession
from municipal.core.types import ApprovalStatus, AuditEvent, SessionType
from municipal.finance.models import PaymentRecord
from municipal.governance.approval import ApprovalRequest, GateDefinition
from municipal.governance.audit import AuditEntry
from municipal.graph.models import Edge, EntityType, Node, RelationshipType
from municipal.intake.models import Case, WizardState
from municipal.notifications.models import Notification
from municipal.web.mission_control import FeedbackEntry, ShadowComparisonResult


@runtime_checkable
class SessionRepository(Protocol):
    """Protocol for session storage."""

    def create_session(
        self, session_type: SessionType = SessionType.ANONYMOUS
    ) -> ChatSession: ...

    def get_session(self, session_id: str) -> ChatSession | None: ...

    def add_message(self, session_id: str, message: ChatMessage) -> None: ...

    def list_active_sessions(self) -> list[ChatSession]: ...


@runtime_checkable
class IntakeRepository(Protocol):
    """Protocol for wizard states and cases storage."""

    def save_wizard_state(self, state: WizardState) -> None: ...

    def get_wizard_state(self, state_id: str) -> WizardState | None: ...

    def list_wizard_states(self, session_id: str) -> list[WizardState]: ...

    def save_case(self, case: Case) -> None: ...

    def get_case(self, case_id: str) -> Case | None: ...

    def list_cases(self, session_id: str) -> list[Case]: ...

    def list_all_cases(self) -> list[Case]: ...

    def list_cases_by_wizard(self, wizard_id: str) -> list[Case]: ...

    @property
    def case_count(self) -> int: ...


@runtime_checkable
class ApprovalRepository(Protocol):
    """Protocol for approval request storage.

    Note: The ApprovalGate retains business logic and YAML config.
    This protocol covers CRUD on approval requests only.
    """

    def request_approval(
        self, gate_type: str, resource: str, requestor: str
    ) -> ApprovalRequest: ...

    def approve(self, request_id: str, approver: str) -> ApprovalRequest: ...

    def deny(
        self, request_id: str, approver: str, reason: str
    ) -> ApprovalRequest: ...

    def check_status(self, request_id: str) -> ApprovalStatus: ...

    def get_request(self, request_id: str) -> ApprovalRequest: ...

    def get_gate(self, gate_type: str) -> GateDefinition | None: ...

    @property
    def gates(self) -> dict[str, GateDefinition]: ...

    @property
    def pending_requests(self) -> list[ApprovalRequest]: ...

    def list_all_requests(self) -> list[ApprovalRequest]: ...


@runtime_checkable
class GraphRepository(Protocol):
    """Protocol for entity graph storage."""

    def add_node(self, node: Node) -> None: ...

    def get_node(self, node_id: str) -> Node | None: ...

    def add_edge(self, edge: Edge) -> None: ...

    def get_neighbors(
        self, node_id: str, relationship: RelationshipType | None = None
    ) -> list[Node]: ...

    def query(
        self,
        entity_type: EntityType | None = None,
        relationship: RelationshipType | None = None,
        from_node: str | None = None,
    ) -> list[Node]: ...

    @property
    def node_count(self) -> int: ...

    @property
    def edge_count(self) -> int: ...


@runtime_checkable
class NotificationRepository(Protocol):
    """Protocol for notification storage."""

    def save(self, notification: Notification) -> Notification: ...

    def get(self, notification_id: str) -> Notification | None: ...

    def list_for_session(self, session_id: str) -> list[Notification]: ...

    def list_all(self) -> list[Notification]: ...

    @property
    def count(self) -> int: ...


@runtime_checkable
class FeedbackRepository(Protocol):
    """Protocol for staff feedback storage."""

    def add(self, entry: FeedbackEntry) -> FeedbackEntry: ...

    def list_all(self) -> list[FeedbackEntry]: ...

    def get_for_session(self, session_id: str) -> list[FeedbackEntry]: ...

    def get_by_id(self, feedback_id: str) -> FeedbackEntry | None: ...

    def count(self) -> int: ...

    def clear(self) -> None: ...


@runtime_checkable
class ShadowComparisonRepository(Protocol):
    """Protocol for shadow comparison results storage."""

    def add(self, result: ShadowComparisonResult) -> ShadowComparisonResult: ...

    def list_all(self) -> list[ShadowComparisonResult]: ...

    def get_for_session(self, session_id: str) -> list[ShadowComparisonResult]: ...

    def stats(self) -> dict[str, Any]: ...

    def clear(self) -> None: ...


@runtime_checkable
class PaymentRepository(Protocol):
    """Protocol for payment record storage."""

    def save(self, record: PaymentRecord) -> PaymentRecord: ...

    def get(self, payment_id: str) -> PaymentRecord | None: ...

    def get_for_case(self, case_id: str) -> list[PaymentRecord]: ...

    def list_all(self) -> list[PaymentRecord]: ...


@runtime_checkable
class AuditRepository(Protocol):
    """Protocol for audit logging."""

    def log(self, event: AuditEvent) -> AuditEntry: ...

    def verify_chain(self) -> bool: ...

    def query(self, filters: dict[str, Any] | None = None) -> list[AuditEvent]: ...


@runtime_checkable
class AuthTokenRepository(Protocol):
    """Protocol for auth token storage."""

    def save_token(
        self, token: str, user_id: str, tier: str, display_name: str, expires_at: Any
    ) -> None: ...

    def get_token(self, token: str) -> dict[str, Any] | None: ...

    def delete_token(self, token: str) -> bool: ...


@runtime_checkable
class TakeoverRepository(Protocol):
    """Protocol for session takeover management."""

    def takeover(self, session_id: str, staff_id: str) -> dict[str, Any]: ...

    def release(self, session_id: str) -> dict[str, Any]: ...

    def is_taken_over(self, session_id: str) -> bool: ...

    def get_controller(self, session_id: str) -> str | None: ...

    def list_takeovers(self) -> dict[str, str]: ...
