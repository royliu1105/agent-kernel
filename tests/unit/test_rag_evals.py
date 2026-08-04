import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import pytest
from kernel_core import DocumentChunk, DocumentStatus
from kernel_evals import (
    EvalDatasetError,
    RagEvalCase,
    RagEvalRunner,
    eval_report_to_dict,
    load_rag_eval_dataset,
)
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
        "max_results",
        "min_top_score",
        "top_result_contains",
        "citations",
        "citation_source_uri",
    }


def test_rag_eval_runner_checks_result_limit_score_and_source_uri(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    knowledge_base_id = _create_indexed_document(
        sqlite_session_factory,
        content=(
            "alpha deployment rollback checklist",
            "alpha deployment health checks",
            "alpha deployment incident review",
        ),
    )

    report = RagEvalRunner().run(
        cases=(
            RagEvalCase(
                name="retrieval-contract",
                query="alpha deployment rollback checklist",
                top_k=2,
                min_results=1,
                max_results=2,
                min_top_score=0.0,
                top_result_must_contain=("deployment",),
                citation_source_uri_must_contain=("deploy.md",),
            ),
        ),
        retrieve=_retrieval_callable(
            sqlite_session_factory=sqlite_session_factory,
            knowledge_base_id=knowledge_base_id,
        ),
    )

    assert report.passed is True
    assertions = {assertion.name: assertion for assertion in report.case_results[0].assertions}
    assert assertions["max_results"].passed is True
    assert assertions["min_top_score"].passed is True
    assert assertions["citation_source_uri"].passed is True


def test_rag_eval_runner_reports_score_and_source_uri_failures() -> None:
    report = RagEvalRunner().run(
        cases=(
            RagEvalCase(
                name="strict-contract",
                query="deployment",
                max_results=1,
                min_top_score=0.9,
                citation_source_uri_must_contain=("runbook.md",),
            ),
        ),
        retrieve=lambda _query, _top_k: _FakeRetrievalResponse(
            results=(
                _FakeRetrievalResult(
                    content="deployment notes",
                    score=0.5,
                    citation=_FakeCitation(document_source_uri="object://local/docs/notes.md"),
                ),
                _FakeRetrievalResult(
                    content="deployment backup",
                    score=0.4,
                    citation=_FakeCitation(document_source_uri="object://local/docs/backup.md"),
                ),
            )
        ),
    )

    assert report.passed is False
    failed = {
        assertion.name: assertion.message
        for assertion in report.case_results[0].assertions
        if not assertion.passed
    }
    assert "max_results" in failed
    assert "min_top_score" in failed
    assert "citation_source_uri" in failed


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


def test_load_rag_eval_dataset_from_json_file(tmp_path: Path) -> None:
    dataset_path = tmp_path / "rag-eval.json"
    dataset_path.write_text(
        json.dumps(
            {
                "name": "rag-smoke",
                "cases": [
                    {
                        "name": "deployment",
                        "query": "deployment rollback",
                        "top_k": 3,
                        "min_results": 1,
                        "max_results": 3,
                        "min_top_score": 0.0,
                        "top_result_must_contain": ["deployment", "rollback"],
                        "citation_source_uri_must_contain": ["deploy.md"],
                        "all_results_require_citations": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    dataset = load_rag_eval_dataset(dataset_path)

    assert dataset.name == "rag-smoke"
    assert dataset.cases == (
        RagEvalCase(
            name="deployment",
            query="deployment rollback",
            top_k=3,
            min_results=1,
            max_results=3,
            min_top_score=0.0,
            top_result_must_contain=("deployment", "rollback"),
            citation_source_uri_must_contain=("deploy.md",),
            all_results_require_citations=True,
        ),
    )


def test_load_rag_eval_dataset_reports_readable_validation_errors(tmp_path: Path) -> None:
    dataset_path = tmp_path / "invalid-rag-eval.json"
    dataset_path.write_text(
        json.dumps({"name": "bad", "cases": [{"name": "", "query": "anything"}]}),
        encoding="utf-8",
    )

    with pytest.raises(EvalDatasetError, match=r"cases\[0\].name"):
        load_rag_eval_dataset(dataset_path)


def test_loaded_rag_eval_dataset_runs_with_retrieval_callable(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    knowledge_base_id = _create_indexed_document(
        sqlite_session_factory,
        content="alpha deployment rollback checklist",
    )
    dataset_path = tmp_path / "rag-eval.json"
    dataset_path.write_text(
        json.dumps(
            {
                "name": "rag-smoke",
                "cases": [
                    {
                        "name": "deployment",
                        "query": "alpha deployment rollback checklist",
                        "top_k": 1,
                        "top_result_must_contain": ["deployment", "rollback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = load_rag_eval_dataset(dataset_path).run(
        _retrieval_callable(
            sqlite_session_factory=sqlite_session_factory,
            knowledge_base_id=knowledge_base_id,
        )
    )

    assert report.name == "rag-smoke"
    assert report.passed is True
    assert report.passed_count == 1


def test_eval_report_serializes_to_stable_dict(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    knowledge_base_id = _create_indexed_document(
        sqlite_session_factory,
        content="alpha deployment rollback checklist",
    )
    report = RagEvalRunner(name="rag-report").run(
        cases=(
            RagEvalCase(
                name="deployment",
                query="alpha deployment rollback checklist",
                top_k=1,
                top_result_must_contain=("deployment", "rollback"),
            ),
        ),
        retrieve=_retrieval_callable(
            sqlite_session_factory=sqlite_session_factory,
            knowledge_base_id=knowledge_base_id,
        ),
    )

    payload = eval_report_to_dict(report)

    assert payload["name"] == "rag-report"
    assert payload["passed"] is True
    assert payload["passed_count"] == 1
    assert payload["failed_count"] == 0
    assert payload["case_count"] == 1
    assert payload["cases"][0]["name"] == "deployment"
    assert payload["cases"][0]["assertions"][0]["name"] == "empty_result"


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
    content: str | tuple[str, ...],
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
        contents = (content,) if isinstance(content, str) else content
        chunks = DocumentChunkRepository(session).replace_for_document(
            document_id=document.id,
            chunks=[
                DocumentChunk(
                    document_id=document.id,
                    index=index,
                    content=chunk_content,
                    start_char=0,
                    end_char=len(chunk_content),
                    token_count_estimate=4,
                    checksum=f"sha256:chunk-{index}",
                )
                for index, chunk_content in enumerate(contents)
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


@dataclass(frozen=True)
class _FakeCitation:
    document_source_uri: str
    document_id: str = "doc"
    document_title: str = "Document"
    chunk_id: str = "chunk"
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 10


@dataclass(frozen=True)
class _FakeRetrievalResult:
    content: str
    score: float
    citation: _FakeCitation


@dataclass(frozen=True)
class _FakeRetrievalResponse:
    results: tuple[_FakeRetrievalResult, ...]
