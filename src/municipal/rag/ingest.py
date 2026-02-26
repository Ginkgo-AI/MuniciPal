"""Document ingestion pipeline for Munici-Pal RAG.

Reads text and markdown files, splits them into chunks, classifies each
chunk, and stores them in the vector database via VectorStore.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from municipal.classification.rules import ClassificationEngine
from municipal.core.types import DataClassification
from municipal.vectordb.store import Document, VectorStore

# Maximum chunk size in characters before we force a split.
_MAX_CHUNK_CHARS = 500

# Supported file extensions for ingestion.
_SUPPORTED_EXTENSIONS = {".txt", ".md"}


class IngestResult(BaseModel):
    """Result of ingesting a single file."""

    source_path: str
    num_chunks: int
    collection: str
    classification: DataClassification
    chunk_ids: list[str] = Field(default_factory=list)


def _detect_section_header(text: str) -> str | None:
    """Return the last markdown heading found before or in *text*, or None."""
    match = re.search(r"^(#{1,6})\s+(.+)", text, re.MULTILINE)
    if match:
        return match.group(2).strip()
    return None


def _split_on_sentence_boundary(text: str, max_chars: int = _MAX_CHUNK_CHARS) -> list[str]:
    """Split *text* into pieces of roughly *max_chars* on sentence boundaries.

    Sentence boundaries are identified by '. ', '! ', '? ', or newline
    followed by an uppercase letter or end-of-string.
    """
    if len(text) <= max_chars:
        return [text]

    # Find sentence-ending positions
    sentence_ends: list[int] = []
    for m in re.finditer(r"[.!?]\s+", text):
        sentence_ends.append(m.end())

    if not sentence_ends:
        # No sentence boundaries found; hard-split at max_chars
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]

    chunks: list[str] = []
    start = 0
    for end in sentence_ends:
        if end - start >= max_chars:
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end
    # Remainder
    remainder = text[start:].strip()
    if remainder:
        if chunks and len(chunks[-1]) + len(remainder) + 1 <= max_chars:
            chunks[-1] = chunks[-1] + " " + remainder
        else:
            chunks.append(remainder)
    return chunks if chunks else [text]


def chunk_text(text: str, max_chunk_chars: int = _MAX_CHUNK_CHARS) -> list[dict[str, Any]]:
    """Split *text* into chunks suitable for vector storage.

    Strategy:
    1. Split on double newlines (paragraphs).
    2. If a paragraph exceeds *max_chunk_chars*, split on sentence boundaries.
    3. Attach detected markdown section headers to each chunk.

    Returns a list of dicts with keys ``text``, ``section_header``, and
    ``chunk_index``.
    """
    paragraphs = re.split(r"\n{2,}", text)

    chunks: list[dict[str, Any]] = []
    current_header: str | None = None
    idx = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Update current section header if this paragraph is a heading
        header_match = re.match(r"^(#{1,6})\s+(.+)", para)
        if header_match:
            current_header = header_match.group(2).strip()

        sub_chunks = _split_on_sentence_boundary(para, max_chunk_chars)
        for sc in sub_chunks:
            sc = sc.strip()
            if not sc:
                continue
            chunks.append({
                "text": sc,
                "section_header": current_header,
                "chunk_index": idx,
            })
            idx += 1

    return chunks


class DocumentIngester:
    """Ingests text/markdown files into the vector store.

    Args:
        vector_store: A VectorStore instance for document storage.
        classification_engine: A ClassificationEngine for classifying chunks.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        classification_engine: ClassificationEngine,
    ) -> None:
        self._store = vector_store
        self._classifier = classification_engine

    def ingest_file(
        self,
        path: str,
        metadata: dict[str, Any] | None = None,
    ) -> IngestResult:
        """Read, chunk, classify, and store a single text/markdown file.

        Args:
            path: Path to the file to ingest.
            metadata: Additional metadata to attach to each chunk. Must
                include a ``collection`` key indicating the target collection.

        Returns:
            An IngestResult summarising what was stored.
        """
        metadata = metadata or {}
        file_path = Path(path)
        text = file_path.read_text(encoding="utf-8")

        collection = metadata.pop("collection", "ordinances")
        resource_type = metadata.pop("resource_type", "ordinance")

        # Classify the document
        classification = self._classifier.classify(resource_type)

        chunks = chunk_text(text)
        if not chunks:
            return IngestResult(
                source_path=str(file_path),
                num_chunks=0,
                collection=collection,
                classification=classification,
                chunk_ids=[],
            )

        documents: list[Document] = []
        chunk_ids: list[str] = []

        for chunk in chunks:
            chunk_id = str(uuid.uuid4())
            chunk_ids.append(chunk_id)
            doc_metadata = {
                **metadata,
                "source_file": str(file_path),
                "chunk_index": chunk["chunk_index"],
            }
            if chunk["section_header"]:
                doc_metadata["section_header"] = chunk["section_header"]

            documents.append(
                Document(
                    id=chunk_id,
                    content=chunk["text"],
                    metadata=doc_metadata,
                    classification=classification,
                )
            )

        self._store.add_documents(documents, collection)

        return IngestResult(
            source_path=str(file_path),
            num_chunks=len(chunks),
            collection=collection,
            classification=classification,
            chunk_ids=chunk_ids,
        )

    def ingest_directory(
        self,
        dir_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[IngestResult]:
        """Ingest all supported files in a directory.

        Args:
            dir_path: Path to the directory.
            metadata: Metadata passed to each ``ingest_file`` call. A copy
                is made per file so mutations do not leak across calls.

        Returns:
            A list of IngestResult instances, one per ingested file.
        """
        metadata = metadata or {}
        directory = Path(dir_path)
        results: list[IngestResult] = []

        for file_path in sorted(directory.iterdir()):
            if file_path.is_file() and file_path.suffix in _SUPPORTED_EXTENSIONS:
                result = self.ingest_file(str(file_path), dict(metadata))
                results.append(result)

        return results
