"""Eval report serialization helpers."""

from __future__ import annotations

from typing import Any

from kernel_evals.models import EvalAssertionResult, EvalCaseResult, EvalReport


def eval_report_to_dict(report: EvalReport) -> dict[str, Any]:
    """Serialize an eval report to a stable JSON-compatible dictionary."""

    return {
        "name": report.name,
        "passed": report.passed,
        "passed_count": report.passed_count,
        "failed_count": report.failed_count,
        "case_count": len(report.case_results),
        "cases": [_case_result_to_dict(result) for result in report.case_results],
    }


def _case_result_to_dict(result: EvalCaseResult) -> dict[str, Any]:
    return {
        "name": result.case_name,
        "passed": result.passed,
        "error_type": result.error_type,
        "error_message": result.error_message,
        "assertions": [_assertion_to_dict(assertion) for assertion in result.assertions],
    }


def _assertion_to_dict(assertion: EvalAssertionResult) -> dict[str, Any]:
    return {
        "name": assertion.name,
        "passed": assertion.passed,
        "message": assertion.message,
    }
