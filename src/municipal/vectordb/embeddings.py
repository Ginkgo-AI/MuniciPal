"""Embedding provider abstraction for Munici-Pal.

Provides a pluggable interface for text embedding. Includes:
  - EmbeddingProvider: base class (uses ChromaDB's built-in default)
  - OllamaEmbedding: calls the Ollama /api/embeddings endpoint
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers.

    Subclasses must implement :meth:`embed` to convert a list of text strings
    into a list of float vectors.
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts into vector representations.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (one per input text).
        """


class DefaultEmbedding(EmbeddingProvider):
    """Default embedding provider that delegates to ChromaDB's built-in model.

    This is a pass-through: ChromaDB handles embedding internally when no
    custom embedding function is provided. This class exists so that the
    VectorStore always has a concrete provider reference, but ``embed()``
    is only used when documents need to be embedded outside of ChromaDB's
    own ``add`` / ``query`` calls.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using ChromaDB's default embedding function.

        Requires ``chromadb`` to be installed. Falls back to a simple
        hash-based stub if ChromaDB's default function is not available
        (useful for testing).
        """
        try:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

            fn = DefaultEmbeddingFunction()
            return fn(texts)  # type: ignore[return-value]
        except Exception:
            # Fallback for environments without the full ChromaDB model
            return _stub_embed(texts)


class OllamaEmbedding(EmbeddingProvider):
    """Embedding provider that calls the Ollama /api/embeddings endpoint.

    Args:
        base_url: Ollama server URL. Defaults to ``http://localhost:11434``.
        model: Embedding model name. Defaults to ``nomic-embed-text``.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts by calling Ollama's /api/embeddings endpoint.

        Each text is sent as a separate request. For large batches consider
        using the ``/api/embed`` batch endpoint if available.

        Raises:
            httpx.HTTPStatusError: If the Ollama server returns an error.
            httpx.ConnectError: If the Ollama server is unreachable.
        """
        embeddings: list[list[float]] = []
        url = f"{self.base_url}/api/embeddings"

        with httpx.Client(timeout=self.timeout) as client:
            for text in texts:
                response = client.post(
                    url,
                    json={"model": self.model, "prompt": text},
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])

        return embeddings


def _stub_embed(texts: list[str]) -> list[list[float]]:
    """Deterministic stub embedding for testing (not for production).

    Produces a 384-dimensional vector from the hash of each text.
    """
    import hashlib

    results: list[list[float]] = []
    for text in texts:
        digest = hashlib.sha256(text.encode()).hexdigest()
        # Convert hex chars to floats in [0, 1]
        vec = [int(digest[i : i + 2], 16) / 255.0 for i in range(0, min(len(digest), 64), 2)]
        # Pad to 384 dimensions
        vec = (vec * 12)[:384]
        results.append(vec)
    return results
