import httpx
import pytest
from kernel_core import DocumentChunk, DocumentStatus
from kernel_rag import (
    DEFAULT_OPENAI_EMBEDDING_DIMENSIONS,
    DEFAULT_OPENAI_EMBEDDING_MODEL,
    DocumentIndexingService,
    MockEmbeddingProvider,
    OpenAIEmbeddingError,
    OpenAIEmbeddingProvider,
    get_openai_embedding_api_key,
    get_openai_embedding_dimensions,
    get_openai_embedding_model,
)
from kernel_storage import (
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from sqlalchemy.orm import Session, sessionmaker


def test_mock_embedding_provider_is_deterministic() -> None:
    provider = MockEmbeddingProvider()

    first = provider.embed_texts(["alpha", "beta"])
    second = provider.embed_texts(["alpha", "beta"])

    assert first == second
    assert len(first) == 2
    assert all(len(vector) == provider.dimensions for vector in first)
    assert first[0] != first[1]


def test_get_openai_embedding_api_key_reads_non_empty_value() -> None:
    assert get_openai_embedding_api_key({"OPENAI_API_KEY": "sk-test"}) == "sk-test"
    assert get_openai_embedding_api_key({"OPENAI_API_KEY": " "}) is None
    assert get_openai_embedding_api_key({}) is None


def test_openai_embedding_model_and_dimensions_config() -> None:
    assert get_openai_embedding_model({}) == DEFAULT_OPENAI_EMBEDDING_MODEL
    assert get_openai_embedding_model({"OPENAI_EMBEDDING_MODEL": "custom-embedding"}) == (
        "custom-embedding"
    )
    assert get_openai_embedding_dimensions({}) == DEFAULT_OPENAI_EMBEDDING_DIMENSIONS
    assert get_openai_embedding_dimensions({"OPENAI_EMBEDDING_DIMENSIONS": "256"}) == 256

    with pytest.raises(ValueError, match="must be an integer"):
        get_openai_embedding_dimensions({"OPENAI_EMBEDDING_DIMENSIONS": "many"})
    with pytest.raises(ValueError, match="must be positive"):
        get_openai_embedding_dimensions({"OPENAI_EMBEDDING_DIMENSIONS": "0"})


def test_openai_embedding_provider_returns_empty_for_empty_input() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(500)

    provider = OpenAIEmbeddingProvider(
        api_key=None,
        dimensions=3,
        transport=httpx.MockTransport(handler),
    )

    assert provider.embed_texts([]) == []
    assert requests == []


def test_openai_embedding_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIEmbeddingProvider(api_key=None, dimensions=3)

    with pytest.raises(OpenAIEmbeddingError) as error:
        provider.embed_texts(["alpha"])

    assert error.value.error_type == "missing_api_key"


def test_openai_embedding_provider_posts_embedding_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [
                    {"object": "embedding", "index": 1, "embedding": [0.4, 0.5, 0.6]},
                    {"object": "embedding", "index": 0, "embedding": [0.1, 0.2, 0.3]},
                ],
                "model": "text-embedding-3-small",
            },
        )

    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="text-embedding-3-small",
        dimensions=3,
        base_url="https://example.test/v1/",
        transport=httpx.MockTransport(handler),
    )

    vectors = provider.embed_texts(["alpha", "beta"])

    assert vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://example.test/v1/embeddings"
    assert request.headers["Authorization"] == "Bearer sk-test"
    assert request.headers["Content-Type"] == "application/json"
    assert request.read() == (
        b'{"model":"text-embedding-3-small","input":["alpha","beta"],"dimensions":3}'
    )


def test_openai_embedding_provider_wraps_http_status_errors() -> None:
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        dimensions=3,
        transport=httpx.MockTransport(lambda _request: httpx.Response(429)),
    )

    with pytest.raises(OpenAIEmbeddingError) as error:
        provider.embed_texts(["alpha"])

    assert error.value.error_type == "openai_embedding_status_error"


def test_openai_embedding_provider_rejects_malformed_response() -> None:
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        dimensions=3,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={"data": [{"index": 0, "embedding": [0.1, 0.2]}]},
            )
        ),
    )

    with pytest.raises(OpenAIEmbeddingError) as error:
        provider.embed_texts(["alpha"])

    assert error.value.error_type == "openai_embedding_dimension_mismatch"


def test_document_indexing_service_indexes_chunked_document(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    provider = MockEmbeddingProvider()

    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="kb")
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Chunked",
            source_uri="object://local/source.md",
            status=DocumentStatus.CHUNKED,
        )
        assert document is not None
        chunks = DocumentChunkRepository(session).replace_for_document(
            document_id=document.id,
            chunks=[
                DocumentChunk(
                    document_id=document.id,
                    index=0,
                    content="alpha",
                    start_char=0,
                    end_char=5,
                    token_count_estimate=2,
                    checksum="sha256:a",
                ),
                DocumentChunk(
                    document_id=document.id,
                    index=1,
                    content="beta",
                    start_char=6,
                    end_char=10,
                    token_count_estimate=1,
                    checksum="sha256:b",
                ),
            ],
        )
        assert chunks is not None

        result = DocumentIndexingService(embedding_provider=provider).index_document(
            document_id=document.id,
            document_repository=DocumentRepository(session),
            chunk_repository=DocumentChunkRepository(session),
            embedding_repository=ChunkEmbeddingRepository(session),
        )
        embeddings = ChunkEmbeddingRepository(session).list_for_document(document_id=document.id)
        loaded_document = DocumentRepository(session).get(document.id)

    assert result.document_id == document.id
    assert result.model == provider.model
    assert result.dimensions == provider.dimensions
    assert result.embedding_count == 2
    assert embeddings is not None
    assert len(embeddings) == 2
    assert all(embedding.model == provider.model for embedding in embeddings)
    assert loaded_document is not None
    assert loaded_document.status is DocumentStatus.INDEXED


def test_document_indexing_service_indexes_with_openai_embedding_provider(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        dimensions=3,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={
                    "data": [
                        {"index": 0, "embedding": [0.1, 0.2, 0.3]},
                        {"index": 1, "embedding": [0.4, 0.5, 0.6]},
                    ]
                },
            )
        ),
    )

    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="kb")
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Chunked",
            source_uri="object://local/source.md",
            status=DocumentStatus.CHUNKED,
        )
        assert document is not None
        chunks = DocumentChunkRepository(session).replace_for_document(
            document_id=document.id,
            chunks=[
                DocumentChunk(
                    document_id=document.id,
                    index=0,
                    content="alpha",
                    start_char=0,
                    end_char=5,
                    token_count_estimate=2,
                    checksum="sha256:a",
                ),
                DocumentChunk(
                    document_id=document.id,
                    index=1,
                    content="beta",
                    start_char=6,
                    end_char=10,
                    token_count_estimate=1,
                    checksum="sha256:b",
                ),
            ],
        )
        assert chunks is not None

        result = DocumentIndexingService(embedding_provider=provider).index_document(
            document_id=document.id,
            document_repository=DocumentRepository(session),
            chunk_repository=DocumentChunkRepository(session),
            embedding_repository=ChunkEmbeddingRepository(session),
        )
        embeddings = ChunkEmbeddingRepository(session).list_for_document(document_id=document.id)

    assert result.model == "text-embedding-3-small"
    assert result.dimensions == 3
    assert result.embedding_count == 2
    assert embeddings is not None
    assert [embedding.vector for embedding in embeddings] == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
