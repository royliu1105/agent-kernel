from pathlib import Path

from kernel_core import DocumentStatus
from kernel_rag import LocalObjectStore, TextChunker
from kernel_rag.chunking import DocumentChunkingService
from kernel_storage import (
    DocumentChunkRepository,
    DocumentRepository,
    IngestionJobRepository,
    KnowledgeBaseRepository,
)
from sqlalchemy.orm import Session, sessionmaker


def test_text_chunker_creates_stable_overlapping_chunks() -> None:
    chunker = TextChunker(chunk_size_chars=12, chunk_overlap_chars=3)

    chunks = chunker.chunk("alpha beta gamma delta")

    assert [chunk.index for chunk in chunks] == [0, 1, 2]
    assert [(chunk.start_char, chunk.end_char) for chunk in chunks] == [
        (0, 10),
        (7, 16),
        (13, 22),
    ]
    assert [chunk.content for chunk in chunks] == ["alpha beta", "eta gamma", "mma delta"]
    assert all(chunk.checksum.startswith("sha256:") for chunk in chunks)
    assert all(chunk.token_count_estimate >= 1 for chunk in chunks)


def test_text_chunker_returns_empty_for_empty_text() -> None:
    assert TextChunker().chunk("") == []


def test_document_chunking_service_chunks_latest_parsed_artifact(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    object_store = LocalObjectStore(root_path=tmp_path)
    chunker = TextChunker(chunk_size_chars=12, chunk_overlap_chars=3)
    service = DocumentChunkingService(object_store=object_store, chunker=chunker)

    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="kb")
        stored = object_store.write_artifact(
            key="documents/source/parsed/job.txt",
            content=b"alpha beta gamma delta",
            content_type="text/plain",
        )
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Parsed",
            source_uri="object://local/source.md",
        )
        assert document is not None
        document = DocumentRepository(session).update_status(
            document_id=document.id,
            status=DocumentStatus.PARSED,
        )
        assert document is not None
        job = IngestionJobRepository(session).create(document_id=document.id)
        assert job is not None
        IngestionJobRepository(session).mark_parsing(job_id=job.id, parser_name="text-markdown")
        IngestionJobRepository(session).complete_parsed(
            job_id=job.id,
            parsed_text_uri=stored.uri,
            parsed_text_checksum=stored.checksum,
            parsed_text_size_bytes=stored.size_bytes,
            content_char_count=len("alpha beta gamma delta"),
        )

        chunks = service.chunk_document(
            document_id=document.id,
            document_repository=DocumentRepository(session),
            ingestion_job_repository=IngestionJobRepository(session),
            chunk_repository=DocumentChunkRepository(session),
        )
        loaded_document = DocumentRepository(session).get(document.id)

    assert [chunk.index for chunk in chunks] == [0, 1, 2]
    assert chunks[0].metadata["source_parsed_text_uri"] == stored.uri
    assert loaded_document is not None
    assert loaded_document.status is loaded_document.status.CHUNKED
