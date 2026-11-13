from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Never

import pytest
from kernel_core import ToolCall
from kernel_evals.timeline import (
    TimelineDataset,
    compare_timeline,
    load_timeline_dataset,
    run_timeline_dataset,
)
from kernel_providers import LLMRequest, LLMResponse
from kernel_runtime import RetryPolicy
from kernel_runtime import execution as runtime_execution
from pydantic import ValidationError

SPEC = importlib.util.spec_from_file_location(
    "timeline_regression", Path(__file__).parents[2] / "scripts/timeline_regression.py"
)
assert SPEC is not None and SPEC.loader is not None
harness = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = harness
SPEC.loader.exec_module(harness)


@pytest.mark.asyncio
@pytest.mark.parametrize("name", sorted(harness.SCENARIOS))
async def test_golden_matches_persisted_runtime_behavior(name: str) -> None:
    dataset = load_timeline_dataset(harness.DEFAULT_GOLDEN)
    case = next(case for case in dataset.cases if case.name == name)
    actual = await harness.execute_scenario(name)
    result = compare_timeline(case, actual)
    assert result.passed, [a.message for a in result.assertions if not a.passed]
    assert actual.facts["stable_tool_call_key"]
    # New run UUIDs, wall clocks and measured execution durations cannot affect goldens.
    repeated = await harness.execute_scenario(name)
    assert repeated == actual


