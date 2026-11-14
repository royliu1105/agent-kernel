"""Runtime retry contracts through fixture providers, tools and PostgreSQL state."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Literal
from uuid import UUID

import pytest
from kernel_core import RiskLevel, Run, RunEvent, RunEventType, RunStatus, ToolCallStatus
from kernel_policy import PolicyDecisionType, ToolPolicy, ToolPolicyEvaluator
from kernel_providers import (
    LLMFinishReason,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMToolChoice,
    LLMUsage,
)
from kernel_runtime import ExecutionLimits, RetryDelayPolicy, RetryPolicy, RunExecutionService
from kernel_storage import (
    AgentRepository,
    ApprovalRepository,
    RunRepository,
    ToolCallRepository,
    WorkerLeaseRepository,
)
from kernel_storage.models import WorkerLeaseRecord
from kernel_tools import ToolError, ToolMetadata, ToolRegistry
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

Phase = Literal["initial", "followup"]
Trace = list[tuple[str, float]]


class ScriptedProvider:
    name = "backoff"

    def __init__(self, script: list[LLMResponse | LLMProviderError], trace: Trace) -> None:
        self.script = list(script)
        self.requests: list[LLMRequest] = []
        self.trace = trace

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        self.trace.append(("provider", len(self.requests)))
        assert self.script, "Unexpected extra provider send"
        outcome = self.script.pop(0)
        if isinstance(outcome, LLMProviderError):
            raise outcome
        return outcome


class ScriptedTool:
    def __init__(
        self,
        trace: Trace,
        *,
        name: str = "read",
        failures: int = 0,
        risk: RiskLevel = RiskLevel.READ_ONLY,
        retry_safe: bool | None = None,
        error_type: str = "tool_execution_failed",
    ) -> None:
        self.metadata = ToolMetadata(
            name=name,
            description="In-memory backoff fixture; no external effects.",
            input_schema={"type": "object", "additionalProperties": False},
            risk_level=risk,
            retry_safe=retry_safe,
        )
        self.trace = trace
        self.failures = failures
        self.error_type = error_type
        self.calls = 0

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        assert arguments == {}
        self.calls += 1
        self.trace.append((self.metadata.name, self.calls))
        if self.calls <= self.failures:
            raise ToolError("Synthetic tool failure.", error_type=self.error_type)
        return {"ok": True, "attempt": self.calls}


class RecordingSleep:
    def __init__(self, trace: Trace) -> None:
        self.trace = trace
        self.delays: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)
        self.trace.append(("sleep", seconds))


class SuspendedSleep(RecordingSleep):
    def __init__(self, trace: Trace) -> None:
        super().__init__(trace)
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def __call__(self, seconds: float) -> None:
        await super().__call__(seconds)
        self.started.set()
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise


def _reply(*tools: str) -> LLMResponse:
    return LLMResponse(
        provider="backoff",
        model="fixture",
        text="" if tools else "final fixture answer",
        finish_reason=LLMFinishReason.TOOL_CALLS if tools else LLMFinishReason.STOP,
        tool_calls=tuple(
            LLMToolCall(id=f"native-{index}", name=name, arguments={})
            for index, name in enumerate(tools)
        ),
        usage=LLMUsage(input_tokens=2, output_tokens=1),
    )


def _failure(hint: float | None = None, error_type: str = "rate_limit") -> LLMProviderError:
    return LLMProviderError(
        "Synthetic provider failure.", error_type=error_type, retry_after_seconds=hint
    )


def _script(
    phase: Phase, outcomes: list[LLMResponse | LLMProviderError], trace: Trace
) -> ScriptedProvider:
    prefix = [_reply("read", "read")] if phase == "followup" else []
    return ScriptedProvider([*prefix, *outcomes], trace)


def _registry(*tools: ScriptedTool) -> ToolRegistry:
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    return registry


def _service(
    provider: ScriptedProvider,
    tool: ScriptedTool,
    sleep: Callable[[float], Awaitable[None]],
    *,
    attempts: int = 3,
    limits: ExecutionLimits | None = None,
) -> RunExecutionService:
    return RunExecutionService(
        provider=provider,
        tool_registry=_registry(tool),
        retry_policy=RetryPolicy(provider_max_attempts=attempts, tool_max_attempts=attempts),
        retry_delay_policy=RetryDelayPolicy(base_seconds=0.25, max_seconds=1),
        retry_sleep=sleep,
        retry_random=lambda: 0.5,
        execution_limits=limits or ExecutionLimits(),
    )


def _queued(factory: sessionmaker[Session], *, fallback: bool = False) -> UUID:
    with factory() as session:
        agent = AgentRepository(session).create(name="runtime-backoff")
        runs = RunRepository(session)
        payload: dict[str, Any] = {"task": "read fixture data", "model": "backoff:fixture"}
        if fallback:
            payload["fallback_models"] = ["backoff:backup"]
        run = runs.create(agent_id=agent.id, input_payload=payload)
        runs.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        return run.id


async def _execute(
    factory: sessionmaker[Session], service: RunExecutionService, run_id: UUID
) -> Run:
    with factory() as session:
        return await service.execute(run_id=run_id, repository=RunRepository(session))


def _retry_events(factory: sessionmaker[Session], run_id: UUID) -> list[RunEvent]:
    with factory() as session:
        return [
            event
            for event in RunRepository(session).list_events(run_id)
            if event.type in {RunEventType.MODEL_CALL_RETRYING, RunEventType.TOOL_CALL_RETRYING}
        ]


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["initial", "followup"])
@pytest.mark.parametrize(
    ("hint", "expected"),
    [(None, [0.125, 0.25, 0.5, 0.5]), (0.75, [0.75] * 4), (1.0, [1.0] * 4)],
)
async def test_model_backoff_records_capped_jitter_and_respects_server_floor(
    postgres_session_factory: sessionmaker[Session],
    phase: Phase,
    hint: float | None,
    expected: list[float],
) -> None:
    trace: Trace = []
    sleep = RecordingSleep(trace)
    tool = ScriptedTool(trace)
    provider = _script(phase, [*[_failure(hint) for _ in range(4)], _reply()], trace)
    run_id = _queued(postgres_session_factory)
    result = await _execute(
        postgres_session_factory, _service(provider, tool, sleep, attempts=5), run_id
    )
    assert result.status is RunStatus.SUCCEEDED
    assert result.output is not None and result.output["text"] == "final fixture answer"
    assert sleep.delays == expected
    offset = int(phase == "followup")
    assert len(provider.requests) == 5 + offset
    assert tool.calls == 2 * offset
    expected_trace: Trace = [("provider", 1), ("read", 1), ("read", 2)] if offset else []
    for index in range(5):
        expected_trace.append(("provider", index + 1 + offset))
        if index < 4:
            expected_trace.append(("sleep", expected[index]))
    assert trace == expected_trace
    retried_requests = provider.requests[offset:]
    assert all(request == retried_requests[0] for request in retried_requests)
    assert all(request.tool_choice is LLMToolChoice.AUTO for request in provider.requests)
    assert all(request.tools for request in provider.requests)
    events = _retry_events(postgres_session_factory, run_id)
    assert [event.type for event in events] == [RunEventType.MODEL_CALL_RETRYING] * 4
    assert [event.payload["attempt"] for event in events] == [2, 3, 4, 5]
    assert [event.payload["delay_seconds"] for event in events] == expected
    assert all(event.payload["max_attempts"] == 5 for event in events)
    assert all(
        event.payload.get("phase") == ("tool_followup" if offset else None) for event in events
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["initial", "followup"])
@pytest.mark.parametrize(
    ("hint", "active_seconds", "error_type"),
    [(1.01, 300.0, "execution_retry_delay_limit"), (0.75, 0.5, "execution_active_time_limit")],
)
async def test_model_hint_refusal_sends_nothing_early_and_does_not_fallback(
    postgres_session_factory: sessionmaker[Session],
    phase: Phase,
    hint: float,
    active_seconds: float,
    error_type: str,
) -> None:
    trace: Trace = []
    sleep = RecordingSleep(trace)
    tool = ScriptedTool(trace)
    provider = _script(phase, [_failure(hint), _reply()], trace)
    run_id = _queued(postgres_session_factory, fallback=True)
    result = await _execute(
        postgres_session_factory,
        _service(provider, tool, sleep, limits=ExecutionLimits(max_active_seconds=active_seconds)),
        run_id,
    )
    assert result.status is RunStatus.FAILED
    assert result.error_type == error_type
    assert len(provider.requests) == 1 + int(phase == "followup")
    assert tool.calls == (2 if phase == "followup" else 0)
    assert sleep.delays == []
    assert _retry_events(postgres_session_factory, run_id) == []
    with postgres_session_factory() as session:
        assert not any(
            event.type is RunEventType.MODEL_FALLBACK_SELECTED
            for event in RunRepository(session).list_events(run_id)
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["initial", "followup"])
@pytest.mark.parametrize("attempts", [1, 3])
async def test_model_max_attempts_has_no_sleep_after_last_failure(
    postgres_session_factory: sessionmaker[Session], phase: Phase, attempts: int
) -> None:
    trace: Trace = []
    sleep = RecordingSleep(trace)
    tool = ScriptedTool(trace)
    provider = _script(phase, [*[_failure() for _ in range(attempts)], _reply()], trace)
    run_id = _queued(postgres_session_factory)
    result = await _execute(
        postgres_session_factory, _service(provider, tool, sleep, attempts=attempts), run_id
    )
    assert result.status is RunStatus.FAILED and result.error_type == "rate_limit"
    assert len(provider.requests) == attempts + int(phase == "followup")
    assert tool.calls == (2 if phase == "followup" else 0)
    assert sleep.delays == [0.125, 0.25][: attempts - 1]
    assert len(_retry_events(postgres_session_factory, run_id)) == attempts - 1
    assert trace[-1][0] == "provider"


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["initial", "followup"])
@pytest.mark.parametrize(
    "error_type", ["openai_quota_exhausted", "openai_status_error", "openai_invalid_response"]
)
async def test_permanent_model_failure_does_not_sleep_retry_or_fallback(
    postgres_session_factory: sessionmaker[Session], phase: Phase, error_type: str
) -> None:
    trace: Trace = []
    sleep = RecordingSleep(trace)
    tool = ScriptedTool(trace)
    provider = _script(phase, [_failure(0.5, error_type), _reply()], trace)
    run_id = _queued(postgres_session_factory, fallback=True)
    result = await _execute(postgres_session_factory, _service(provider, tool, sleep), run_id)
    assert result.status is RunStatus.FAILED and result.error_type == error_type
    assert len(provider.requests) == 1 + int(phase == "followup")
    assert tool.calls == (2 if phase == "followup" else 0)
    assert sleep.delays == []
    assert _retry_events(postgres_session_factory, run_id) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("retry_safe", [None, True])
@pytest.mark.parametrize("succeeds", [False, True])
async def test_safe_read_only_tool_backoff_uses_real_executor_and_attempt_limit(
    postgres_session_factory: sessionmaker[Session], retry_safe: bool | None, succeeds: bool
) -> None:
    trace: Trace = []
    sleep = RecordingSleep(trace)
    tool = ScriptedTool(trace, failures=2 if succeeds else 3, retry_safe=retry_safe)
    provider = ScriptedProvider([_reply("read"), _reply()], trace)
    run_id = _queued(postgres_session_factory)
    result = await _execute(postgres_session_factory, _service(provider, tool, sleep), run_id)
    assert result.status is (RunStatus.SUCCEEDED if succeeds else RunStatus.FAILED)
    assert result.error_type == (None if succeeds else "tool_execution_failed")
    assert tool.calls == 3
    assert len(provider.requests) == (2 if succeeds else 1)
    assert sleep.delays == [0.125, 0.25]
    assert trace[:6] == [
        ("provider", 1),
        ("read", 1),
        ("sleep", 0.125),
        ("read", 2),
        ("sleep", 0.25),
        ("read", 3),
    ]
    events = _retry_events(postgres_session_factory, run_id)
    assert [event.type for event in events] == [RunEventType.TOOL_CALL_RETRYING] * 2
    assert [event.payload["delay_seconds"] for event in events] == [0.125, 0.25]
    assert [event.payload["attempt"] for event in events] == [2, 3]
    with postgres_session_factory() as session:
        calls = ToolCallRepository(session).list_for_run(run_id)
    assert len(calls) == 1
    assert calls[0].status is (ToolCallStatus.SUCCEEDED if succeeds else ToolCallStatus.FAILED)
    assert all(event.payload["tool_call_id"] == str(calls[0].id) for event in events)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["not_retry_safe", "write", "permanent"])
async def test_ineligible_tool_failure_is_never_replayed(
    postgres_session_factory: sessionmaker[Session], kind: str
) -> None:
    trace: Trace = []
    sleep = RecordingSleep(trace)
    tool = ScriptedTool(
        trace,
        failures=1,
        risk=RiskLevel.EXTERNAL_WRITE if kind == "write" else RiskLevel.READ_ONLY,
        retry_safe=kind != "not_retry_safe",
        error_type="tool_validation_error" if kind == "permanent" else "tool_execution_failed",
    )
    provider = ScriptedProvider([_reply("read"), _reply()], trace)
    service = RunExecutionService(
        provider=provider,
        tool_registry=_registry(tool),
        policy_evaluator=ToolPolicyEvaluator(
            ToolPolicy(tool_decisions={"read": PolicyDecisionType.ALLOW})
        ),
        retry_policy=RetryPolicy(tool_max_attempts=3),
        retry_sleep=sleep,
        retry_random=lambda: 0.5,
        execution_limits=ExecutionLimits(),
    )
    run_id = _queued(postgres_session_factory)
    result = await _execute(postgres_session_factory, service, run_id)
    assert result.status is RunStatus.FAILED and result.error_type == tool.error_type
    assert tool.calls == 1
    assert len(provider.requests) == 1
    assert sleep.delays == []
    assert _retry_events(postgres_session_factory, run_id) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("risk", [RiskLevel.READ_ONLY, RiskLevel.EXTERNAL_WRITE])
async def test_approved_tool_failure_is_not_retried_even_when_marked_retry_safe(
    postgres_session_factory: sessionmaker[Session], risk: RiskLevel
) -> None:
    trace: Trace = []
    sleep = RecordingSleep(trace)
    tool = ScriptedTool(trace, failures=1, risk=risk, retry_safe=True)
    provider = ScriptedProvider([_reply("read"), _reply()], trace)
    service = RunExecutionService(
        provider=provider,
        tool_registry=_registry(tool),
        policy_evaluator=ToolPolicyEvaluator(
            ToolPolicy(tool_decisions={"read": PolicyDecisionType.REQUIRE_APPROVAL})
        ),
        retry_policy=RetryPolicy(tool_max_attempts=3),
        retry_sleep=sleep,
        retry_random=lambda: 0.5,
        execution_limits=ExecutionLimits(),
    )
    run_id = _queued(postgres_session_factory)
    waiting = await _execute(postgres_session_factory, service, run_id)
    assert waiting.status is RunStatus.WAITING_APPROVAL
    assert tool.calls == 0 and sleep.delays == []
    with postgres_session_factory() as session:
        approvals = ApprovalRepository(session)
        approval = approvals.list_for_run(run_id)[0]
        approvals.approve(approval_id=approval.id)
        result = await service.resume(
            run_id=run_id,
            repository=RunRepository(session),
            approval_repository=approvals,
            tool_call_repository=ToolCallRepository(session),
            approval_id=approval.id,
        )
        calls = ToolCallRepository(session).list_for_run(run_id)
    assert result.status is RunStatus.FAILED and result.error_type == "tool_execution_failed"
    assert tool.calls == 1 and len(provider.requests) == 1
    assert len(calls) == 1 and calls[0].status is ToolCallStatus.FAILED
    assert calls[0].requires_approval
    assert sleep.delays == []
    assert _retry_events(postgres_session_factory, run_id) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("boundary", ["initial", "followup", "tool"])
async def test_cancellation_during_backoff_has_no_late_send_or_tool_effect(
    postgres_session_factory: sessionmaker[Session], boundary: str
) -> None:
    trace: Trace = []
    sleep = SuspendedSleep(trace)
    read = ScriptedTool(trace, failures=int(boundary == "tool"))
    later = ScriptedTool(trace, name="later")
    scripts: dict[str, list[LLMResponse | LLMProviderError]] = {
        "initial": [_failure(), _reply("later"), _reply()],
        "followup": [_reply("read"), _failure(), _reply("later"), _reply()],
        "tool": [_reply("read", "later"), _reply()],
    }
    provider = ScriptedProvider(scripts[boundary], trace)
    service = RunExecutionService(
        provider=provider,
        tool_registry=_registry(read, later),
        retry_sleep=sleep,
        retry_random=lambda: 1,
        execution_limits=ExecutionLimits(),
    )
    run_id = _queued(postgres_session_factory)
    initial_tasks = asyncio.all_tasks()
    task = asyncio.create_task(_execute(postgres_session_factory, service, run_id))
    try:
        await asyncio.wait_for(sleep.started.wait(), timeout=5)
        assert len(provider.requests) == (2 if boundary == "followup" else 1)
        assert read.calls == int(boundary != "initial")
        assert later.calls == 0
        before_cancel = list(trace)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=5)
        sleep.release.set()
        assert sleep.cancelled.is_set()
        assert trace == before_cancel
        assert not (asyncio.all_tasks() - initial_tasks), "Leaked retry or heartbeat task"
        events = _retry_events(postgres_session_factory, run_id)
        assert len(events) == 1 and events[0].payload["delay_seconds"] == 0.25
        with postgres_session_factory() as session:
            run = RunRepository(session).get(run_id)
            assert run is not None and run.status is RunStatus.RUNNING and run.output is None
            assert WorkerLeaseRepository(session).get_active(run_id=run_id) is None
            calls = ToolCallRepository(session).list_for_run(run_id)
        if boundary == "initial":
            assert calls == []
        elif boundary == "followup":
            assert len(calls) == 1 and calls[0].status is ToolCallStatus.SUCCEEDED
        else:
            assert [call.status for call in calls] == [
                ToolCallStatus.RUNNING,
                ToolCallStatus.REQUESTED,
            ]
    finally:
        sleep.release.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_lease_heartbeat_continues_while_retry_sleep_exceeds_lease_ttl(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    trace: Trace = []
    provider = ScriptedProvider([_failure(), _reply()], trace)
    run_id = _queued(postgres_session_factory)
    observed_delays: list[float] = []

    async def real_sleep(seconds: float) -> None:
        observed_delays.append(seconds)
        assert len(provider.requests) == 1
        await asyncio.sleep(seconds)
        assert len(provider.requests) == 1
        with postgres_session_factory() as session:
            lease = WorkerLeaseRepository(session).get_active(run_id=run_id)
            assert lease is not None
            assert lease.heartbeat_at > lease.acquired_at

    service = RunExecutionService(
        provider=provider,
        tool_registry=ToolRegistry(),
        retry_delay_policy=RetryDelayPolicy(base_seconds=1.1, max_seconds=2),
        retry_sleep=real_sleep,
        retry_random=lambda: 1,
        lease_ttl_seconds=1,
        execution_limits=ExecutionLimits(max_active_seconds=10),
    )
    result = await asyncio.wait_for(_execute(postgres_session_factory, service, run_id), timeout=5)
    assert result.status is RunStatus.SUCCEEDED
    assert observed_delays == [1.1] and len(provider.requests) == 2
    with postgres_session_factory() as session:
        lease_record = session.scalar(
            select(WorkerLeaseRecord).where(WorkerLeaseRecord.run_id == str(run_id))
        )
        assert lease_record is not None and lease_record.released_at is not None
        assert lease_record.heartbeat_at > lease_record.acquired_at
