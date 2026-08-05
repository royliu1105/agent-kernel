"""Deterministic provider-native tool-call behavior evals."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from kernel_evals.models import EvalAssertionResult, EvalCaseResult, EvalReport


@dataclass(frozen=True)
class ToolCallEvalToolCall:
    tool_name: str
    status: str
    provider_name: str | None = None
    provider_tool_call_id: str | None = None
    result: dict[str, Any] | None = None


@dataclass(frozen=True)
class ToolCallEvalObservation:
    run_status: str
    output: dict[str, Any] | None = None
    error_type: str | None = None
    events: tuple[str, ...] = ()
    tool_calls: tuple[ToolCallEvalToolCall, ...] = ()
    model_call_count: int | None = None


@dataclass(frozen=True)
class ToolCallEvalCase:
    name: str
    expected_run_status: str
    expected_error_type: str | None = None
    expected_tool_call_count: int | None = None
    expected_tool_name: str | None = None
    expected_tool_status: str | None = None
    expected_provider_tool_call_id: str | None = None
    expected_event_types: tuple[str, ...] = ()
    expected_model_call_count: int | None = None
    requires_provider_tool_loop: bool = False
    output_must_contain: tuple[str, ...] = ()


ToolCallEvalCallable = Callable[[ToolCallEvalCase], Awaitable[ToolCallEvalObservation]]


class ToolCallEvalRunner:
    def __init__(self, *, name: str = "tool-call-behavior") -> None:
        self._name = name

    async def run(
        self,
        *,
        cases: tuple[ToolCallEvalCase, ...],
        execute: ToolCallEvalCallable,
    ) -> EvalReport:
        case_results = [await self._run_case(case=case, execute=execute) for case in cases]
        return EvalReport(
            name=self._name,
            case_results=tuple(case_results),
        )

    async def _run_case(
        self,
        *,
        case: ToolCallEvalCase,
        execute: ToolCallEvalCallable,
    ) -> EvalCaseResult:
        try:
            observation = await execute(case)
        except Exception as error:
            return EvalCaseResult(
                case_name=case.name,
                passed=False,
                assertions=(
                    EvalAssertionResult(
                        name="unexpected_error",
                        passed=False,
                        message=f"Unexpected eval execution error {type(error).__name__}: {error}",
                    ),
                ),
                error_type=type(error).__name__,
                error_message=str(error),
            )

        assertions = (
            _assert_run_status(case=case, observation=observation),
            _assert_error_type(case=case, observation=observation),
            _assert_tool_call_count(case=case, observation=observation),
            _assert_tool_name(case=case, observation=observation),
            _assert_tool_status(case=case, observation=observation),
            _assert_provider_tool_call_id(case=case, observation=observation),
            _assert_event_sequence(case=case, observation=observation),
            _assert_model_call_count(case=case, observation=observation),
            _assert_provider_tool_loop(case=case, observation=observation),
            _assert_output_content(case=case, observation=observation),
        )
        return EvalCaseResult(
            case_name=case.name,
            passed=all(assertion.passed for assertion in assertions),
            assertions=assertions,
            error_type=observation.error_type,
        )


def _assert_run_status(
    *,
    case: ToolCallEvalCase,
    observation: ToolCallEvalObservation,
) -> EvalAssertionResult:
    passed = observation.run_status == case.expected_run_status
    return EvalAssertionResult(
        name="run_status",
        passed=passed,
        message=(
            f"Run status was {observation.run_status}."
            if passed
            else (
                f"Run status was {observation.run_status}, expected "
                f"{case.expected_run_status}."
            )
        ),
    )


def _assert_error_type(
    *,
    case: ToolCallEvalCase,
    observation: ToolCallEvalObservation,
) -> EvalAssertionResult:
    passed = observation.error_type == case.expected_error_type
    expected = case.expected_error_type or "no error"
    actual = observation.error_type or "no error"
    return EvalAssertionResult(
        name="error_type",
        passed=passed,
        message=f"Error type was {actual}, expected {expected}.",
    )


def _assert_tool_call_count(
    *,
    case: ToolCallEvalCase,
    observation: ToolCallEvalObservation,
) -> EvalAssertionResult:
    if case.expected_tool_call_count is None:
        return EvalAssertionResult(
            name="tool_call_count",
            passed=True,
            message="Tool-call count assertion not required.",
        )

    actual = len(observation.tool_calls)
    passed = actual == case.expected_tool_call_count
    return EvalAssertionResult(
        name="tool_call_count",
        passed=passed,
        message=f"Observed {actual} tool call(s), expected {case.expected_tool_call_count}.",
    )


def _assert_tool_name(
    *,
    case: ToolCallEvalCase,
    observation: ToolCallEvalObservation,
) -> EvalAssertionResult:
    if case.expected_tool_name is None:
        return EvalAssertionResult(
            name="tool_name",
            passed=True,
            message="Tool-name assertion not required.",
        )

    tool_call = _first_tool_call(observation)
    passed = tool_call is not None and tool_call.tool_name == case.expected_tool_name
    actual = tool_call.tool_name if tool_call is not None else "none"
    return EvalAssertionResult(
        name="tool_name",
        passed=passed,
        message=f"Tool name was {actual}, expected {case.expected_tool_name}.",
    )


def _assert_tool_status(
    *,
    case: ToolCallEvalCase,
    observation: ToolCallEvalObservation,
) -> EvalAssertionResult:
    if case.expected_tool_status is None:
        return EvalAssertionResult(
            name="tool_status",
            passed=True,
            message="Tool-status assertion not required.",
        )

    tool_call = _first_tool_call(observation)
    passed = tool_call is not None and tool_call.status == case.expected_tool_status
    actual = tool_call.status if tool_call is not None else "none"
    return EvalAssertionResult(
        name="tool_status",
        passed=passed,
        message=f"Tool status was {actual}, expected {case.expected_tool_status}.",
    )


def _assert_provider_tool_call_id(
    *,
    case: ToolCallEvalCase,
    observation: ToolCallEvalObservation,
) -> EvalAssertionResult:
    if case.expected_provider_tool_call_id is None:
        return EvalAssertionResult(
            name="provider_tool_call_id",
            passed=True,
            message="Provider tool-call id assertion not required.",
        )

    tool_call = _first_tool_call(observation)
    actual = tool_call.provider_tool_call_id if tool_call is not None else None
    passed = actual == case.expected_provider_tool_call_id
    return EvalAssertionResult(
        name="provider_tool_call_id",
        passed=passed,
        message=(
            f"Provider tool-call id was {actual or 'none'}, expected "
            f"{case.expected_provider_tool_call_id}."
        ),
    )


def _assert_event_sequence(
    *,
    case: ToolCallEvalCase,
    observation: ToolCallEvalObservation,
) -> EvalAssertionResult:
    if not case.expected_event_types:
        return EvalAssertionResult(
            name="event_sequence",
            passed=True,
            message="Event sequence assertion not required.",
        )

    passed = observation.events == case.expected_event_types
    return EvalAssertionResult(
        name="event_sequence",
        passed=passed,
        message=(
            "Observed expected event sequence."
            if passed
            else (
                f"Event sequence was {list(observation.events)}, expected "
                f"{list(case.expected_event_types)}."
            )
        ),
    )


def _assert_model_call_count(
    *,
    case: ToolCallEvalCase,
    observation: ToolCallEvalObservation,
) -> EvalAssertionResult:
    if case.expected_model_call_count is None:
        return EvalAssertionResult(
            name="model_call_count",
            passed=True,
            message="Model-call count assertion not required.",
        )
    if observation.model_call_count is None:
        return EvalAssertionResult(
            name="model_call_count",
            passed=False,
            message="Model-call count was not observed.",
        )

    passed = observation.model_call_count == case.expected_model_call_count
    return EvalAssertionResult(
        name="model_call_count",
        passed=passed,
        message=(
            f"Model call count was {observation.model_call_count}, expected "
            f"{case.expected_model_call_count}."
        ),
    )


def _assert_provider_tool_loop(
    *,
    case: ToolCallEvalCase,
    observation: ToolCallEvalObservation,
) -> EvalAssertionResult:
    if not case.requires_provider_tool_loop:
        return EvalAssertionResult(
            name="provider_tool_loop",
            passed=True,
            message="Provider tool loop assertion not required.",
        )

    passed = observation.output is not None and "provider_tool_loop" in observation.output
    return EvalAssertionResult(
        name="provider_tool_loop",
        passed=passed,
        message=(
            "Output included provider_tool_loop."
            if passed
            else "Expected output.provider_tool_loop to be present."
        ),
    )


def _assert_output_content(
    *,
    case: ToolCallEvalCase,
    observation: ToolCallEvalObservation,
) -> EvalAssertionResult:
    if not case.output_must_contain:
        return EvalAssertionResult(
            name="output_content",
            passed=True,
            message="Output content assertion not required.",
        )

    output_text = json.dumps(observation.output or {}, sort_keys=True)
    missing_terms = [term for term in case.output_must_contain if term not in output_text]
    return EvalAssertionResult(
        name="output_content",
        passed=not missing_terms,
        message=(
            "Output contained all required terms."
            if not missing_terms
            else f"Output missed required term(s): {', '.join(missing_terms)}."
        ),
    )


def _first_tool_call(observation: ToolCallEvalObservation) -> ToolCallEvalToolCall | None:
    return observation.tool_calls[0] if observation.tool_calls else None
