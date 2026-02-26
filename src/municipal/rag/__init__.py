"""RAG pipeline for Munici-Pal Digital Librarian (Phase 1).

Provides document ingestion, retrieval with confidence scoring,
citation-backed answer generation, and a high-level pipeline that
ties them together.
"""

from municipal.rag.citation import CitationEngine, CitedAnswer, Citation
from municipal.rag.ingest import DocumentIngester, IngestResult
from municipal.rag.pipeline import RAGPipeline, create_rag_pipeline
from municipal.rag.retrieve import Retriever, RetrievalResult

__all__ = [
    "CitationEngine",
    "CitedAnswer",
    "Citation",
    "DocumentIngester",
    "IngestResult",
    "RAGPipeline",
    "RetrievalResult",
    "Retriever",
    "create_rag_pipeline",
]
