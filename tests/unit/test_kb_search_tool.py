from uuid import UUID

import pytest
from kernel_core import DocumentChunk, DocumentStatus, RiskLevel
from kernel_rag import DocumentIndexingService, KnowledgeBaseSearchTool
from kernel_storage import (
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from kernel_tools import ToolExecutor, ToolRegistry, ToolRequest, ToolValidationError
from sqlalchemy.orm import Session, sessionmaker


@pytest.mark.asyncio
async def test_kb_search_tool_returns_cited_results(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    knowledge_base_id, chunk_id = _create_indexed_document(
        sqlite_session_factory,
        content="alpha deployment rollback checklist",
    )
    tool = KnowledgeBaseSearchTool(session_factory=sqlite_session_factory)

    result = await tool.execute(
        {
            "knowledge_base_id": str(knowledge_base_id),
            "query": "alpha deployment rollback checklist",
            "top_k": 1,
        }
    )

    assert tool.metadata.name == "kb_search"
    assert tool.metadata.risk_level is RiskLevel.READ_ONLY
    assert result["knowledge_base_id"] == str(knowledge_base_id)
    assert result["query"] == "alpha deployment rollback checklist"
    assert result["model"] == "mock-embedding-v1"
    assert len(result["results"]) == 1
    first = result["results"][0]
    assert first["content"] == "alpha deployment rollback checklist"
    assert first["score"] >= 0.99
    assert first["citation"]["chunk_id"] == str(chunk_id)
    assert first["citation"]["document_title"] == "Deploy Guide"


@pytest.mark.asyncio
async def test_kb_search_tool_returns_empty_results_for_empty_kb(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="empty")

    tool = KnowledgeBaseSearchTool(session_factory=sqlite_session_factory)

    result = await tool.execute(
        {
            "knowledge_base_id": str(knowledge_base.id),
            "query": "anything",
        }
    )

    assert result["results"] == []


@pytest.mark.asyncio
async def test_kb_search_tool_schema_rejects_invalid_top_k(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    tool = KnowledgeBaseSearchTool(session_factory=sqlite_session_factory)
    registry = ToolRegistry()
    registry.register(tool)
    executor = ToolExecutor(registry=registry)

    with pytest.raises(ToolValidationError):
        await executor.execute(
            ToolRequest(
                tool_name="kb_search",
                arguments={
                    "knowledge_base_id": "00000000-0000-0000-0000-000000000000",
                    "query": "anything",
                    "top_k": 0,
                },
            )
        )


def _create_indexed_document(
    sqlite_session_factory: sessionmaker[Session],
    *,
    content: str,
) -> tuple[UUID, UUID]:
    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="kb")
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Deploy Guide",
            source_uri="object://local/docs/deploy.md",
            status=DocumentStatus.CHUNKED,
        )
        assert document is not None
        chunks = DocumentChunkRepository(session).replace_for_document(
            document_id=document.id,
            chunks=[
                DocumentChunk(
                    document_id=document.id,
                    index=0,
                    content=content,
                    start_char=0,
                    end_char=len(content),
                    token_count_estimate=4,
                    checksum="sha256:chunk",
                )
            ],
        )
        assert chunks is not None
        DocumentIndexingService().index_document(
            document_id=document.id,
            document_repository=DocumentRepository(session),
            chunk_repository=DocumentChunkRepository(session),
            embedding_repository=ChunkEmbeddingRepository(session),
        )
        return knowledge_base.id, chunks[0].id
