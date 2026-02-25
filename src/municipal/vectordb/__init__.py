"""Vector database module for Munici-Pal.

Provides classification-aware vector storage and retrieval using ChromaDB.
"""

from municipal.vectordb.embeddings import EmbeddingProvider, OllamaEmbedding
from municipal.vectordb.store import Document, SearchResult, VectorStore

__all__ = [
    "Document",
    "EmbeddingProvider",
    "OllamaEmbedding",
    "SearchResult",
    "VectorStore",
]
