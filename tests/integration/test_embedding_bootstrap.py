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
    DashScopeEmbeddingProvider,
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


@pytest.mark.parametrize("backend", ["openai", "dashscope"])
def test_api_index_retrieve_and_worker_tool_use_selected_real_adapter(
    postgres_session_factory: sessionmaker[Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    backend: str,
) -> None:
    monkeypatch.setenv("AGENT_KERNEL_EMBEDDING_PROVIDER", backend)
    monkeypatch.setenv("OPENAI_API_KEY", "embedding-fixture-not-a-real-key")
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "fixture-embedding")
    monkeypatch.setenv("OPENAI_EMBEDDING_DIMENSIONS", "3")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-fixture")
    monkeypatch.setenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v3")
    monkeypatch.setenv("DASHSCOPE_EMBEDDING_DIMENSIONS", "64")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = "text-embedding-v3" if backend == "dashscope" else "fixture-embedding"
    dimensions = 64 if backend == "dashscope" else 3
    requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        assert request.url.path == (
            "/compatible-mode/v1/embeddings" if backend == "dashscope" else "/v1/embeddings"
        )
        assert request.headers["authorization"] == (
            "Bearer dashscope-fixture"
            if backend == "dashscope"
            else "Bearer embedding-fixture-not-a-real-key"
        )
        assert payload["model"] == model and payload["dimensions"] == dimensions
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": i, "embedding": [1.0] + [0.0] * (dimensions - 1)}
                    for i, _ in enumerate(payload["input"])
                ]
            },
        )

    original_init = OpenAIEmbeddingProvider.__init__

    def init_with_fixture(self: OpenAIEmbeddingProvider, **kwargs: Any) -> None:
        kwargs["transport"] = httpx.MockTransport(handler)
        original_init(self, **kwargs)

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
        assert retrieved.json()["model"] == model
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
        assert result["output"]["tool"]["result"]["model"] == model
    assert len(requests) == 3


@pytest.mark.parametrize("failure", ["http_status", "nonfinite_vector"])
def test_dashscope_failed_second_batch_preserves_previous_pgvector_index(
    postgres_session_factory: sessionmaker[Session],
    failure: str,
) -> None:
    from kernel_core import DocumentChunk, DocumentStatus
    from kernel_rag import DocumentIndexingService, OpenAIEmbeddingError
    from kernel_storage import (
        ChunkEmbeddingRepository,
        DocumentChunkRepository,
        DocumentRepository,
        KnowledgeBaseRepository,
    )

    failing = False
    batch_sizes: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        texts = json.loads(request.content)["input"]
        batch_sizes.append(len(texts))
        if failing and len(batch_sizes) == 2:
            if failure == "http_status":
                return httpx.Response(503, json={"error": "synthetic unavailable"})
            return httpx.Response(
                200,
                content=json.dumps(
                    {"data": [{"index": 0, "embedding": [float("inf")] + [0.0] * 63}]}
                ),
            )
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": index, "embedding": [2.0 if failing else 1.0] + [0.0] * 63}
                    for index in range(len(texts))
                ]
            },
        )

    provider = DashScopeEmbeddingProvider(
        env={
            "DASHSCOPE_API_KEY": "synthetic-fixture",
            "DASHSCOPE_EMBEDDING_DIMENSIONS": "64",
        },
        transport=httpx.MockTransport(handler),
    )
    with postgres_session_factory() as session:
        kb = KnowledgeBaseRepository(session).create(name="batched")
        documents = DocumentRepository(session)
        document = documents.create(
            knowledge_base_id=kb.id,
            title="batched",
            source_uri="fixture",
            status=DocumentStatus.CHUNKED,
        )
        assert document is not None
        chunks = DocumentChunkRepository(session)
        chunks.replace_for_document(
            document_id=document.id,
            chunks=[
                DocumentChunk(
                    document_id=document.id,
                    index=index,
                    content="test",
                    start_char=index * 4,
                    end_char=index * 4 + 4,
                    token_count_estimate=1,
                    checksum=f"fixture-{index}",
                )
                for index in range(11)
            ],
        )
        embeddings = ChunkEmbeddingRepository(session)
        service = DocumentIndexingService(embedding_provider=provider)

        def index_document() -> None:
            service.index_document(
                document_id=document.id,
                document_repository=documents,
                chunk_repository=chunks,
                embedding_repository=embeddings,
            )

        index_document()
        before = embeddings.list_for_document(document_id=document.id)
        assert before is not None and len(before) == 11 and batch_sizes == [10, 1]
        failing = True
        batch_sizes.clear()
        with pytest.raises(OpenAIEmbeddingError):
            index_document()
        assert batch_sizes == [10, 1]
        assert embeddings.list_for_document(document_id=document.id) == before
        saved = documents.get(document.id)
        assert saved is not None and saved.status is DocumentStatus.INDEXED
        matches = embeddings.similarity_search(
            knowledge_base_id=kb.id,
            query_vector=[1.0] + [0.0] * 63,
            model="text-embedding-v3",
            limit=11,
        )
        assert len(matches) == 11
        assert all(item.vector[0] == 1.0 for item, _ in matches)


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
