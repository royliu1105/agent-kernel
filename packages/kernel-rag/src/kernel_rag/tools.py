"""RAG-backed tool implementations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from kernel_core import RiskLevel
from kernel_storage import (
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from kernel_tools import ToolMetadata, ToolRegistry, create_default_tool_registry
from sqlalchemy.orm import Session, sessionmaker

from kernel_rag.retrieval import Retriever


class KnowledgeBaseSearchTool:
    """Read-only tool that searches one indexed knowledge base."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        retriever: Retriever | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._retriever = retriever or Retriever()

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="kb_search",
            description="Search indexed chunks in a knowledge base and return cited results.",
            input_schema={
                "type": "object",
                "properties": {
                    "knowledge_base_id": {"type": "string", "format": "uuid"},
                    "query": {"type": "string", "minLength": 1},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["knowledge_base_id", "query"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "knowledge_base_id": {"type": "string"},
                    "query": {"type": "string"},
                    "model": {"type": "string"},
                    "results": {"type": "array"},
                },
                "required": ["knowledge_base_id", "query", "model", "results"],
                "additionalProperties": False,
            },
            risk_level=RiskLevel.READ_ONLY,
            timeout_ms=5_000,
            enabled=True,
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        knowledge_base_id = UUID(arguments["knowledge_base_id"])
        query = arguments["query"]
        top_k = arguments.get("top_k", 5)
        if not isinstance(query, str):
            raise TypeError("query must be a string.")
        if not isinstance(top_k, int):
            raise TypeError("top_k must be an integer.")

        with self._session_factory() as session:
            response = self._retriever.retrieve(
                knowledge_base_id=knowledge_base_id,
                query=query,
                top_k=top_k,
                knowledge_base_repository=KnowledgeBaseRepository(session),
                document_repository=DocumentRepository(session),
                chunk_repository=DocumentChunkRepository(session),
                embedding_repository=ChunkEmbeddingRepository(session),
            )

        return {
            "knowledge_base_id": str(response.knowledge_base_id),
            "query": response.query,
            "model": response.model,
            "results": [
                {
                    "content": result.content,
                    "score": result.score,
                    "citation": {
                        "knowledge_base_id": str(result.citation.knowledge_base_id),
                        "document_id": str(result.citation.document_id),
                        "document_title": result.citation.document_title,
                        "document_source_uri": result.citation.document_source_uri,
                        "chunk_id": str(result.citation.chunk_id),
                        "chunk_index": result.citation.chunk_index,
                        "start_char": result.citation.start_char,
                        "end_char": result.citation.end_char,
                    },
                    "metadata": result.metadata,
                }
                for result in response.results
            ],
        }


def create_rag_tool_registry(*, session_factory: sessionmaker[Session]) -> ToolRegistry:
    """Return default tools plus RAG-backed tools."""

    registry = create_default_tool_registry()
    registry.register(KnowledgeBaseSearchTool(session_factory=session_factory))
    return registry
