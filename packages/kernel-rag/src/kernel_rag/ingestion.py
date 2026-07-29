"""Synchronous document ingestion service."""

from __future__ import annotations

from uuid import UUID

from kernel_core import Document, DocumentStatus, IngestionJob
from kernel_storage import DocumentRepository, IngestionJobRepository, IngestionJobStateError

from kernel_rag.object_store import LocalObjectStore
from kernel_rag.parsers import ParserError, TextMarkdownParser, UnsupportedDocumentError


class DocumentIngestionError(RuntimeError):
    """Raised when a document cannot be ingested."""


class DocumentNotFoundError(DocumentIngestionError):
    """Raised when the target document is missing."""


class DocumentNotReadyError(DocumentIngestionError):
    """Raised when the document is not in an ingestible state."""


class DocumentIngestionService:
    def __init__(
        self,
        *,
        object_store: LocalObjectStore | None = None,
        parser: TextMarkdownParser | None = None,
    ) -> None:
        self._object_store = object_store or LocalObjectStore()
        self._parser = parser or TextMarkdownParser()

    def ingest(
        self,
        *,
        document_id: UUID,
        document_repository: DocumentRepository,
        ingestion_job_repository: IngestionJobRepository,
    ) -> IngestionJob:
        document = document_repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(f"Document {document_id} was not found.")
        if document.status not in {DocumentStatus.UPLOADED, DocumentStatus.FAILED}:
            raise DocumentNotReadyError(
                f"Document {document_id} cannot be ingested from status {document.status}."
            )

        job = ingestion_job_repository.create(
            document_id=document.id,
            metadata={"source_uri": document.source_uri},
        )
        if job is None:
            raise DocumentNotFoundError(f"Document {document_id} was not found.")

        filename = _original_filename(document)
        try:
            started = ingestion_job_repository.mark_parsing(
                job_id=job.id,
                parser_name=self._parser.name,
            )
            if started is None:
                raise DocumentIngestionError(f"Ingestion job {job.id} was not found.")

            source_bytes = self._object_store.read_uri_bytes(document.source_uri)
            parsed = self._parser.parse(
                content=source_bytes,
                filename=filename,
                mime_type=document.mime_type,
            )
            parsed_object = self._object_store.write_artifact(
                key=f"documents/{document.id}/parsed/{job.id}.txt",
                content=parsed.text.encode("utf-8"),
                content_type="text/plain",
            )
            completed = ingestion_job_repository.complete_parsed(
                job_id=job.id,
                parsed_text_uri=parsed_object.uri,
                parsed_text_checksum=parsed_object.checksum,
                parsed_text_size_bytes=parsed_object.size_bytes,
                content_char_count=parsed.content_char_count,
            )
            if completed is None:
                raise DocumentIngestionError(f"Ingestion job {job.id} was not found.")
            return completed
        except UnsupportedDocumentError as error:
            failed = ingestion_job_repository.fail(
                job_id=job.id,
                error_type="unsupported_document",
                error_message=str(error),
            )
            if failed is None:
                raise DocumentIngestionError(f"Ingestion job {job.id} was not found.") from error
            return failed
        except (ParserError, IngestionJobStateError, OSError) as error:
            failed = ingestion_job_repository.fail(
                job_id=job.id,
                error_type=error.__class__.__name__,
                error_message=str(error),
            )
            if failed is None:
                raise DocumentIngestionError(f"Ingestion job {job.id} was not found.") from error
            return failed


def _original_filename(document: Document) -> str | None:
    value = document.metadata.get("original_filename")
    if isinstance(value, str):
        return value
    return None
