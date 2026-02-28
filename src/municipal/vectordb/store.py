"""Vector store abstraction for Munici-Pal.

Wraps ChromaDB to provide classification-aware document storage and retrieval.
Documents are tagged with their DataClassification level, and queries can
filter by the maximum classification level the caller is authorized to see.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from municipal.core.config import VectorDBConfig
from municipal.core.types import DataClassification


class Document(BaseModel):
    """A document to be stored in the vector database."""

    id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    classification: DataClassification = DataClassification.PUBLIC


class SearchResult(BaseModel):
    """A single search result returned from a vector query."""

    document_id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    classification: DataClassification = DataClassification.PUBLIC
    distance: float = 0.0


# Classification level ordering for filtering
_LEVEL_ORDER: dict[DataClassification, int] = {
    DataClassification.PUBLIC: 1,
    DataClassification.INTERNAL: 2,
    DataClassification.SENSITIVE: 3,
    DataClassification.RESTRICTED: 4,
}


class VectorStore:
    """Classification-aware vector store backed by ChromaDB.

    Args:
        config: VectorDBConfig instance. Defaults to VectorDBConfig().
        client: Optional pre-configured ChromaDB client. If not provided,
            a persistent client is created using the config settings.
    """

    def __init__(
        self,
        config: VectorDBConfig | None = None,
        client: Any = None,
    ) -> None:
        self._config = config or VectorDBConfig()
        self._client = client or self._create_client()

    def _create_client(self) -> Any:
        """Create a ChromaDB client from config."""
        import chromadb

        return chromadb.HttpClient(
            host=self._config.host,
            port=self._config.port,
        )

    def _collection_name(self, collection: str) -> str:
        """Prefix the collection name with the configured prefix."""
        prefix = self._config.collection_prefix
        if collection.startswith(prefix):
            return collection
        return f"{prefix}_{collection}"

    def add_documents(self, docs: list[Document], collection: str) -> None:
        """Add documents to a collection.

        Each document is stored with its classification level in metadata
        so that queries can filter by access level.

        Args:
            docs: List of Document instances to store.
            collection: Name of the target collection.
        """
        col = self._client.get_or_create_collection(
            name=self._collection_name(collection),
        )

        ids = [doc.id for doc in docs]
        documents = [doc.content for doc in docs]
        metadatas = [
            {
                **doc.metadata,
                "classification": doc.classification.value,
                "classification_level": _LEVEL_ORDER[doc.classification],
            }
            for doc in docs
        ]

        col.add(ids=ids, documents=documents, metadatas=metadatas)

    def query(
        self,
        query_text: str,
        collection: str,
        n_results: int = 5,
        max_classification: DataClassification | None = None,
    ) -> list[SearchResult]:
        """Query a collection for similar documents.

        Args:
            query_text: The query string to search for.
            collection: Name of the collection to search.
            n_results: Maximum number of results to return.
            max_classification: If provided, only return documents at or below
                this classification level. This enforces access control at the
                data layer.

        Returns:
            List of SearchResult instances ordered by relevance.
        """
        col_name = self._collection_name(collection)

        try:
            col = self._client.get_collection(name=col_name)
        except Exception:
            return []

        where_filter = None
        if max_classification is not None:
            max_level = _LEVEL_ORDER[max_classification]
            where_filter = {"classification_level": {"$lte": max_level}}

        results = col.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter,
        )

        search_results: list[SearchResult] = []
        if not results or not results.get("ids"):
            return search_results

        ids = results["ids"][0]
        documents = results["documents"][0] if results.get("documents") else [""] * len(ids)
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

        for i, doc_id in enumerate(ids):
            meta = dict(metadatas[i]) if metadatas[i] else {}
            classification_str = meta.pop("classification", "public")
            meta.pop("classification_level", None)

            search_results.append(
                SearchResult(
                    document_id=doc_id,
                    content=documents[i],
                    metadata=meta,
                    classification=DataClassification(classification_str),
                    distance=distances[i],
                )
            )

        return search_results

    def delete_collection(self, collection: str) -> None:
        """Delete an entire collection.

        Args:
            collection: Name of the collection to delete.
        """
        col_name = self._collection_name(collection)
        try:
            self._client.delete_collection(name=col_name)
        except ValueError:
            pass  # Collection does not exist

    def list_collections(self) -> list[str]:
        """List all collection names managed by this store."""
        collections = self._client.list_collections()
        prefix = self._config.collection_prefix
        return [c.name for c in collections if c.name.startswith(prefix)]
