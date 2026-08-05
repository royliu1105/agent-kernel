"""Deterministic text chunking for parsed documents."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import UUID

from kernel_core import Document, DocumentChunk, DocumentStatus, IngestionJobStatus
from kernel_storage import DocumentChunkRepository, DocumentRepository, IngestionJobRepository

from kernel_rag.object_store import ObjectStore, create_object_store

DEFAULT_CHUNK_SIZE_CHARS = 1000
DEFAULT_CHUNK_OVERLAP_CHARS = 150


class ChunkingError(RuntimeError):
    """Raised when a document cannot be chunked."""


class DocumentNotChunkableError(ChunkingError):
    """Raised when the document is not ready for chunking."""


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str
    start_char: int
    end_char: int
    token_count_estimate: int
    checksum: str


class TextChunker:
    def __init__(
        self,
        *,
        chunk_size_chars: int = DEFAULT_CHUNK_SIZE_CHARS,
        chunk_overlap_chars: int = DEFAULT_CHUNK_OVERLAP_CHARS,
    ) -> None:
        if chunk_size_chars < 1:
            raise ValueError("chunk_size_chars must be at least 1.")
        if chunk_overlap_chars < 0:
            raise ValueError("chunk_overlap_chars must be non-negative.")
        if chunk_overlap_chars >= chunk_size_chars:
            raise ValueError("chunk_overlap_chars must be smaller than chunk_size_chars.")

        self._chunk_size_chars = chunk_size_chars
        self._chunk_overlap_chars = chunk_overlap_chars

    @property
    def chunk_size_chars(self) -> int:
        return self._chunk_size_chars

    @property
    def chunk_overlap_chars(self) -> int:
        return self._chunk_overlap_chars

    def chunk(self, text: str) -> list[TextChunk]:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        if not normalized:
            return []

        chunks: list[TextChunk] = []
        start = 0
        while start < len(normalized):
            end = min(start + self._chunk_size_chars, len(normalized))
            if end < len(normalized):
                boundary = _find_boundary(normalized, start, end)
                if boundary > start:
                    end = boundary

            content = normalized[start:end]
            chunks.append(
                TextChunk(
                    index=len(chunks),
                    content=content,
                    start_char=start,
                    end_char=end,
                    token_count_estimate=_estimate_tokens(content),
                    checksum=f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}",
                )
            )
            if end == len(normalized):
                break
            start = max(end - self._chunk_overlap_chars, 0)

        return chunks


class DocumentChunkingService:
    def __init__(
        self,
        *,
        object_store: ObjectStore | None = None,
        chunker: TextChunker | None = None,
    ) -> None:
        self._object_store = object_store or create_object_store()
        self._chunker = chunker or TextChunker()

    def chunk_document(
        self,
        *,
        document_id: UUID,
        document_repository: DocumentRepository,
        ingestion_job_repository: IngestionJobRepository,
        chunk_repository: DocumentChunkRepository,
    ) -> list[DocumentChunk]:
        document = document_repository.get(document_id)
        if document is None:
            raise DocumentNotChunkableError(f"Document {document_id} was not found.")
        if document.status not in {DocumentStatus.PARSED, DocumentStatus.CHUNKED}:
            raise DocumentNotChunkableError(
                f"Document {document_id} cannot be chunked from status {document.status}."
            )

        parsed_uri = _latest_parsed_text_uri(document=document, repository=ingestion_job_repository)
        if parsed_uri is None:
            raise DocumentNotChunkableError(f"Document {document_id} has no parsed text artifact.")

        parsed_text = self._object_store.read_uri_bytes(parsed_uri).decode("utf-8")
        document_repository.update_status(document_id=document.id, status=DocumentStatus.CHUNKING)
        text_chunks = self._chunker.chunk(parsed_text)
        document_chunks = [
            DocumentChunk(
                document_id=document.id,
                index=chunk.index,
                content=chunk.content,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                token_count_estimate=chunk.token_count_estimate,
                checksum=chunk.checksum,
                metadata={
                    "source_parsed_text_uri": parsed_uri,
                    "chunk_size_chars": self._chunker.chunk_size_chars,
                    "chunk_overlap_chars": self._chunker.chunk_overlap_chars,
                },
            )
            for chunk in text_chunks
        ]
        persisted = chunk_repository.replace_for_document(
            document_id=document.id,
            chunks=document_chunks,
        )
        if persisted is None:
            raise DocumentNotChunkableError(f"Document {document_id} was not found.")
        return persisted


def _find_boundary(text: str, start: int, hard_end: int) -> int:
    boundary_window_start = start + max((hard_end - start) // 2, 1)
    candidates = [
        text.rfind("\n\n", boundary_window_start, hard_end),
        text.rfind("\n", boundary_window_start, hard_end),
        text.rfind(" ", boundary_window_start, hard_end),
    ]
    return max(candidates)


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def _latest_parsed_text_uri(
    *,
    document: Document,
    repository: IngestionJobRepository,
) -> str | None:
    jobs = repository.list_for_document(document.id)
    if not jobs:
        return None
    parsed_jobs = [
        job
        for job in jobs
        if job.status is IngestionJobStatus.PARSED and job.parsed_text_uri is not None
    ]
    if not parsed_jobs:
        return None
    return parsed_jobs[-1].parsed_text_uri
