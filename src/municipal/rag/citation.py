"""Citation engine for Munici-Pal RAG.

Builds LLM prompts from retrieved context, generates answers with inline
citations, parses them, and enforces the hallucination kill-switch when
confidence is too low (ROADMAP.md Section 6.3).
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from municipal.core.types import DataClassification
from municipal.llm.client import LLMClient
from municipal.rag.rerank import rerank
from municipal.rag.retrieve import Retriever

# Confidence threshold below which the kill-switch fires.
_LOW_CONFIDENCE_THRESHOLD = 0.5

_SYSTEM_PROMPT = """\
You are a helpful municipal government assistant. Answer the resident's \
question using ONLY the context provided below. Do not use outside knowledge.

For every claim you make, cite the source using the format [Source: <source name>].

If you cannot find the answer in the provided context, say: \
"I cannot find the specific policy. Let me connect you with a staff member."

Do NOT include any <think> or reasoning tags in your answer.

{history_block}Context:
{context}

/no_think
"""


def _strip_think_tokens(text: str) -> str:
    """Remove <think>...</think> blocks emitted by reasoning models."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _friendly_source(raw_path: str) -> str:
    """Convert a raw file path into a human-readable source name."""
    import os
    basename = os.path.splitext(os.path.basename(raw_path))[0]
    return basename.replace("_", " ").title()


class Citation(BaseModel):
    """A single citation reference extracted from an LLM answer."""

    source: str
    section: str | None = None
    quote: str
    relevance_score: float = 0.0


