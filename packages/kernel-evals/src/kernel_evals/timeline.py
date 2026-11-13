"""Versioned golden timelines, independent of runtime/storage implementations."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kernel_evals.models import EvalAssertionResult, EvalCaseResult, EvalReport


class TimelineModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TimelineEvent(TimelineModel):
    type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class TimelineObservation(TimelineModel):
    status: str
    error_type: str | None = None
    events: tuple[TimelineEvent, ...]
    facts: dict[str, Any] = Field(default_factory=dict)


class TimelineCase(TimelineModel):
    name: str = Field(min_length=1)
    expected: TimelineObservation


class TimelineDataset(TimelineModel):
    schema_version: Literal[1]
    name: str = Field(min_length=1)
    cases: tuple[TimelineCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_names(self) -> TimelineDataset:
        names = [case.name for case in self.cases]
        if len(set(names)) != len(names):
            raise ValueError("Timeline case names must be unique.")
        return self


def load_timeline_dataset(path: str | Path) -> TimelineDataset:
    return TimelineDataset.model_validate_json(Path(path).read_text(encoding="utf-8"))


def compare_timeline(case: TimelineCase, actual: TimelineObservation) -> EvalCaseResult:
    """Compare order exactly; golden payload/fact fields are required subsets.

    UUIDs, wall clocks and timings belong outside goldens. Unexpected event types
    are never silently filtered out. Only selected golden fields enter reports.
    """
    assertions = [
        _equal("status", case.expected.status, actual.status),
        _equal("error_type", case.expected.error_type, actual.error_type),
    ]
    expected_types = [event.type for event in case.expected.events]
    actual_types = [event.type for event in actual.events]
    if expected_types != actual_types:
        index = next(
            (
                i
                for i in range(min(len(expected_types), len(actual_types)))
                if expected_types[i] != actual_types[i]
            ),
            min(len(expected_types), len(actual_types)),
        )
        expected_type = expected_types[index] if index < len(expected_types) else "<end>"
        actual_type = actual_types[index] if index < len(actual_types) else "<end>"
        assertions.append(
            EvalAssertionResult(
                name="event_order",
                passed=False,
                message=(
                    f"First divergence at event[{index}]: expected {expected_type!r}, "
                    f"observed {actual_type!r}; event counts "
                    f"{len(expected_types)} expected / {len(actual_types)} observed. "
                    "Inspect runtime transitions and persisted event order; do not "
                    "regenerate the golden without reviewing the behavior change."
                ),
            )
        )
    else:
        assertions.append(EvalAssertionResult("event_order", True, "Exact event order matched."))
        for index, (expected_event, actual_event) in enumerate(
            zip(case.expected.events, actual.events, strict=True)
        ):
            assertions.extend(
                _subset(
                    f"events[{index}].{expected_event.type}.payload",
                    expected_event.payload,
                    actual_event.payload,
                )
            )
    assertions.extend(_subset("facts", case.expected.facts, actual.facts))
    return EvalCaseResult(
        case_name=case.name,
        passed=all(assertion.passed for assertion in assertions),
        assertions=tuple(assertions),
        error_type=actual.error_type,
    )


async def run_timeline_dataset(
    dataset: TimelineDataset,
    execute: Callable[[str], Awaitable[TimelineObservation]],
) -> EvalReport:
    results: list[EvalCaseResult] = []
    for case in dataset.cases:
        try:
            observation = await execute(case.name)
        except Exception as error:
            # Exception messages may contain arguments, credentials or response bodies.
            results.append(
                EvalCaseResult(
                    case_name=case.name,
                    passed=False,
                    assertions=(
                        EvalAssertionResult(
                            "fixture_execution",
                            False,
                            f"Fixture raised {type(error).__name__}; run the focused fixture "
                            "test for a local traceback. No golden comparison was performed.",
                        ),
                    ),
                    error_type=type(error).__name__,
                )
            )
        else:
            results.append(compare_timeline(case, observation))
    return EvalReport(name=dataset.name, case_results=tuple(results))


def _subset(
    path: str, expected: dict[str, Any], actual: dict[str, Any]
) -> list[EvalAssertionResult]:
    assertions = []
    for key, expected_value in expected.items():
        field = f"{path}.{key}"
        if key not in actual:
            assertions.append(EvalAssertionResult(field, False, f"Missing required field {field}."))
        elif isinstance(expected_value, dict) and isinstance(actual[key], dict):
            assertions.extend(_subset(field, expected_value, actual[key]))
        else:
            assertions.append(_equal(field, expected_value, actual[key]))
    return assertions


def _equal(name: str, expected: Any, actual: Any) -> EvalAssertionResult:
    # JSON comparison distinguishes true from 1 and ignores mapping key order.
    passed = json.dumps(expected, sort_keys=True) == json.dumps(actual, sort_keys=True)
    return EvalAssertionResult(
        name=name,
        passed=passed,
        message=(
            f"{name} matched."
            if passed
            else f"{name}: expected {expected!r}, observed {actual!r}. "
            "Inspect the corresponding transition, persisted record or execution count."
        ),
    )
