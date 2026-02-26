"""Chat service wiring RAG pipeline, session management, and audit logging.

This is the primary entry point for handling a user's chat message. It
coordinates the RAG pipeline call, session bookkeeping, and audit trail.
"""

from __future__ import annotations

import logging

from municipal.chat.session import ChatMessage, MessageRole, SessionManager
from municipal.core.types import AuditEvent, DataClassification
from municipal.governance.audit import AuditLogger
from municipal.rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

_KILL_SWITCH_MESSAGE = (
    "\n\n---\n"
    "I'm not confident enough in this answer to provide it as reliable "
    "information. Please contact city staff directly for assistance with "
    "this question."
)


class ChatService:
    """Orchestrates chat interactions across RAG, sessions, and audit.

    Args:
        rag_pipeline: The RAGPipeline for answering questions.
        session_manager: The SessionManager for session state.
        audit_logger: The AuditLogger for governance logging.
    """

    def __init__(
        self,
        rag_pipeline: RAGPipeline,
        session_manager: SessionManager,
        audit_logger: AuditLogger,
    ) -> None:
        self._rag = rag_pipeline
        self._sessions = session_manager
        self._audit = audit_logger

    async def respond(
        self,
        session_id: str,
        user_message: str,
        collection: str = "default",
    ) -> ChatMessage:
        """Process a user message and return an assistant response.

        Steps:
            1. Record the user message in the session.
            2. Call the RAG pipeline to generate a cited answer.
            3. If confidence is low, append the kill-switch disclaimer.
            4. Record the assistant response in the session.
            5. Log the interaction to the audit trail.

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

        return assistant_msg
