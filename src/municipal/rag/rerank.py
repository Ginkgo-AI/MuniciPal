"""Lightweight re-ranking service for retrieval results.

Re-scores candidates using a combination of vector distance (from ChromaDB)
and keyword overlap with the query.  This avoids needing external models
while still improving relevance over pure vector search.
"""

from __future__ import annotations

import re
from collections import Counter

from municipal.rag.retrieve import RetrievalResult


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokeniser."""
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _keyword_overlap(query_tokens: list[str], content_tokens: list[str]) -> float:
    """Fraction of query tokens found in content (0-1)."""
    if not query_tokens:
        return 0.0
    query_set = set(query_tokens)
    content_counter = Counter(content_tokens)
    hits = sum(1 for t in query_set if content_counter[t] > 0)
    return hits / len(query_set)


def _content_quality(text: str) -> float:
    """Heuristic quality score (0-1) based on length and information density."""
    if not text:
        return 0.0
    length_score = min(len(text) / 800, 1.0)  # Prefer substantial chunks
    alpha_ratio = sum(1 for c in text if c.isalpha()) / max(len(text), 1)
    return 0.5 * length_score + 0.5 * alpha_ratio


def rerank(
    query: str,
    results: list[RetrievalResult],
    final_count: int = 5,
    vector_weight: float = 0.5,
    keyword_weight: float = 0.35,
    quality_weight: float = 0.15,
) -> list[RetrievalResult]:
    """Re-rank retrieval results using a weighted scoring formula.

    Score = vector_weight * confidence + keyword_weight * keyword_overlap
            + quality_weight * content_quality

    Args:
        query: The original search query.
        results: Candidate retrieval results.
        final_count: Number of results to return.
        vector_weight: Weight for vector similarity score.
        keyword_weight: Weight for keyword overlap score.
        quality_weight: Weight for content quality score.

    Returns:
        Top ``final_count`` results, re-ranked by combined score.
    """
    if len(results) <= final_count:
        return results

    query_tokens = _tokenize(query)

    scored: list[tuple[float, RetrievalResult]] = []
    for r in results:
        content_tokens = _tokenize(r.content)
        kw_score = _keyword_overlap(query_tokens, content_tokens)
        q_score = _content_quality(r.content)
        combined = (
            vector_weight * r.confidence_score
            + keyword_weight * kw_score
            + quality_weight * q_score
        )
        scored.append((combined, r))

    scored.sort(key=lambda x: x[0], reverse=True)

    reranked = []
    for score, r in scored[:final_count]:
        reranked.append(
            RetrievalResult(
                content=r.content,
                source=r.source,
                chunk_id=r.chunk_id,
                distance=r.distance,
                confidence_score=score,
                metadata=r.metadata,
            )
        )
    return reranked
