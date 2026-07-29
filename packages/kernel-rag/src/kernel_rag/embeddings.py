"""Embedding provider and indexing primitives."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from kernel_core import ChunkEmbedding, DocumentStatus
from kernel_storage import ChunkEmbeddingRepository, DocumentChunkRepository, DocumentRepository

MOCK_EMBEDDING_MODEL = "mock-embedding-v1"
MOCK_EMBEDDING_DIMENSIONS = 8


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""


@dataclass(frozen=True)
class EmbeddingIndexResult:
    document_id: UUID
    model: str
    dimensions: int
    embedding_count: int


class MockEmbeddingProvider:
    model = MOCK_EMBEDDING_MODEL
    dimensions = MOCK_EMBEDDING_DIMENSIONS

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [
            _mock_embedding(text, model=self.model, dimensions=self.dimensions) for text in texts
        ]


class DocumentIndexingError(RuntimeError):
    """Raised when a document cannot be indexed."""


class DocumentNotIndexableError(DocumentIndexingError):
    """Raised when a document is not ready for embedding/indexing."""


class DocumentIndexingService:
    def __init__(self, *, embedding_provider: EmbeddingProvider | None = None) -> None:
        self._embedding_provider = embedding_provider or MockEmbeddingProvider()

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        return self._embedding_provider

    def index_document(
        self,
        *,
        document_id: UUID,
        document_repository: DocumentRepository,
        chunk_repository: DocumentChunkRepository,
        embedding_repository: ChunkEmbeddingRepository,
    ) -> EmbeddingIndexResult:
        document = document_repository.get(document_id)
        if document is None:
            raise DocumentNotIndexableError(f"Document {document_id} was not found.")
        if document.status not in {DocumentStatus.CHUNKED, DocumentStatus.INDEXED}:
            raise DocumentNotIndexableError(
                f"Document {document_id} cannot be indexed from status {document.status}."
            )

        chunks = chunk_repository.list_for_document(document_id)
        if chunks is None:
            raise DocumentNotIndexableError(f"Document {document_id} was not found.")
        if not chunks:
            raise DocumentNotIndexableError(f"Document {document_id} has no chunks to index.")

        document_repository.update_status(document_id=document_id, status=DocumentStatus.EMBEDDING)
        vectors = self._embedding_provider.embed_texts([chunk.content for chunk in chunks])
        embeddings = [
            ChunkEmbedding(
                document_id=document_id,
                chunk_id=chunk.id,
                model=self._embedding_provider.model,
                dimensions=self._embedding_provider.dimensions,
                vector=vector,
                checksum=_vector_checksum(vector),
                metadata={"chunk_index": chunk.index},
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        persisted = embedding_repository.replace_for_document(
            document_id=document_id,
            model=self._embedding_provider.model,
            embeddings=embeddings,
        )
        if persisted is None:
            raise DocumentNotIndexableError(f"Document {document_id} was not found.")
        return EmbeddingIndexResult(
            document_id=document_id,
            model=self._embedding_provider.model,
            dimensions=self._embedding_provider.dimensions,
            embedding_count=len(persisted),
        )


def _mock_embedding(text: str, *, model: str, dimensions: int) -> list[float]:
    digest = hashlib.sha256(f"{model}:{text}".encode()).digest()
    values = [((digest[index] / 255.0) * 2.0) - 1.0 for index in range(dimensions)]
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0.0:
        return [0.0 for _ in values]
    return [value / norm for value in values]


def _vector_checksum(vector: list[float]) -> str:
    payload = ",".join(f"{value:.12f}" for value in vector)
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"
