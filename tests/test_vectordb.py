"""Tests for the vector database module.

Uses a mock ChromaDB client to avoid requiring a running ChromaDB instance.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from municipal.core.config import VectorDBConfig
from municipal.core.types import DataClassification
from municipal.vectordb.embeddings import DefaultEmbedding, OllamaEmbedding, _stub_embed
from municipal.vectordb.store import Document, SearchResult, VectorStore


# ---------------------------------------------------------------------------
# Mock ChromaDB helpers
# ---------------------------------------------------------------------------


class MockCollection:
    """In-memory mock of a ChromaDB collection."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._docs: dict[str, dict[str, Any]] = {}

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        for i, doc_id in enumerate(ids):
            self._docs[doc_id] = {
                "document": documents[i],
                "metadata": metadatas[i] if metadatas else {},
            }

    def query(
        self,
        query_texts: list[str],
        n_results: int = 5,
        where: dict | None = None,
    ) -> dict[str, list]:
        # Simple mock: return all docs that pass the where filter
        results_ids: list[str] = []
        results_docs: list[str] = []
        results_meta: list[dict] = []
        results_dist: list[float] = []

        for doc_id, data in self._docs.items():
            meta = data["metadata"]
            if where and not self._matches_filter(meta, where):
                continue
            results_ids.append(doc_id)
            results_docs.append(data["document"])
            results_meta.append(meta)
            results_dist.append(0.1)

            if len(results_ids) >= n_results:
                break

        return {
            "ids": [results_ids],
            "documents": [results_docs],
            "metadatas": [results_meta],
            "distances": [results_dist],
        }

    @staticmethod
    def _matches_filter(meta: dict, where: dict) -> bool:
        for field, condition in where.items():
            val = meta.get(field)
            if val is None:
                return False
            if isinstance(condition, dict):
                for op, threshold in condition.items():
                    if op == "$lte" and val > threshold:
                        return False
                    if op == "$gte" and val < threshold:
                        return False
                    if op == "$eq" and val != threshold:
                        return False
            elif val != condition:
                return False
        return True


class MockChromaClient:
    """In-memory mock of a ChromaDB client."""

    def __init__(self) -> None:
        self._collections: dict[str, MockCollection] = {}

    def get_or_create_collection(self, name: str, **kwargs) -> MockCollection:
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]

    def get_collection(self, name: str, **kwargs) -> MockCollection:
        if name not in self._collections:
            raise ValueError(f"Collection '{name}' not found")
        return self._collections[name]

    def delete_collection(self, name: str) -> None:
        self._collections.pop(name, None)

    def list_collections(self) -> list[MockCollection]:
        return list(self._collections.values())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_client() -> MockChromaClient:
    return MockChromaClient()


@pytest.fixture()
def store(mock_client: MockChromaClient) -> VectorStore:
    config = VectorDBConfig(collection_prefix="test")
    return VectorStore(config=config, client=mock_client)


# ---------------------------------------------------------------------------
# VectorStore tests
# ---------------------------------------------------------------------------


