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
from municipal.rag.retrieve import Retriever

# Confidence threshold below which the kill-switch fires.
_LOW_CONFIDENCE_THRESHOLD = 0.5

_SYSTEM_PROMPT = """\
You are a helpful municipal government assistant. Answer the resident's \
question using ONLY the context provided below. Do not use outside knowledge.

For every claim you make, cite the source using the format [Source: <filename>].

If you cannot find the answer in the provided context, say: \
"I cannot find the specific policy. Let me connect you with a staff member."

Context:
{context}
"""


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


def _build_context_block(results: list[Any]) -> str:
    """Format retrieval results into a context block for the LLM prompt."""
    blocks: list[str] = []
    for i, r in enumerate(results, 1):
        section = r.metadata.get("section_header", "")
        header = f" (Section: {section})" if section else ""
        blocks.append(
            f"[{i}] Source: {r.source}{header}\n{r.content}"
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
    ) -> CitedAnswer:
        """Answer a question with citations from the vector store.

        Retrieves relevant chunks, builds a prompt, calls the LLM, parses
        citations, and computes overall confidence. If confidence is below
        the threshold, sets ``low_confidence=True`` to trigger the
        hallucination kill-switch.

        Args:
            question: The resident's question.
            collection: The vector store collection to search.
            max_classification: Maximum classification level for retrieval.

        Returns:
            A CitedAnswer with the LLM response, citations, and confidence.
        """
        # Retrieve relevant chunks
        results = self._retriever.retrieve(
            query=question,
            collection=collection,
            n_results=5,
            max_classification=max_classification,
        )

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
        system_prompt = _SYSTEM_PROMPT.format(context=context_block)

        # Call LLM
        answer_text = await self._llm.generate(
            prompt=question,
            system_prompt=system_prompt,
            temperature=0.1,
        )

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
