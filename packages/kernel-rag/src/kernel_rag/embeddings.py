"""Embedding provider and indexing primitives."""

from __future__ import annotations

import hashlib
import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import httpx
from kernel_core import ChunkEmbedding, DocumentStatus
from kernel_storage import ChunkEmbeddingRepository, DocumentChunkRepository, DocumentRepository

MOCK_EMBEDDING_MODEL = "mock-embedding-v1"
MOCK_EMBEDDING_DIMENSIONS = 8
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_EMBEDDING_MODEL_ENV = "OPENAI_EMBEDDING_MODEL"
OPENAI_EMBEDDING_DIMENSIONS_ENV = "OPENAI_EMBEDDING_DIMENSIONS"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_OPENAI_EMBEDDING_DIMENSIONS = 1536
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


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


class OpenAIEmbeddingError(RuntimeError):
    """Raised when OpenAI embeddings cannot be generated."""

    def __init__(self, message: str, *, error_type: str = "openai_embedding_error") -> None:
        self.error_type = error_type
        super().__init__(message)


def get_openai_embedding_api_key(env: Mapping[str, str] | None = None) -> str | None:
    values = env or os.environ
    value = values.get(OPENAI_API_KEY_ENV)
    if value is None or value.strip() == "":
        return None
    return value


def get_openai_embedding_model(env: Mapping[str, str] | None = None) -> str:
    values = env or os.environ
    value = values.get(OPENAI_EMBEDDING_MODEL_ENV)
    if value is None or value.strip() == "":
        return DEFAULT_OPENAI_EMBEDDING_MODEL
    return value


def get_openai_embedding_dimensions(env: Mapping[str, str] | None = None) -> int:
    values = env or os.environ
    value = values.get(OPENAI_EMBEDDING_DIMENSIONS_ENV)
    if value is None or value.strip() == "":
        return DEFAULT_OPENAI_EMBEDDING_DIMENSIONS
    try:
        dimensions = int(value)
    except ValueError as error:
        raise ValueError(f"{OPENAI_EMBEDDING_DIMENSIONS_ENV} must be an integer.") from error
    if dimensions <= 0:
        raise ValueError(f"{OPENAI_EMBEDDING_DIMENSIONS_ENV} must be positive.")
    return dimensions


class OpenAIEmbeddingProvider:
    """OpenAI embeddings backend for real RAG indexing and retrieval paths."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
        base_url: str = DEFAULT_OPENAI_BASE_URL,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        resolved_dimensions = (
            dimensions if dimensions is not None else get_openai_embedding_dimensions()
        )
        if resolved_dimensions <= 0:
            raise ValueError("OpenAI embedding dimensions must be positive.")
        self._api_key = api_key if api_key is not None else get_openai_embedding_api_key()
        self.model = model or get_openai_embedding_model()
        self.dimensions = resolved_dimensions
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._api_key is None:
            raise OpenAIEmbeddingError(
                f"{OPENAI_API_KEY_ENV} is not configured.",
                error_type="missing_api_key",
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "input": texts,
        }
        if self.dimensions:
            payload["dimensions"] = self.dimensions
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(transport=self._transport, timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/embeddings",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise OpenAIEmbeddingError(
                f"OpenAI embeddings API returned {error.response.status_code}.",
                error_type="openai_embedding_status_error",
            ) from error
        except httpx.RequestError as error:
            raise OpenAIEmbeddingError(
                f"OpenAI embeddings API request failed: {error}",
                error_type="openai_embedding_request_error",
            ) from error

        try:
            data = response.json()
        except ValueError as error:
            raise OpenAIEmbeddingError(
                "OpenAI embeddings response was not valid JSON.",
                error_type="openai_embedding_invalid_response",
            ) from error
        if not isinstance(data, dict):
            raise OpenAIEmbeddingError(
                "OpenAI embeddings response must be a JSON object.",
                error_type="openai_embedding_invalid_response",
            )

        return _extract_openai_embedding_vectors(
            data,
            expected_count=len(texts),
            dimensions=self.dimensions,
        )


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


def _extract_openai_embedding_vectors(
    data: dict[str, Any],
    *,
    expected_count: int,
    dimensions: int,
) -> list[list[float]]:
    raw_items = data.get("data")
    if not isinstance(raw_items, list):
        raise OpenAIEmbeddingError(
            "OpenAI embeddings response field 'data' must be an array.",
            error_type="openai_embedding_invalid_response",
        )
    if len(raw_items) != expected_count:
        raise OpenAIEmbeddingError(
            f"OpenAI embeddings response returned {len(raw_items)} item(s), "
            f"expected {expected_count}.",
            error_type="openai_embedding_count_mismatch",
        )

    vectors_by_index: dict[int, list[float]] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            raise OpenAIEmbeddingError(
                "OpenAI embeddings response item must be an object.",
                error_type="openai_embedding_invalid_response",
            )
        index = item.get("index")
        if not isinstance(index, int):
            raise OpenAIEmbeddingError(
                "OpenAI embeddings response item is missing integer index.",
                error_type="openai_embedding_invalid_response",
            )
        vectors_by_index[index] = _embedding_vector_from_item(item, dimensions=dimensions)

    try:
        return [vectors_by_index[index] for index in range(expected_count)]
    except KeyError as error:
        raise OpenAIEmbeddingError(
            "OpenAI embeddings response indexes are incomplete.",
            error_type="openai_embedding_index_mismatch",
        ) from error


def _embedding_vector_from_item(item: dict[str, Any], *, dimensions: int) -> list[float]:
    raw_embedding = item.get("embedding")
    if not isinstance(raw_embedding, list):
        raise OpenAIEmbeddingError(
            "OpenAI embeddings response item is missing embedding vector.",
            error_type="openai_embedding_invalid_response",
        )

    vector: list[float] = []
    for value in raw_embedding:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise OpenAIEmbeddingError(
                "OpenAI embedding vector values must be numeric.",
                error_type="openai_embedding_invalid_vector",
            )
        vector.append(float(value))

    if len(vector) != dimensions:
        raise OpenAIEmbeddingError(
            f"OpenAI embedding vector has {len(vector)} dimensions, expected {dimensions}.",
            error_type="openai_embedding_dimension_mismatch",
        )
    return vector