class CitedAnswer(BaseModel):
    """An answer with extracted citations and confidence metadata."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = 0.0
    sources_used: int = 0
    low_confidence: bool = False


def _format_history(history: list[dict] | None, max_turns: int = 5) -> str:
    """Format conversation history into a prompt block.

    Returns an empty string if no history, or a formatted block like:
        Conversation History:
        User: ...
        Assistant: ...
    """
    if not history:
        return ""
    # Take last N turns
    recent = history[-max_turns * 2:] if len(history) > max_turns * 2 else history
    lines = []
    for msg in recent:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        if content:
            lines.append(f"{role}: {content}")
    if not lines:
        return ""
    return "Conversation History:\n" + "\n".join(lines) + "\n\n"


def _build_context_block(results: list[Any]) -> str:
    """Format retrieval results into a context block for the LLM prompt."""
    blocks: list[str] = []
    for i, r in enumerate(results, 1):
        friendly = _friendly_source(r.source)
        section = r.metadata.get("section_header", "")
        header = f" (Section: {section})" if section else ""
        blocks.append(
            f"[{i}] Source: {friendly}{header}\n{r.content}"
        )
    return "\n\n".join(blocks)


def _parse_citations(
    answer_text: str,
    retrieval_results: list[Any],
) -> list[Citation]:
    """Extract [Source: ...] citations from the LLM answer text.

    Matches each cited source back to a retrieval result to populate the
    quote and relevance_score fields.
    """
    # Build a lookup by source filename
    source_lookup: dict[str, Any] = {}
    for r in retrieval_results:
        source_lookup[r.source] = r

    pattern = re.compile(r"\[Source:\s*([^\]]+)\]")
    seen: set[str] = set()
    citations: list[Citation] = []

    for match in pattern.finditer(answer_text):
        source_name = match.group(1).strip()
        if source_name in seen:
            continue
        seen.add(source_name)

        rr = source_lookup.get(source_name)
        quote = ""
        relevance = 0.0
        section = None
        if rr is not None:
            quote = rr.content[:200]
            relevance = rr.confidence_score
            section = rr.metadata.get("section_header")

        citations.append(
            Citation(
                source=source_name,
                section=section,
                quote=quote,
                relevance_score=relevance,
            )
        )

    return citations


class CitationEngine:
    """Generates cited answers by combining retrieval with LLM generation.

    Args:
        llm_client: An LLMClient for text generation.
        retriever: A Retriever for fetching relevant context.
    """

    def __init__(self, llm_client: LLMClient, retriever: Retriever) -> None:
        self._llm = llm_client
        self._retriever = retriever

    async def answer(
        self,
        question: str,
        collection: str,
        max_classification: DataClassification = DataClassification.PUBLIC,
        history: list[dict] | None = None,
    ) -> CitedAnswer:
        """Answer a question with citations from the vector store.

        Retrieves relevant chunks (with neighboring context), builds a prompt
        including conversation history, calls the LLM, parses citations, and
        computes overall confidence. If confidence is below the threshold,
        sets ``low_confidence=True`` to trigger the hallucination kill-switch.

        Args:
            question: The resident's question.
            collection: The vector store collection to search.
            max_classification: Maximum classification level for retrieval.
            history: Optional list of prior messages [{"role": ..., "content": ...}].

        Returns:
            A CitedAnswer with the LLM response, citations, and confidence.
        """
        # Retrieve relevant chunks with ±1 neighboring context
        # Over-fetch for re-ranking: retrieve 10, re-rank to 5
        results = self._retriever.retrieve_with_neighbors(
            query=question,
            collection=collection,
            n_results=10,
            neighbor_window=1,
            max_classification=max_classification,
        )

        # Re-rank using keyword overlap + content quality scoring
        results = rerank(query=question, results=results, final_count=5)

        if not results:
            return CitedAnswer(
                answer=(
                    "I cannot find the specific policy. "
                    "Let me connect you with a staff member."
                ),
                citations=[],
                confidence=0.0,
                sources_used=0,
                low_confidence=True,
            )

        # Build prompt context
        context_block = _build_context_block(results)
        history_block = _format_history(history)
        system_prompt = _SYSTEM_PROMPT.format(
            context=context_block,
            history_block=history_block,
        )

        # Call LLM
        raw_answer = await self._llm.generate(
            prompt=question,
            system_prompt=system_prompt,
            temperature=0.1,
        )
        answer_text = _strip_think_tokens(raw_answer)

        # Parse citations
        citations = _parse_citations(answer_text, results)

        # Compute overall confidence from retrieval scores of cited sources
        cited_sources = {c.source for c in citations}
        cited_confidences = [
            r.confidence_score for r in results if r.source in cited_sources
        ]
        if cited_confidences:
            avg_confidence = sum(cited_confidences) / len(cited_confidences)
        else:
            # If no citations were parsed, use average of all retrieval scores
            avg_confidence = (
                sum(r.confidence_score for r in results) / len(results)
            )

        low_confidence = avg_confidence < _LOW_CONFIDENCE_THRESHOLD

        return CitedAnswer(
            answer=answer_text,
            citations=citations,
            confidence=avg_confidence,
            sources_used=len(cited_sources) if cited_sources else len(results),
            low_confidence=low_confidence,
        )

    async def answer_stream(
        self,
        question: str,
        collection: str,
        max_classification: DataClassification = DataClassification.PUBLIC,
        history: list[dict] | None = None,
    ):
        """Stream an answer token-by-token as an async generator.

        Yields dicts suitable for SSE events:
          {"type": "token", "data": "..."}
          {"type": "citations", "data": [...]}
          {"type": "metadata", "data": {"confidence": ..., "low_confidence": ...}}
          {"type": "done"}
        """
        import re as _re

        # Retrieve and re-rank
        results = self._retriever.retrieve_with_neighbors(
            query=question,
            collection=collection,
            n_results=10,
            neighbor_window=1,
            max_classification=max_classification,
        )
        results = rerank(query=question, results=results, final_count=5)

        if not results:
            yield {
                "type": "token",
                "data": "I cannot find the specific policy. Let me connect you with a staff member.",
            }
            yield {"type": "metadata", "data": {"confidence": 0.0, "low_confidence": True}}
            yield {"type": "done"}
            return

        # Build prompt
        context_block = _build_context_block(results)
        history_block = _format_history(history)
        system_prompt = _SYSTEM_PROMPT.format(
            context=context_block,
            history_block=history_block,
        )

        # Stream tokens from LLM
        full_answer = ""
        async for token in self._llm.generate_stream(
            prompt=question,
            system_prompt=system_prompt,
            temperature=0.1,
        ):
            # Strip think tokens progressively
            full_answer += token
            yield {"type": "token", "data": token}

        # Clean up think tokens from the accumulated answer
        clean_answer = _strip_think_tokens(full_answer)

        # Parse citations from the full answer
        citations = _parse_citations(clean_answer, results)

        # Compute confidence
        cited_sources = {c.source for c in citations}
        cited_confidences = [
            r.confidence_score for r in results if r.source in cited_sources
        ]
        if cited_confidences:
            avg_confidence = sum(cited_confidences) / len(cited_confidences)
        else:
            avg_confidence = sum(r.confidence_score for r in results) / len(results)

        low_confidence = avg_confidence < _LOW_CONFIDENCE_THRESHOLD

        # Emit citations and metadata
        yield {
            "type": "citations",
            "data": [
                {
                    "source": c.source,
                    "section": c.section,
                    "quote": c.quote,
                    "relevance_score": c.relevance_score,
                }
                for c in citations
            ],
        }
        yield {
            "type": "metadata",
            "data": {
                "confidence": avg_confidence,
                "low_confidence": low_confidence,
                "sources_used": len(cited_sources) if cited_sources else len(results),
            },
        }
        yield {"type": "done"}