@pytest.mark.asyncio
async def test_real_retry_behavior_regression_fails_golden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        harness,
        "RetryPolicy",
        lambda **_: RetryPolicy(provider_max_attempts=1, tool_max_attempts=2),
    )
    dataset = load_timeline_dataset(harness.DEFAULT_GOLDEN)
    case = next(case for case in dataset.cases if case.name == "model-retry")
    actual = await harness.execute_scenario(case.name)
    assert actual.status == "failed"
    result = compare_timeline(case, actual)
    assert not result.passed
    failures = {a.name: a.message for a in result.assertions if not a.passed}
    assert "First divergence at event[3]" in failures["event_order"]
    assert "model_call_retrying" in failures["event_order"]
    assert "run_failed" in failures["event_order"]
    assert "expected 2, observed 1" in failures["facts.model_calls"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutation",
    [
        "remove_result",
        "corrupt_result",
        "remove_call",
        "wrong_call_id",
        "wrong_arguments",
        "changed_task",
        "wrong_internal_id",
    ],
)
async def test_native_followup_request_mutations_fail_release_gate(
    monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    original = runtime_execution._request_with_tool_result

    def mutate(
        *, initial_request: LLMRequest, initial_response: LLMResponse, tool_call: ToolCall
    ) -> LLMRequest:
        request = original(
            initial_request=initial_request, initial_response=initial_response, tool_call=tool_call
        )
        messages = list(request.messages)
        if mutation == "remove_result":
            messages.pop()
        elif mutation == "corrupt_result":
            payload = json.loads(messages[-1].content)
            payload["result"] = {"ok": False}
            messages[-1] = messages[-1].model_copy(update={"content": json.dumps(payload)})
        elif mutation == "remove_call":
            messages[1] = messages[1].model_copy(update={"metadata": {}})
        elif mutation == "wrong_call_id":
            messages[-1] = messages[-1].model_copy(
                update={
                    "metadata": {**messages[-1].metadata, "provider_tool_call_id": "different-call"}
                }
            )
        elif mutation == "wrong_arguments":
            calls = messages[1].metadata["tool_calls"]
            messages[1] = messages[1].model_copy(
                update={
                    "metadata": {
                        **messages[1].metadata,
                        "tool_calls": [{**calls[0], "arguments": {"unexpected": True}}],
                    }
                }
            )
        elif mutation == "changed_task":
            messages[0] = messages[0].model_copy(update={"content": "unrelated task"})
        else:
            # Keep the two request fields consistent, but break persisted correlation.
            wrong_id = "00000000-0000-0000-0000-000000000001"
            payload = json.loads(messages[-1].content)
            payload["tool_call_id"] = wrong_id
            messages[-1] = messages[-1].model_copy(
                update={
                    "metadata": {**messages[-1].metadata, "tool_call_id": wrong_id},
                    "content": json.dumps(payload),
                }
            )
        return request.model_copy(update={"messages": tuple(messages)})

    monkeypatch.setattr(runtime_execution, "_request_with_tool_result", mutate)
    dataset = load_timeline_dataset(harness.DEFAULT_GOLDEN)
    report = await run_timeline_dataset(dataset, harness.execute_scenario)
    assert not report.passed
    assert report.failed_count == 1
    native_result = next(case for case in report.case_results if case.case_name == "native-tool")
    assert not native_result.passed


def test_timeline_cli_rejects_removed_tool_result(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    original = runtime_execution._request_with_tool_result

    def omit_result(
        *, initial_request: LLMRequest, initial_response: LLMResponse, tool_call: ToolCall
    ) -> LLMRequest:
        request = original(
            initial_request=initial_request, initial_response=initial_response, tool_call=tool_call
        )
        return request.model_copy(update={"messages": request.messages[:-1]})

    monkeypatch.setattr(runtime_execution, "_request_with_tool_result", omit_result)
    assert harness.main([]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["failed_count"] == 1
    native = next(case for case in report["cases"] if case["name"] == "native-tool")
    assert not native["passed"]
    assert native["error_type"] == "FixtureContractError"


@pytest.mark.asyncio
async def test_payload_and_missing_fact_diagnostics_use_runtime_observation() -> None:
    dataset = load_timeline_dataset(harness.DEFAULT_GOLDEN)
    case = next(case for case in dataset.cases if case.name == "model-retry")
    actual = await harness.execute_scenario(case.name)
    events = list(actual.events)
    events[3] = events[3].model_copy(update={"payload": {**events[3].payload, "attempt": 99}})
    facts = {key: value for key, value in actual.facts.items() if key != "model_calls"}
    changed = actual.model_copy(update={"events": tuple(events), "facts": facts})
    result = compare_timeline(case, changed)
    failures = {a.name: a.message for a in result.assertions if not a.passed}
    assert "expected 2, observed 99" in failures["events[3].model_call_retrying.payload.attempt"]
    assert "Missing required field" in failures["facts.model_calls"]


@pytest.mark.asyncio
async def test_inserted_or_removed_event_is_not_filtered_out() -> None:
    dataset = load_timeline_dataset(harness.DEFAULT_GOLDEN)
    case = dataset.cases[0]
    actual = await harness.execute_scenario(case.name)
    for events in (actual.events[:-1], (*actual.events, actual.events[-1])):
        result = compare_timeline(case, actual.model_copy(update={"events": events}))
        assert not result.passed
        assert any("<end>" in a.message for a in result.assertions if not a.passed)


@pytest.mark.asyncio
async def test_fixture_exception_does_not_leak_error_content() -> None:
    dataset = load_timeline_dataset(harness.DEFAULT_GOLDEN)

    async def broken(_name: str) -> Never:
        raise ValueError("secret credential and raw model response")

    report = await run_timeline_dataset(dataset, broken)
    assert report.failed_count == len(dataset.cases)
    assert "secret" not in str(report)
    assert "ValueError" in report.case_results[0].assertions[0].message


def test_golden_schema_and_case_coverage_fail_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = json.loads(harness.DEFAULT_GOLDEN.read_text())
    data["cases"].append(data["cases"][0])
    with pytest.raises(ValidationError, match="unique"):
        TimelineDataset.model_validate(data)
    data["cases"] = []
    with pytest.raises(ValidationError):
        TimelineDataset.model_validate(data)
    data = json.loads(harness.DEFAULT_GOLDEN.read_text())
    data["cases"].pop()
    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(json.dumps(data))
    assert harness.main(["--golden", str(incomplete)]) == 2
    assert "lease-recovery" in capsys.readouterr().out


def test_timeline_cli_emits_machine_readable_report(capsys: pytest.CaptureFixture[str]) -> None:
    assert harness.main([]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["passed"]
    assert report["case_count"] == len(harness.SCENARIOS)
    assert report["failed_count"] == 0


def test_timeline_cli_returns_nonzero_on_behavior_mismatch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = json.loads(harness.DEFAULT_GOLDEN.read_text())
    data["cases"][0]["expected"]["facts"]["model_calls"] = 99
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(data))
    assert harness.main(["--golden", str(changed)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["failed_count"] == 1
    assert "expected 99, observed 2" in str(report)
