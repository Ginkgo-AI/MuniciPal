"""High-level RAG pipeline for Munici-Pal.

Composes DocumentIngester, Retriever, and CitationEngine into a single
facade that the rest of the application can use.
"""

from __future__ import annotations

from typing import Any

from municipal.classification.rules import ClassificationEngine
from municipal.core.config import Settings
from municipal.core.types import DataClassification
from municipal.llm.client import LLMClient, create_llm_client
from municipal.rag.citation import CitationEngine, CitedAnswer
from municipal.rag.ingest import DocumentIngester, IngestResult
from municipal.rag.retrieve import Retriever
from municipal.vectordb.store import VectorStore


class RAGPipeline:
    """Unified RAG pipeline combining ingestion, retrieval, and citation.

    Args:
        ingester: A DocumentIngester for loading files into the vector store.
        retriever: A Retriever for searching the vector store.
        citation_engine: A CitationEngine for generating cited answers.
    """

    def __init__(
        self,
        ingester: DocumentIngester,
        retriever: Retriever,
        citation_engine: CitationEngine,
    ) -> None:
        self.ingester = ingester
        self.retriever = retriever
        self.citation_engine = citation_engine

    def ingest(
        self,
        path: str,
        metadata: dict[str, Any] | None = None,
    ) -> IngestResult | list[IngestResult]:
        """Ingest a file or directory.

        If *path* points to a directory, all supported files within it are
        ingested and a list of results is returned. Otherwise a single
        IngestResult is returned.
        """
        from pathlib import Path as _Path

        p = _Path(path)
        if p.is_dir():
            return self.ingester.ingest_directory(path, metadata)
        return self.ingester.ingest_file(path, metadata)

    async def ask(
        self,
        question: str,
        collection: str = "ordinances",
        max_classification: DataClassification = DataClassification.PUBLIC,
        history: list[dict] | None = None,
    ) -> CitedAnswer:
        """Ask a question and get a cited answer.

        Args:
            question: The resident's question.
            collection: The vector store collection to search.
            max_classification: Maximum classification level for retrieval.
            history: Optional list of prior messages for conversation context.

        Returns:
            A CitedAnswer with the LLM response, citations, and confidence.
        """
        return await self.citation_engine.answer(
            question=question,
            collection=collection,
            max_classification=max_classification,
            history=history,
        )


def create_rag_pipeline(
    settings: Settings,
    llm_client: LLMClient | None = None,
    classification_engine: ClassificationEngine | None = None,
) -> RAGPipeline:
    """Factory function to build a fully-wired RAGPipeline from settings.

    Args:
        settings: Application settings.
        llm_client: Optional pre-built LLMClient. If not provided, one is
            created from ``settings.llm``.
        classification_engine: Optional pre-built ClassificationEngine.
            If not provided, a default one is created.

    Returns:
        A ready-to-use RAGPipeline instance.
    """
    store = VectorStore(config=settings.vectordb)

    if classification_engine is None:
        classification_engine = ClassificationEngine()

    if llm_client is None:
        llm_client = create_llm_client(settings.llm)

    ingester = DocumentIngester(store, classification_engine)
    retriever = Retriever(store)
    citation_engine = CitationEngine(llm_client, retriever)

    return RAGPipeline(ingester, retriever, citation_engine)
