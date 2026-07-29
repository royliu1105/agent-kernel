from collections.abc import Callable
from uuid import UUID

from kernel_core import DocumentChunk, DocumentStatus
from kernel_evals import RagEvalCase, RagEvalRunner
from kernel_rag import DocumentIndexingService, RetrievalResponse, Retriever
from kernel_storage import (
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from sqlalchemy.orm import Session, sessionmaker


def test_rag_eval_runner_passes_relevance_and_citation_cases(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    knowledge_base_id = _create_indexed_document(
        sqlite_session_factory,
        content="alpha deployment rollback checklist",
    )

    report = RagEvalRunner().run(
        cases=(
            RagEvalCase(
                name="deployment-rollback-relevance",
                query="alpha deployment rollback checklist",
                top_k=1,
                top_result_must_contain=("rollback", "deployment"),
            ),
        ),
        retrieve=_retrieval_callable(
            sqlite_session_factory=sqlite_session_factory,
            knowledge_base_id=knowledge_base_id,
        ),
    )

    assert report.passed is True
    assert report.passed_count == 1
    assert report.failed_count == 0
    case_result = report.case_results[0]
    assert case_result.passed is True
    assert {assertion.name for assertion in case_result.assertions} == {
        "empty_result",
        "min_results",
        "top_result_contains",
        "citations",
    }


def test_rag_eval_runner_records_readable_failure_reasons(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    knowledge_base_id = _create_indexed_document(
        sqlite_session_factory,
        content="alpha deployment rollback checklist",
    )

    report = RagEvalRunner().run(
        cases=(
            RagEvalCase(
                name="wrong-top-result-expectation",
                query="alpha deployment rollback checklist",
                top_k=1,
                top_result_must_contain=("billing",),
            ),
        ),
        retrieve=_retrieval_callable(
            sqlite_session_factory=sqlite_session_factory,
            knowledge_base_id=knowledge_base_id,
        ),
    )

    assert report.passed is False
    assert report.passed_count == 0
    assert report.failed_count == 1
    failed_assertions = [
        assertion for assertion in report.case_results[0].assertions if not assertion.passed
    ]
    assert len(failed_assertions) == 1
    assert failed_assertions[0].name == "top_result_contains"
    assert "billing" in failed_assertions[0].message


def test_rag_eval_runner_passes_empty_knowledge_base_case(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="empty")

    report = RagEvalRunner().run(
        cases=(
            RagEvalCase(
                name="empty-kb",
                query="anything",
                expect_empty=True,
                min_results=0,
            ),
        ),
        retrieve=_retrieval_callable(
            sqlite_session_factory=sqlite_session_factory,
            knowledge_base_id=knowledge_base.id,
        ),
    )

    assert report.passed is True
    assert report.case_results[0].assertions[0].name == "empty_result"
    assert report.case_results[0].assertions[0].passed is True


def test_rag_eval_runner_passes_expected_missing_knowledge_base_error(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    report = RagEvalRunner().run(
        cases=(
            RagEvalCase(
                name="missing-kb",
                query="anything",
                expected_error_type="KnowledgeBaseNotFoundError",
            ),
        ),
        retrieve=_retrieval_callable(
            sqlite_session_factory=sqlite_session_factory,
            knowledge_base_id=UUID("00000000-0000-0000-0000-000000000000"),
        ),
    )

    assert report.passed is True
    assert report.case_results[0].error_type == "KnowledgeBaseNotFoundError"
    assert report.case_results[0].assertions[0].message.startswith("Received expected error")


def _retrieval_callable(
    *,
    sqlite_session_factory: sessionmaker[Session],
    knowledge_base_id: UUID,
) -> Callable[[str, int], RetrievalResponse]:
    def retrieve(query: str, top_k: int) -> RetrievalResponse:
        with sqlite_session_factory() as session:
            return Retriever().retrieve(
                knowledge_base_id=knowledge_base_id,
                query=query,
                top_k=top_k,
                knowledge_base_repository=KnowledgeBaseRepository(session),
                document_repository=DocumentRepository(session),
                chunk_repository=DocumentChunkRepository(session),
                embedding_repository=ChunkEmbeddingRepository(session),
            )

    return retrieve


def _create_indexed_document(
    sqlite_session_factory: sessionmaker[Session],
    *,
    content: str,
) -> UUID:
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
        return knowledge_base.id
