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

    def retrieve_with_neighbors(
        self,
        query: str,
        collection: str,
        n_results: int = 5,
        neighbor_window: int = 1,
        max_classification: DataClassification = DataClassification.PUBLIC,
    ) -> list[RetrievalResult]:
        """Retrieve chunks with neighboring context expansion.

        For each matched chunk, also fetches the ±*neighbor_window* chunks
        from the same source file (by chunk_index). This provides surrounding
        context that dramatically improves answer quality for legal text.

        Args:
            query: The search query.
            collection: The collection to search.
            n_results: Maximum primary results to return.
            neighbor_window: Number of neighboring chunks to include on each side.
            max_classification: Maximum classification level the caller may see.

        Returns:
            A list of RetrievalResult instances, with neighbors merged in,
            sorted by confidence (descending). Duplicates are removed.
        """
        primary = self.retrieve(
            query=query,
            collection=collection,
            n_results=n_results,
            max_classification=max_classification,
        )

        if not primary or neighbor_window <= 0:
            return primary

        # Collect neighbor chunk indices we need per source file
        needed: dict[str, set[int]] = {}
        for r in primary:
            source = r.source
            idx = r.metadata.get("chunk_index")
            if idx is None:
                continue
            if source not in needed:
                needed[source] = set()
            for offset in range(-neighbor_window, neighbor_window + 1):
                neighbor_idx = idx + offset
                if neighbor_idx >= 0:
                    needed[source].add(neighbor_idx)

        # Fetch a wider set of chunks to find neighbors
        all_results = self.retrieve(
            query=query,
            collection=collection,
            n_results=n_results * 3,
            max_classification=max_classification,
        )

        # Build lookup by (source, chunk_index)
        seen_ids: set[str] = set()
        merged: list[RetrievalResult] = []

        # Add primary results first
        for r in primary:
            if r.chunk_id not in seen_ids:
                seen_ids.add(r.chunk_id)
                merged.append(r)

        # Add neighbors from the wider search
        for r in all_results:
            if r.chunk_id in seen_ids:
                continue
            source = r.source
            idx = r.metadata.get("chunk_index")
            if source in needed and idx in needed.get(source, set()):
                seen_ids.add(r.chunk_id)
                merged.append(r)

        # Sort by source then chunk_index for coherent context ordering
        merged.sort(
            key=lambda r: (r.source, r.metadata.get("chunk_index", 0)),
        )
        return merged
