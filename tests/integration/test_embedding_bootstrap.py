"""Production composition must select the same embedding backend end to end."""

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from agent_kernel_api.main import create_app
from agent_kernel_worker.main import _create_worker
from fastapi.testclient import TestClient
from kernel_rag import (
    LocalObjectStore,
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
    create_embedding_provider,
)
from sqlalchemy.orm import Session, sessionmaker


def test_embedding_selection_is_explicit_and_validated() -> None:
    assert isinstance(
        create_embedding_provider({"OPENAI_API_KEY": "fixture"}), MockEmbeddingProvider
    )
    with pytest.raises(ValueError, match="credentials"):
        create_embedding_provider({"AGENT_KERNEL_EMBEDDING_PROVIDER": "openai"})
    with pytest.raises(ValueError, match="mock or openai"):
        create_embedding_provider({"AGENT_KERNEL_EMBEDDING_PROVIDER": "typo"})


def test_api_index_retrieve_and_worker_tool_use_selected_real_adapter(
    postgres_session_factory: sessionmaker[Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_KERNEL_EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "embedding-fixture-not-a-real-key")
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "fixture-embedding")
    monkeypatch.setenv("OPENAI_EMBEDDING_DIMENSIONS", "3")
    requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        assert request.url.path == "/v1/embeddings"
        assert payload["model"] == "fixture-embedding" and payload["dimensions"] == 3
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": i, "embedding": [1.0, 0.0, 0.0]}
                    for i, _ in enumerate(payload["input"])
                ]
            },
        )

    original_init = OpenAIEmbeddingProvider.__init__

    def init_with_fixture(self: OpenAIEmbeddingProvider, **kwargs: Any) -> None:
        original_init(self, **kwargs, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(OpenAIEmbeddingProvider, "__init__", init_with_fixture)
    with TestClient(
        create_app(
            session_factory=postgres_session_factory,
            object_store=LocalObjectStore(root_path=tmp_path),
        )
    ) as client:
        kb = client.post("/v1/knowledge-bases", json={"name": "real embedding"}).json()["id"]
        uploaded = client.post(
            f"/v1/knowledge-bases/{kb}/documents/upload",
            files={"file": ("guide.md", b"alpha checklist", "text/markdown")},
        )
        assert uploaded.status_code == 201, uploaded.text
        doc = uploaded.json()["id"]
        assert client.post(f"/v1/documents/{doc}/ingest").status_code == 201
        assert client.post(f"/v1/documents/{doc}/chunk").status_code == 201
        indexed = client.post(f"/v1/documents/{doc}/index")
        assert indexed.status_code == 201, indexed.text
        retrieved = client.post(f"/v1/knowledge-bases/{kb}/retrieve", json={"query": "alpha"})
        assert retrieved.status_code == 200, retrieved.text
        assert retrieved.json()["model"] == "fixture-embedding"
        assert retrieved.json()["results"]
        agent = client.post("/v1/agents", json={"name": "search"}).json()["id"]
        run = client.post(
            f"/v1/agents/{agent}/runs",
            json={
                "input": {
                    "tool": {
                        "name": "kb_search",
                        "arguments": {"knowledge_base_id": kb, "query": "alpha"},
                    }
                }
            },
        ).json()["id"]
        assert client.post(f"/v1/runs/{run}/queue").status_code == 200
        worker = _create_worker(session_factory=postgres_session_factory)
        assert asyncio.run(worker.run_once()).succeeded_count == 1
        result = client.get(f"/v1/runs/{run}").json()
        assert result["output"]["tool"]["result"]["model"] == "fixture-embedding"
    assert len(requests) == 3


def test_embedding_failure_keeps_document_retryable(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    from kernel_core import DocumentChunk, DocumentStatus
    from kernel_rag import DocumentIndexingService, OpenAIEmbeddingError
    from kernel_storage import (
        ChunkEmbeddingRepository,
        DocumentChunkRepository,
        DocumentRepository,
        KnowledgeBaseRepository,
    )

    class FailingEmbedding(MockEmbeddingProvider):
        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            raise OpenAIEmbeddingError("Provider unavailable.")

    with postgres_session_factory() as session:
        kb = KnowledgeBaseRepository(session).create(name="retry")
        docs = DocumentRepository(session)
        doc = docs.create(
            knowledge_base_id=kb.id,
            title="retry",
            source_uri="fixture",
            status=DocumentStatus.CHUNKED,
        )
        assert doc is not None
        chunks = DocumentChunkRepository(session)
        chunks.replace_for_document(
            document_id=doc.id,
            chunks=[
                DocumentChunk(
                    document_id=doc.id,
                    index=0,
                    content="test",
                    start_char=0,
                    end_char=4,
                    token_count_estimate=1,
                    checksum="fixture",
                )
            ],
        )
        embeddings = ChunkEmbeddingRepository(session)
        with pytest.raises(OpenAIEmbeddingError):
            DocumentIndexingService(embedding_provider=FailingEmbedding()).index_document(
                document_id=doc.id,
                document_repository=docs,
                chunk_repository=chunks,
                embedding_repository=embeddings,
            )
        stored = docs.get(doc.id)
        assert stored is not None and stored.status is DocumentStatus.CHUNKED
        result = DocumentIndexingService().index_document(
            document_id=doc.id,
            document_repository=docs,
            chunk_repository=chunks,
            embedding_repository=embeddings,
        )
        assert result.embedding_count == 1
