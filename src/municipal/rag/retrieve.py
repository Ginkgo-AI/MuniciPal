"""Retrieval with confidence scoring for Munici-Pal RAG.

Wraps VectorStore.query and converts raw ChromaDB distances into
normalised 0-1 confidence scores.
"""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, Field

from municipal.core.types import DataClassification
from municipal.vectordb.store import VectorStore


class RetrievalResult(BaseModel):
    """A single retrieval result with confidence scoring."""

    content: str
    source: str
    chunk_id: str
    distance: float
    confidence_score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


def distance_to_confidence(distance: float) -> float:
    """Convert a ChromaDB L2 distance to a 0-1 confidence score.

    Uses an exponential decay: ``confidence = exp(-distance / 2)``.
    A distance of 0 yields confidence 1.0; larger distances approach 0.

    Returns:
        A float clamped to [0.0, 1.0].
    """
    score = math.exp(-distance / 2.0)
    return max(0.0, min(1.0, score))


class Retriever:
    """Retrieval layer with confidence scoring.

    Args:
        vector_store: A VectorStore instance to query against.
    """

    def __init__(self, vector_store: VectorStore) -> None:
        self._store = vector_store

    def retrieve(
        self,
        query: str,
        collection: str,
        n_results: int = 5,
        max_classification: DataClassification = DataClassification.PUBLIC,
    ) -> list[RetrievalResult]:
        """Retrieve relevant chunks for *query* with confidence scores.

        Args:
            query: The search query.
            collection: The collection to search.
            n_results: Maximum results to return.
            max_classification: Maximum classification level the caller may see.

        Returns:
            A list of RetrievalResult instances sorted by confidence (descending).
        """
        search_results = self._store.query(
            query_text=query,
            collection=collection,
            n_results=n_results,
            max_classification=max_classification,
        )

        results: list[RetrievalResult] = []
        for sr in search_results:
            confidence = distance_to_confidence(sr.distance)
            source = sr.metadata.get("source_file", "unknown")
            results.append(
                RetrievalResult(
                    content=sr.content,
                    source=source,
                    chunk_id=sr.document_id,
                    distance=sr.distance,
                    confidence_score=confidence,
                    metadata=sr.metadata,
                )
            )

        # Sort by confidence descending
        results.sort(key=lambda r: r.confidence_score, reverse=True)
        return results
