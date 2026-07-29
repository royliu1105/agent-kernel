"""File-backed eval dataset loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kernel_evals.models import EvalReport
from kernel_evals.rag import RagEvalCase, RagEvalRunner, RetrievalCallable


class EvalDatasetError(ValueError):
    """Raised when an eval dataset is invalid."""


@dataclass(frozen=True)
class RagEvalDataset:
    """A deterministic RAG eval dataset loaded from disk."""

    name: str
    cases: tuple[RagEvalCase, ...]

    def run(self, retrieve: RetrievalCallable) -> EvalReport:
        """Run this dataset with the RAG eval runner."""

        return RagEvalRunner(name=self.name).run(cases=self.cases, retrieve=retrieve)


def load_rag_eval_dataset(path: str | Path) -> RagEvalDataset:
    """Load a JSON RAG eval dataset from disk."""

    dataset_path = Path(path)
    try:
        raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise EvalDatasetError(f"Could not read eval dataset {dataset_path}: {error}") from error
    except json.JSONDecodeError as error:
        raise EvalDatasetError(f"Invalid JSON eval dataset {dataset_path}: {error.msg}") from error

    return rag_eval_dataset_from_mapping(raw)


def rag_eval_dataset_from_mapping(raw: object) -> RagEvalDataset:
    """Build a RAG eval dataset from a decoded JSON object."""

    if not isinstance(raw, dict):
        raise EvalDatasetError("Eval dataset must be a JSON object.")

    name = _required_string(raw, "name", path="dataset")
    raw_cases = raw.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise EvalDatasetError("Eval dataset field 'cases' must be a non-empty array.")

    return RagEvalDataset(
        name=name,
        cases=tuple(_case_from_mapping(case, index=index) for index, case in enumerate(raw_cases)),
    )


def _case_from_mapping(raw: object, *, index: int) -> RagEvalCase:
    path = f"cases[{index}]"
    if not isinstance(raw, dict):
        raise EvalDatasetError(f"{path} must be a JSON object.")

    return RagEvalCase(
        name=_required_string(raw, "name", path=path),
        query=_required_string(raw, "query", path=path),
        top_k=_optional_int(raw, "top_k", path=path, default=5, minimum=1),
        min_results=_optional_int(raw, "min_results", path=path, default=1, minimum=0),
        top_result_must_contain=_optional_string_tuple(
            raw,
            "top_result_must_contain",
            path=path,
        ),
        all_results_require_citations=_optional_bool(
            raw,
            "all_results_require_citations",
            path=path,
            default=True,
        ),
        expect_empty=_optional_bool(raw, "expect_empty", path=path, default=False),
        expected_error_type=_optional_string(raw, "expected_error_type", path=path),
    )


def _required_string(raw: dict[str, Any], key: str, *, path: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or value == "":
        raise EvalDatasetError(f"{path}.{key} must be a non-empty string.")
    return value


def _optional_string(raw: dict[str, Any], key: str, *, path: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or value == "":
        raise EvalDatasetError(f"{path}.{key} must be a non-empty string when provided.")
    return value


def _optional_bool(raw: dict[str, Any], key: str, *, path: str, default: bool) -> bool:
    value = raw.get(key, default)
    if not isinstance(value, bool):
        raise EvalDatasetError(f"{path}.{key} must be a boolean.")
    return value


def _optional_int(
    raw: dict[str, Any],
    key: str,
    *,
    path: str,
    default: int,
    minimum: int,
) -> int:
    value = raw.get(key, default)
    if not isinstance(value, int) or value < minimum:
        raise EvalDatasetError(
            f"{path}.{key} must be an integer greater than or equal to {minimum}."
        )
    return value


def _optional_string_tuple(
    raw: dict[str, Any],
    key: str,
    *,
    path: str,
) -> tuple[str, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list):
        raise EvalDatasetError(f"{path}.{key} must be an array of strings.")
    terms: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or item == "":
            raise EvalDatasetError(f"{path}.{key}[{index}] must be a non-empty string.")
        terms.append(item)
    return tuple(terms)
