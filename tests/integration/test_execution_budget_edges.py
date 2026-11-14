"""Deadline, fallback cooldown, and returned-usage boundary regressions."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any
from uuid import UUID

import kernel_runtime.native_state as native_state
import pytest
from kernel_core import RiskLevel, Run, RunEventType, RunStatus
from kernel_providers import (
    LLMFinishReason,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMUsage,
)
from kernel_runtime import ExecutionLimits, RetryDelayPolicy, RetryPolicy, RunExecutionService
from kernel_storage import (
    AgentRepository,
    ExecutionOwnershipError,
    RunRepository,
    ToolCallRepository,
    WorkerLeaseRepository,
)
from kernel_storage.models import ModelUsageRecord, RunRecord, WorkerLeaseRecord
from kernel_tools import ToolMetadata, ToolRegistry
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker


def _queued(factory: sessionmaker[Session], *, fallback: bool = False) -> UUID:
    with factory() as session:
        agent = AgentRepository(session).create(name="budget-edge")
        repository = RunRepository(session)
        payload: dict[str, Any] = {"task": "budget edge fixture", "model": "budget:primary"}
        if fallback:
            payload["fallback_models"] = ["budget:backup"]
        run = repository.create(agent_id=agent.id, input_payload=payload)
        repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={},
        )
        return run.id


async def _execute(
    factory: sessionmaker[Session], service: RunExecutionService, run_id: UUID
) -> Run:
    with factory() as session:
        return await service.execute(run_id=run_id, repository=RunRepository(session))


class CountingTool:
    metadata = ToolMetadata(
        name="edge_tool",
        description="In-memory counter only.",
        input_schema={"type": "object", "additionalProperties": False},
        risk_level=RiskLevel.READ_ONLY,
    )

    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        assert arguments == {}
        self.calls += 1
        return {"calls": self.calls}


def _stored_snapshot(factory: sessionmaker[Session], run_id: UUID) -> dict[str, Any]:
    with factory() as session:
        record = session.get(RunRecord, str(run_id))
        run = RunRepository(session).get(run_id)
        assert record is not None and run is not None
        return {
            "run": run.model_dump(mode="json"),
            "checkpoint": deepcopy(record.execution_checkpoint),
            "events": [
                event.model_dump(mode="json")
                for event in RunRepository(session).list_events(run_id)
            ],
            "tools": [
                call.model_dump(mode="json")
                for call in ToolCallRepository(session).list_for_run(run_id)
            ],
            "usage": [
                dict(row)
                for row in session.execute(
                    select(ModelUsageRecord.__table__)
                    .where(ModelUsageRecord.run_id == str(run_id))
                    .order_by(ModelUsageRecord.id)
                ).mappings()
            ],
            "leases": [
                dict(row)
                for row in session.execute(
                    select(WorkerLeaseRecord.__table__)
                    .where(WorkerLeaseRecord.run_id == str(run_id))
                    .order_by(WorkerLeaseRecord.id)
                ).mappings()
            ],
        }


class CancellationResistantProvider:
    name = "budget"

    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.cancelled = asyncio.Event()
        self.release = asyncio.Event()
        self.returned = asyncio.Event()
        self.task: asyncio.Task[Any] | None = None
        self.calls = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.task = asyncio.current_task()
        self.calls += 1
        self.entered.set()
        while not self.release.is_set():
            try:
                await self.release.wait()
            except asyncio.CancelledError:
                self.cancelled.set()
        self.returned.set()
        return LLMResponse(
            provider=self.name,
            model=request.model,
            text="late private provider response",
            usage=LLMUsage(input_tokens=11, output_tokens=7, estimated_cost=0.25),
            finish_reason=LLMFinishReason.TOOL_CALLS,
            tool_calls=(LLMToolCall(id="late-call", name="edge_tool", arguments={}),),
        )


@pytest.mark.asyncio
async def test_active_deadline_fences_run_without_waiting_for_cancellation_resistant_provider(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    provider = CancellationResistantProvider()
    tool = CountingTool()
    registry = ToolRegistry()
    registry.register(tool)
    run_id = _queued(postgres_session_factory)
    service = RunExecutionService(
        provider=provider,
        tool_registry=registry,
        execution_limits=ExecutionLimits(max_active_seconds=0.1),
        lease_ttl_seconds=1,
    )
    initial_tasks = asyncio.all_tasks()
    execution = asyncio.create_task(_execute(postgres_session_factory, service, run_id))
    try:
        await asyncio.wait_for(provider.entered.wait(), timeout=3)
        await asyncio.wait_for(provider.cancelled.wait(), timeout=3)
        # Do not cancel execution on this deadline: that would conceal the regression.
        done, _ = await asyncio.wait({execution}, timeout=1)
        assert execution in done, "The active deadline waited for an uncooperative provider"
        result = execution.result()
        assert result.status is RunStatus.FAILED
        assert result.error_type == "execution_active_time_limit"
        assert result.output is None
        assert result.input_tokens_total == result.output_tokens_total == 0
        assert result.estimated_cost_total == 0
        assert not provider.returned.is_set()
        assert provider.task is not None and not provider.task.done()

        with postgres_session_factory() as session:
            assert WorkerLeaseRepository(session).get_active(run_id=run_id) is None
            lease = session.scalars(
                select(WorkerLeaseRecord).where(WorkerLeaseRecord.run_id == str(run_id))
            ).one()
            stale = RunRepository(session, lease_token=lease.lease_token)
            with pytest.raises(ExecutionOwnershipError):
                stale.save_execution_checkpoint(run_id, {"late": True})
            session.rollback()
        before = _stored_snapshot(postgres_session_factory, run_id)
        assert before["tools"] == before["usage"] == []
        assert before["checkpoint"] is not None
        assert before["checkpoint"]["response"] is None

        provider.release.set()
        late = await asyncio.wait_for(asyncio.shield(provider.task), timeout=3)
        assert late.text == "late private provider response"
        await asyncio.sleep(0)
        assert _stored_snapshot(postgres_session_factory, run_id) == before
        assert provider.calls == 1 and tool.calls == 0
        assert not (asyncio.all_tasks() - initial_tasks), "Leaked runtime/heartbeat task"
    finally:
        # Even the regressed wait_for implementation must leave no blocked fixture behind.
        provider.release.set()
        tasks = {execution}
        if provider.task is not None:
            tasks.add(provider.task)
        done, pending = await asyncio.wait(tasks, timeout=3)
        for task in pending:
            task.cancel()
        if pending:
            finished, pending = await asyncio.wait(pending, timeout=1)
            done.update(finished)
        await asyncio.gather(*done, return_exceptions=True)
        assert not pending, "Budget-edge fixture could not finish cleanup"


@pytest.mark.asyncio
@pytest.mark.parametrize("attempts", [1, 2])
@pytest.mark.parametrize("hint", [0.75, 1.0, 1.01, 60.0])
async def test_same_provider_fallback_obeys_final_attempt_retry_after(
    postgres_session_factory: sessionmaker[Session], attempts: int, hint: float
) -> None:
    trace: list[tuple[str, str | float]] = []
    primary_calls = 0

    class HintProvider:
        name = "budget"

        async def complete(self, request: LLMRequest) -> LLMResponse:
            nonlocal primary_calls
            trace.append(("call", request.model))
            if request.model == "primary":
                primary_calls += 1
                assert primary_calls <= attempts, "Unexpected additional primary attempt"
                raise LLMProviderError(
                    "Synthetic rate limit.",
                    error_type="rate_limit",
                    retry_after_seconds=hint if primary_calls == attempts else None,
                )
            assert request.model == "backup"
            return LLMResponse(provider=self.name, model=request.model, text="fallback answer")

    async def sleep(seconds: float) -> None:
        trace.append(("sleep_start", seconds))
        await asyncio.sleep(0)
        trace.append(("sleep_end", seconds))

    run_id = _queued(postgres_session_factory, fallback=True)
    result = await _execute(
        postgres_session_factory,
        RunExecutionService(
            provider=HintProvider(),
            retry_policy=RetryPolicy(provider_max_attempts=attempts),
            retry_delay_policy=RetryDelayPolicy(base_seconds=0.25, max_seconds=1),
            retry_sleep=sleep,
            retry_random=lambda: 0.5,
        ),
        run_id,
    )
    expected: list[tuple[str, str | float]] = []
    for attempt in range(attempts):
        expected.append(("call", "primary"))
        if attempt + 1 < attempts:
            expected.extend([("sleep_start", 0.125), ("sleep_end", 0.125)])
    with postgres_session_factory() as session:
        fallback_events = [
            event
            for event in RunRepository(session).list_events(run_id)
            if event.type is RunEventType.MODEL_FALLBACK_SELECTED
        ]
    if hint > 1:
        assert result.status is RunStatus.FAILED
        assert result.error_type == "execution_retry_delay_limit"
        assert result.output is None
        assert fallback_events == []
    else:
        expected.extend([("sleep_start", hint), ("sleep_end", hint), ("call", "backup")])
        assert result.status is RunStatus.SUCCEEDED
        assert result.output is not None and result.output["text"] == "fallback answer"
        assert len(fallback_events) == 1
        assert fallback_events[0].payload["delay_seconds"] == pytest.approx(hint)
        assert fallback_events[0].payload["from_model"] == "budget:primary"
        assert fallback_events[0].payload["to_model"] == "budget:backup"
    assert trace == expected
    assert primary_calls == attempts


@pytest.mark.asyncio
@pytest.mark.parametrize("native", [False, True], ids=["terminal-answer", "native-tool-response"])
async def test_normally_returned_usage_is_saved_before_active_time_failure(
    postgres_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch, native: bool
) -> None:
    clock = [0.0]
    monkeypatch.setattr(native_state, "monotonic", lambda: clock[0])
    requests: list[LLMRequest] = []

    class ReturnedUsageProvider:
        name = "budget"

        async def complete(self, request: LLMRequest) -> LLMResponse:
            requests.append(request)
            # A normal completed response crosses the observed active-time boundary.
            clock[0] = 2.0
            return LLMResponse(
                provider=self.name,
                model=request.model,
                text="normal completed response",
                usage=LLMUsage(input_tokens=11, output_tokens=7, estimated_cost=0.25),
                finish_reason=LLMFinishReason.TOOL_CALLS if native else LLMFinishReason.STOP,
                tool_calls=(LLMToolCall(id="normal-call", name="edge_tool", arguments={}),)
                if native
                else (),
            )

    tool = CountingTool()
    registry = ToolRegistry()
    registry.register(tool)
    run_id = _queued(postgres_session_factory)
    result = await _execute(
        postgres_session_factory,
        RunExecutionService(
            provider=ReturnedUsageProvider(),
            tool_registry=registry,
            execution_limits=ExecutionLimits(max_active_seconds=1),
        ),
        run_id,
    )
    assert result.status is RunStatus.FAILED
    assert result.error_type == "execution_active_time_limit"
    assert result.output is None
    assert len(requests) == 1 and tool.calls == 0
    with postgres_session_factory() as session:
        persisted = RunRepository(session).get(run_id)
        assert persisted is not None
        assert persisted.input_tokens_total == result.input_tokens_total == 11
        assert persisted.output_tokens_total == result.output_tokens_total == 7
        assert persisted.estimated_cost_total == result.estimated_cost_total == pytest.approx(0.25)
        usage = session.scalars(
            select(ModelUsageRecord).where(ModelUsageRecord.run_id == str(run_id))
        ).one()
        assert (usage.provider, usage.model) == ("budget", "primary")
        assert (usage.input_tokens, usage.output_tokens) == (11, 7)
        assert usage.estimated_cost == pytest.approx(0.25)
        assert ToolCallRepository(session).list_for_run(run_id) == []
        assert WorkerLeaseRepository(session).get_active(run_id=run_id) is None
        events = RunRepository(session).list_events(run_id)
        assert [event.type for event in events].count(RunEventType.RUN_FAILED) == 1
        assert not any(event.type is RunEventType.RUN_COMPLETED for event in events)
