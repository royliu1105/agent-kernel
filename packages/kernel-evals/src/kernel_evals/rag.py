"""Deterministic RAG behavior evals."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from kernel_evals.models import EvalAssertionResult, EvalCaseResult, EvalReport


class RetrievedCitation(Protocol):
    @property
    def document_id(self) -> object: ...

    @property
    def document_title(self) -> str: ...

    @property
    def document_source_uri(self) -> str: ...

    @property
    def chunk_id(self) -> object: ...

    @property
    def chunk_index(self) -> int: ...

    @property
    def start_char(self) -> int: ...

    @property
    def end_char(self) -> int: ...


class RetrievedResult(Protocol):
    @property
    def content(self) -> str: ...

    @property
    def score(self) -> float: ...

    @property
    def citation(self) -> RetrievedCitation: ...


class RetrievalLikeResponse(Protocol):
    @property
    def results(self) -> Sequence[RetrievedResult]: ...


RetrievalCallable = Callable[[str, int], RetrievalLikeResponse]


@dataclass(frozen=True)
class RagEvalCase:
    name: str
    query: str
    top_k: int = 5
    min_results: int = 1
    max_results: int | None = None
    min_top_score: float | None = None
    top_result_must_contain: tuple[str, ...] = ()
    citation_source_uri_must_contain: tuple[str, ...] = ()
    all_results_require_citations: bool = True
    expect_empty: bool = False
    expected_error_type: str | None = None


class RagEvalRunner:
    def __init__(self, *, name: str = "rag-behavior") -> None:
        self._name = name

    def run(
        self,
        *,
        cases: tuple[RagEvalCase, ...],
        retrieve: RetrievalCallable,
    ) -> EvalReport:
        return EvalReport(
            name=self._name,
            case_results=tuple(self._run_case(case=case, retrieve=retrieve) for case in cases),
        )

    def _run_case(
        self,
        *,
        case: RagEvalCase,
        retrieve: RetrievalCallable,
    ) -> EvalCaseResult:
        try:
            response = retrieve(case.query, case.top_k)
        except Exception as error:
            return _error_case_result(case=case, error=error)

        if case.expected_error_type is not None:
            return EvalCaseResult(
                case_name=case.name,
                passed=False,
                assertions=(
                    EvalAssertionResult(
                        name="expected_error",
                        passed=False,
                        message=(
                            f"Expected {case.expected_error_type}, but retrieval succeeded."
                        ),
                    ),
                ),
            )

        assertions = [
            _assert_empty_behavior(case=case, response=response),
            _assert_min_results(case=case, response=response),
            _assert_max_results(case=case, response=response),
            _assert_min_top_score(case=case, response=response),
            _assert_top_result_contains(case=case, response=response),
            _assert_citations(case=case, response=response),
            _assert_citation_source_uri(case=case, response=response),
        ]
        return EvalCaseResult(
            case_name=case.name,
            passed=all(assertion.passed for assertion in assertions),
            assertions=tuple(assertions),
        )


def _error_case_result(*, case: RagEvalCase, error: Exception) -> EvalCaseResult:
    error_type = type(error).__name__
    if case.expected_error_type == error_type:
        return EvalCaseResult(
            case_name=case.name,
            passed=True,
            assertions=(
                EvalAssertionResult(
                    name="expected_error",
                    passed=True,
                    message=f"Received expected error {error_type}.",
                ),
            ),
            error_type=error_type,
            error_message=str(error),
        )

    return EvalCaseResult(
        case_name=case.name,
        passed=False,
        assertions=(
            EvalAssertionResult(
                name="unexpected_error",
                passed=False,
                message=f"Unexpected error {error_type}: {error}",
            ),
        ),
        error_type=error_type,
        error_message=str(error),
    )


def _assert_empty_behavior(
    *,
    case: RagEvalCase,
    response: RetrievalLikeResponse,
) -> EvalAssertionResult:
    if not case.expect_empty:
        return EvalAssertionResult(
            name="empty_result",
            passed=True,
            message="Empty result assertion not required.",
        )

    result_count = len(response.results)
    return EvalAssertionResult(
        name="empty_result",
        passed=result_count == 0,
        message=(
            "Expected no retrieval results."
            if result_count == 0
            else f"Expected no retrieval results, got {result_count}."
        ),
    )


def _assert_min_results(
    *,
    case: RagEvalCase,
    response: RetrievalLikeResponse,
) -> EvalAssertionResult:
    if case.expect_empty:
        return EvalAssertionResult(
            name="min_results",
            passed=True,
            message="Minimum result assertion skipped for empty-result case.",
        )

    result_count = len(response.results)
    passed = result_count >= case.min_results
    return EvalAssertionResult(
        name="min_results",
        passed=passed,
        message=(
            f"Retrieved {result_count} result(s), expected at least {case.min_results}."
        ),
    )


def _assert_max_results(
    *,
    case: RagEvalCase,
    response: RetrievalLikeResponse,
) -> EvalAssertionResult:
    if case.expect_empty or case.max_results is None:
        return EvalAssertionResult(
            name="max_results",
            passed=True,
            message="Maximum result assertion not required.",
        )

    result_count = len(response.results)
    passed = result_count <= case.max_results
    return EvalAssertionResult(
        name="max_results",
        passed=passed,
        message=(
            f"Retrieved {result_count} result(s), expected at most {case.max_results}."
        ),
    )


def _assert_min_top_score(
    *,
    case: RagEvalCase,
    response: RetrievalLikeResponse,
) -> EvalAssertionResult:
    if case.expect_empty or case.min_top_score is None:
        return EvalAssertionResult(
            name="min_top_score",
            passed=True,
            message="Top-score assertion not required.",
        )
    if not response.results:
        return EvalAssertionResult(
            name="min_top_score",
            passed=False,
            message="Expected top score, but retrieval returned no results.",
        )

    score = response.results[0].score
    return EvalAssertionResult(
        name="min_top_score",
        passed=score >= case.min_top_score,
        message=(
            f"Top score {score:.6f} met minimum {case.min_top_score:.6f}."
            if score >= case.min_top_score
            else f"Top score {score:.6f} was below minimum {case.min_top_score:.6f}."
        ),
    )


def _assert_top_result_contains(
    *,
    case: RagEvalCase,
    response: RetrievalLikeResponse,
) -> EvalAssertionResult:
    if case.expect_empty or not case.top_result_must_contain:
        return EvalAssertionResult(
            name="top_result_contains",
            passed=True,
            message="Top-result content assertion not required.",
        )
    if not response.results:
        return EvalAssertionResult(
            name="top_result_contains",
            passed=False,
            message="Expected top result, but retrieval returned no results.",
        )

    top_content = response.results[0].content.lower()
    missing_terms = [
        term for term in case.top_result_must_contain if term.lower() not in top_content
    ]
    return EvalAssertionResult(
        name="top_result_contains",
        passed=not missing_terms,
        message=(
            "Top result contained all required terms."
            if not missing_terms
            else f"Top result missed required term(s): {', '.join(missing_terms)}."
        ),
    )


def _assert_citations(
    *,
    case: RagEvalCase,
    response: RetrievalLikeResponse,
) -> EvalAssertionResult:
    if case.expect_empty or not case.all_results_require_citations:
        return EvalAssertionResult(
            name="citations",
            passed=True,
            message="Citation assertion not required.",
        )

    missing_indexes = [
        index
        for index, result in enumerate(response.results)
        if not _has_valid_citation(result)
    ]
    return EvalAssertionResult(
        name="citations",
        passed=not missing_indexes,
        message=(
            "All retrieved results included valid citations."
            if not missing_indexes
            else f"Missing or invalid citation for result index(es): {missing_indexes}."
        ),
    )


def _assert_citation_source_uri(
    *,
    case: RagEvalCase,
    response: RetrievalLikeResponse,
) -> EvalAssertionResult:
    if case.expect_empty or not case.citation_source_uri_must_contain:
        return EvalAssertionResult(
            name="citation_source_uri",
            passed=True,
            message="Citation source URI assertion not required.",
        )

    missing_indexes: list[int] = []
    for index, result in enumerate(response.results):
        source_uri = result.citation.document_source_uri.lower()
        if any(
            term.lower() not in source_uri
            for term in case.citation_source_uri_must_contain
        ):
            missing_indexes.append(index)

    return EvalAssertionResult(
        name="citation_source_uri",
        passed=not missing_indexes,
        message=(
            "All citation source URIs contained required terms."
            if not missing_indexes
            else (
                "Citation source URI missed required term(s) for result "
                f"index(es): {missing_indexes}."
            )
        ),
    )


def _has_valid_citation(result: RetrievedResult) -> bool:
    citation = result.citation
    return (
        citation.document_id is not None
        and citation.document_title != ""
        and citation.chunk_id is not None
        and citation.chunk_index >= 0
        and citation.start_char >= 0
        and citation.end_char >= citation.start_char
    )
