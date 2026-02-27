"""Chat service wiring RAG pipeline, session management, and audit logging.

This is the primary entry point for handling a user's chat message. It
coordinates the RAG pipeline call, session bookkeeping, and audit trail.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, TYPE_CHECKING

from municipal.chat.session import ChatMessage, MessageRole, SessionManager
from municipal.core.types import AuditEvent, DataClassification
from municipal.governance.audit import AuditLogger
from municipal.rag.pipeline import RAGPipeline

if TYPE_CHECKING:
    from municipal.llm.client import LLMClient
    from municipal.web.mission_control import ShadowComparisonStore, ShadowModeManager
    from municipal.web.mission_control_v1 import SessionTakeoverManager

logger = logging.getLogger(__name__)

_KILL_SWITCH_MESSAGE = (
    "\n\n---\n"
    "I'm not confident enough in this answer to provide it as reliable "
    "information. Please contact city staff directly for assistance with "
    "this question."
)

_TAKEOVER_MESSAGE = (
    "This session is currently being handled by a staff member. "
    "Please wait for their response."
)


class ChatService:
    """Orchestrates chat interactions across RAG, sessions, and audit.

    Args:
        rag_pipeline: The RAGPipeline for answering questions.
        session_manager: The SessionManager for session state.
        audit_logger: The AuditLogger for governance logging.
        shadow_manager: Optional ShadowModeManager for shadow comparisons.
        comparison_store: Optional ShadowComparisonStore for logging comparisons.
        takeover_manager: Optional SessionTakeoverManager for staff takeover.
    """

    def __init__(
        self,
        rag_pipeline: RAGPipeline,
        session_manager: SessionManager,
        audit_logger: AuditLogger,
        shadow_manager: ShadowModeManager | None = None,
        comparison_store: ShadowComparisonStore | None = None,
        takeover_manager: SessionTakeoverManager | None = None,
    ) -> None:
        self._rag = rag_pipeline
        self._sessions = session_manager
        self._audit = audit_logger
        self._shadow_manager = shadow_manager
        self._comparison_store = comparison_store
        self._takeover_manager = takeover_manager
        self._background_tasks: set[asyncio.Task] = set()

    async def respond(
        self,
        session_id: str,
        user_message: str,
        collection: str = "default",
    ) -> ChatMessage:
        """Process a user message and return an assistant response.

        Steps:
            1. Check if session is taken over by staff; if so, return placeholder.
            2. Record the user message in the session.
            3. Call the RAG pipeline to generate a cited answer.
            4. If confidence is low, append the kill-switch disclaimer.
            5. Record the assistant response in the session.
            6. Log the interaction to the audit trail.
            7. If shadow mode active, fire-and-forget comparison.

        Args:
            session_id: The UUID of the chat session.
            user_message: The text of the user's question.
            collection: The vector store collection to search.

        Returns:
            The assistant ChatMessage with citations and confidence.

        Raises:
            KeyError: If the session_id does not exist.
        """
        # Verify session exists
        session = self._sessions.get_session(session_id)
        if session is None:
            raise KeyError(f"Session {session_id!r} not found")

        # Check for staff takeover
        if self._takeover_manager and self._takeover_manager.is_taken_over(session_id):
            user_msg = ChatMessage(role=MessageRole.USER, content=user_message)
            self._sessions.add_message(session_id, user_msg)

            takeover_msg = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=_TAKEOVER_MESSAGE,
                confidence=1.0,
                low_confidence=False,
            )
            self._sessions.add_message(session_id, takeover_msg)
            return takeover_msg

        # 1. Log the user message
        user_msg = ChatMessage(role=MessageRole.USER, content=user_message)
        self._sessions.add_message(session_id, user_msg)

        # 2. Call RAG pipeline
        try:
            cited_answer = await self._rag.ask(
                question=user_message,
                collection=collection,
                max_classification=DataClassification.PUBLIC,
            )
        except Exception:
            logger.exception("RAG pipeline error for session %s", session_id)
            error_msg = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=(
                    "I'm sorry, I encountered an error processing your "
                    "question. Please try again or contact city staff "
                    "for assistance."
                ),
                confidence=0.0,
                low_confidence=True,
            )
            self._sessions.add_message(session_id, error_msg)
            return error_msg

        # 3. Build response content
        answer_text = cited_answer.answer
        if cited_answer.low_confidence:
            answer_text += _KILL_SWITCH_MESSAGE

        # Serialize citations for the message
        citation_dicts = [
            {
                "source": c.source,
                "section": c.section,
                "quote": c.quote,
                "relevance_score": c.relevance_score,
            }
            for c in cited_answer.citations
        ]

        # 4. Create assistant message
        assistant_msg = ChatMessage(
            role=MessageRole.ASSISTANT,
            content=answer_text,
            citations=citation_dicts if citation_dicts else None,
            confidence=cited_answer.confidence,
            low_confidence=cited_answer.low_confidence,
        )
        self._sessions.add_message(session_id, assistant_msg)

        # 5. Audit log
        self._audit.log(
            AuditEvent(
                session_id=session_id,
                actor="resident",
                action="chat_response",
                resource=collection,
                classification=DataClassification.PUBLIC,
                details={
                    "question": user_message,
                    "confidence": cited_answer.confidence,
                    "sources_used": cited_answer.sources_used,
                    "low_confidence": cited_answer.low_confidence,
                    "citation_count": len(cited_answer.citations),
                },
                data_sources=[c.source for c in cited_answer.citations],
            )
        )

        # 6. Fire-and-forget shadow comparison if active
        if (
            self._shadow_manager
            and self._comparison_store
            and self._shadow_manager.is_active(session_id)
            and self._shadow_manager.shadow_llm_config is not None
        ):
            task = asyncio.create_task(
                self._run_shadow_comparison(
                    session_id=session_id,
                    user_message=user_message,
                    production_response=answer_text,
                )
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        return assistant_msg

    async def _run_shadow_comparison(
        self,
        session_id: str,
        user_message: str,
        production_response: str,
    ) -> None:
        """Run the candidate model and log a comparison result."""
        from municipal.llm.client import create_llm_client
        from municipal.web.mission_control import ShadowComparisonResult

        try:
            config = self._shadow_manager.shadow_llm_config  # type: ignore[union-attr]
            client = create_llm_client(config)
            try:
                candidate_response = await client.generate(user_message)
            finally:
                await client.close()

            diverged = candidate_response.strip() != production_response.strip()
            result = ShadowComparisonResult(
                session_id=session_id,
                user_message=user_message,
                production_response=production_response,
                candidate_response=candidate_response,
                diverged=diverged,
            )
            self._comparison_store.add(result)  # type: ignore[union-attr]
        except Exception:
            logger.exception("Shadow comparison failed for session %s", session_id)
