from pathlib import Path
from uuid import uuid4

import pytest
from kernel_core import Run
from kernel_providers import LLMRequest
from kernel_runtime import ExecutionLimits
from kernel_runtime.native_state import ExecutionBudget, ExecutionLimitError, NativeState
from pydantic import ValidationError


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("max_model_calls", "0"),
        ("max_model_calls", "257"),
        ("max_tool_calls", "-1"),
        ("max_tool_calls", "1025"),
        ("max_active_seconds", "nan"),
        ("max_active_seconds", "inf"),
        ("max_active_seconds", "0"),
        ("max_history_bytes", "63"),
        ("max_total_tokens", "0"),
        ("max_output_tokens", "0"),
        ("max_estimated_cost", "-1"),
        ("max_estimated_cost", "inf"),
        ("max_model_calls", "1.5"),
        ("max_tool_calls", "true"),
    ],
)
def test_invalid_environment_bounds_fail_validation(name: str, value: str) -> None:
    with pytest.raises((ValueError, ValidationError)):
        ExecutionLimits.from_env({f"AGENT_KERNEL_{name.upper()}": value})


def test_all_environment_bounds_are_parsed_and_declared_for_both_executors() -> None:
    limits = ExecutionLimits.from_env(
        {
            "AGENT_KERNEL_MAX_MODEL_CALLS": "3",
            "AGENT_KERNEL_MAX_TOOL_CALLS": "0",
            "AGENT_KERNEL_MAX_ACTIVE_SECONDS": "12.5",
            "AGENT_KERNEL_MAX_HISTORY_BYTES": "8192",
            "AGENT_KERNEL_MAX_TOTAL_TOKENS": "100",
            "AGENT_KERNEL_MAX_OUTPUT_TOKENS": "25",
            "AGENT_KERNEL_MAX_ESTIMATED_COST": "0.25",
        }
    )
    assert limits == ExecutionLimits(
        max_model_calls=3,
        max_tool_calls=0,
        max_active_seconds=12.5,
        max_history_bytes=8192,
        max_total_tokens=100,
        max_output_tokens=25,
        max_estimated_cost=0.25,
    )
    assert ExecutionLimits.from_env({"AGENT_KERNEL_MAX_ESTIMATED_COST": ""}) == ExecutionLimits()
    root = Path(__file__).resolve().parents[2]
    compose = (root / "docker-compose.yml").read_text()
    example = (root / ".env.example").read_text()
    reference = (root / "docs/configuration.md").read_text()
    for field in ExecutionLimits.model_fields:
        variable = f"AGENT_KERNEL_{field.upper()}"
        assert compose.count(f"\n      {variable}:") == 2
        assert f"{variable}=" in example
        assert f"`{variable}`" in reference


def test_restored_bounds_cannot_be_increased() -> None:
    saved = ExecutionLimits(max_model_calls=2, max_estimated_cost=0.1)
    current = ExecutionLimits(max_model_calls=100, max_tool_calls=1, max_estimated_cost=0.9)
    tightened = saved.tightened(current)
    assert tightened.max_model_calls == 2
    assert tightened.max_tool_calls == 1
    assert tightened.max_estimated_cost == 0.1
    assert saved.tightened(ExecutionLimits()).max_estimated_cost == 0.1
    assert ExecutionLimits().tightened(saved).max_estimated_cost == 0.1


def test_active_time_survives_restore_but_human_wait_is_excluded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kernel_runtime.native_state as module

    clock = [100.0]
    monkeypatch.setattr(module, "monotonic", lambda: clock[0])
    run = Run(agent_id=uuid4(), input={})
    state = NativeState(
        run_id=run.id,
        limits=ExecutionLimits(max_active_seconds=5),
        request=LLMRequest(model="small", messages=()),
        model_ref="mock:small",
    )
    before = ExecutionBudget(state)
    clock[0] += 3
    before.tick()
    payload = state.serialized()
    clock[0] += 86400
    resumed = ExecutionBudget(NativeState.model_validate(payload))
    assert resumed.remaining_seconds() == 2
    clock[0] += 2
    with pytest.raises(ExecutionLimitError, match="active time"):
        resumed.check(run)