class TestVectorStore:
    def test_add_and_query_documents(self, store: VectorStore) -> None:
        docs = [
            Document(id="d1", content="Building permit fee schedule", classification=DataClassification.PUBLIC),
            Document(id="d2", content="John Doe's permit application", classification=DataClassification.SENSITIVE),
        ]
        store.add_documents(docs, "permits")

        results = store.query("permit fees", "permits")
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)

    def test_classification_filtering_public_only(self, store: VectorStore) -> None:
        docs = [
            Document(id="pub1", content="Public ordinance", classification=DataClassification.PUBLIC),
            Document(id="int1", content="Internal memo", classification=DataClassification.INTERNAL),
            Document(id="sen1", content="Resident SSN data", classification=DataClassification.SENSITIVE),
        ]
        store.add_documents(docs, "mixed")

        results = store.query(
            "documents",
            "mixed",
            max_classification=DataClassification.PUBLIC,
        )
        assert len(results) == 1
        assert results[0].document_id == "pub1"
        assert results[0].classification == DataClassification.PUBLIC

    def test_classification_filtering_internal_max(self, store: VectorStore) -> None:
        docs = [
            Document(id="pub1", content="Public info", classification=DataClassification.PUBLIC),
            Document(id="int1", content="Internal info", classification=DataClassification.INTERNAL),
            Document(id="sen1", content="Sensitive info", classification=DataClassification.SENSITIVE),
        ]
        store.add_documents(docs, "mixed2")

        results = store.query(
            "info",
            "mixed2",
            max_classification=DataClassification.INTERNAL,
        )
        assert len(results) == 2
        ids = {r.document_id for r in results}
        assert ids == {"pub1", "int1"}

    def test_query_nonexistent_collection(self, store: VectorStore) -> None:
        results = store.query("anything", "nonexistent")
        assert results == []

    def test_delete_collection(self, store: VectorStore, mock_client: MockChromaClient) -> None:
        docs = [Document(id="d1", content="test", classification=DataClassification.PUBLIC)]
        store.add_documents(docs, "to_delete")
        store.delete_collection("to_delete")
        results = store.query("test", "to_delete")
        assert results == []

    def test_n_results_limit(self, store: VectorStore) -> None:
        docs = [
            Document(id=f"d{i}", content=f"Document {i}", classification=DataClassification.PUBLIC)
            for i in range(10)
        ]
        store.add_documents(docs, "many")
        results = store.query("document", "many", n_results=3)
        assert len(results) == 3

    def test_document_metadata_preserved(self, store: VectorStore) -> None:
        docs = [
            Document(
                id="m1",
                content="Meeting minutes",
                metadata={"department": "planning", "date": "2024-01-15"},
                classification=DataClassification.PUBLIC,
            ),
        ]
        store.add_documents(docs, "meta_test")
        results = store.query("meeting", "meta_test")
        assert len(results) == 1
        assert results[0].metadata["department"] == "planning"
        assert results[0].metadata["date"] == "2024-01-15"

    def test_collection_prefix(self, store: VectorStore, mock_client: MockChromaClient) -> None:
        docs = [Document(id="d1", content="test", classification=DataClassification.PUBLIC)]
        store.add_documents(docs, "my_col")
        # Collection should be prefixed
        assert "test_my_col" in mock_client._collections

    def test_no_double_prefix(self, store: VectorStore, mock_client: MockChromaClient) -> None:
        docs = [Document(id="d1", content="test", classification=DataClassification.PUBLIC)]
        store.add_documents(docs, "test_already_prefixed")
        assert "test_already_prefixed" in mock_client._collections


# ---------------------------------------------------------------------------
# Embedding tests
# ---------------------------------------------------------------------------


class TestStubEmbedding:
    def test_stub_produces_vectors(self) -> None:
        vectors = _stub_embed(["hello world", "municipal government"])
        assert len(vectors) == 2
        assert len(vectors[0]) == 384
        assert all(0.0 <= v <= 1.0 for v in vectors[0])

    def test_stub_is_deterministic(self) -> None:
        v1 = _stub_embed(["test"])
        v2 = _stub_embed(["test"])
        assert v1 == v2

    def test_stub_different_texts_differ(self) -> None:
        v1 = _stub_embed(["hello"])
        v2 = _stub_embed(["world"])
        assert v1 != v2


class TestDefaultEmbedding:
    def test_embed_returns_vectors(self) -> None:
        provider = DefaultEmbedding()
        # Will use stub fallback if chromadb model not installed
        vectors = provider.embed(["test text"])
        assert len(vectors) == 1
        assert len(vectors[0]) > 0


class TestOllamaEmbedding:
    def test_embed_calls_ollama_api(self) -> None:
        provider = OllamaEmbedding(base_url="http://localhost:11434", model="nomic-embed-text")

        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            MockClient.return_value = mock_client

            result = provider.embed(["test text"])

        assert result == [[0.1, 0.2, 0.3]]
        mock_client.post.assert_called_once_with(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": "test text"},
        )

    def test_embed_multiple_texts(self) -> None:
        provider = OllamaEmbedding()

        mock_response = MagicMock()
        mock_response.json.side_effect = [
            {"embedding": [1.0, 2.0]},
            {"embedding": [3.0, 4.0]},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            MockClient.return_value = mock_client

            result = provider.embed(["text1", "text2"])

        assert len(result) == 2
        assert mock_client.post.call_count == 2
