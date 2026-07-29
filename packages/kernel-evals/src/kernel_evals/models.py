"""Evaluation result models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalAssertionResult:
    name: str
    passed: bool
    message: str


@dataclass(frozen=True)
class EvalCaseResult:
    case_name: str
    passed: bool
    assertions: tuple[EvalAssertionResult, ...]
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class EvalReport:
    name: str
    case_results: tuple[EvalCaseResult, ...]

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.case_results)

    @property
    def passed_count(self) -> int:
        return sum(1 for result in self.case_results if result.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for result in self.case_results if not result.passed)
