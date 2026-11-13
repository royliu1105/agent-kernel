"""Run credential-free golden timelines against actual runtime services."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from kernel_core import RiskLevel, RunEventType, RunStatus
from kernel_evals.reporting import eval_report_to_dict
from kernel_evals.timeline import (
    TimelineEvent,
    TimelineObservation,
    load_timeline_dataset,
    run_timeline_dataset,
)
from kernel_providers import (
    LLMFinishReason,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMToolChoice,
    LLMUsage,
    MessageRole,
)
from kernel_runtime import (
    ModelRouter,
    QueuedRunWorker,
    RetryPolicy,
    RunExecutionService,
    StuckRunRecoveryService,
)
from kernel_storage import (
    AgentRepository,
    ApprovalRepository,
    Base,
    RunRepository,
    ToolCallRepository,
    WorkerLeaseRepository,
    create_session_factory,
)
from kernel_tools import ToolExecutionContext, ToolMetadata, ToolRegistry
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

DEFAULT_GOLDEN = Path(__file__).resolve().parents[1] / "evals/timelines/runtime-v1.json"
SCENARIOS = frozenset(
    {
        "native-tool",
        "approval-approved",
        "approval-rejected",
        "model-retry",
        "model-fallback",
        "tool-retry",
        "lease-recovery",
    }
)
STABLE_PAYLOAD_FIELDS = frozenset(
    {
        "from_status",
        "to_status",
        "tool_name",
        "decision",
        "risk_level",
        "requires_approval",
        "attempt",
        "max_attempts",
        "error_type",
        "reason",
        "provider",
        "model",
        "model_ref",
        "from_model",
        "to_model",
        "attempt_count",
        "fallback_used",
    }
)


class _SimulatedProcessExit(BaseException):
    """Escape normal provider failure handling to leave a durable running run."""


class FixtureContractError(ValueError):
    """The real runtime sent an invalid request to a deterministic fixture."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FixtureContractError(message)


class _FixtureProvider:
    def __init__(
        self, name: str, *, failures: int = 0, native_tool: bool = False, crash: bool = False
    ) -> None:
        self.name = name
        self.failures = failures
        self.native_tool = native_tool
        self.crash = crash
        self.calls = 0
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        self.requests.append(request)
        self._validate_request(request)
        if self.crash:
            raise _SimulatedProcessExit()
        if self.calls <= self.failures:
            raise LLMProviderError("fixture transient failure", error_type="mock_transient")
        if self.native_tool and self.calls == 1:
            return LLMResponse(
                provider=self.name,
                model=request.model,
                text="",
                finish_reason=LLMFinishReason.TOOL_CALLS,
                tool_calls=(LLMToolCall(id="fixture-call-1", name="fixture_read", arguments={}),),
            )
        return LLMResponse(
            provider=self.name,
            model=request.model,
            text="fixture complete",
            usage=LLMUsage(input_tokens=5, output_tokens=2),
        )

    def _validate_request(self, request: LLMRequest) -> None:
        followup = self.native_tool and self.calls > 1
        expected_roles = (
            [MessageRole.USER, MessageRole.ASSISTANT, MessageRole.TOOL]
            if followup
            else [MessageRole.USER]
        )
        _require(
            [m.role for m in request.messages] == expected_roles, "message roles/order changed"
        )
        _require(request.messages[0].content == "timeline fixture", "task content changed")
        _require(request.model == "small", "routed model changed")
        if not followup:
            _require(request.tool_choice is LLMToolChoice.AUTO, "initial tool choice changed")
            _require(len(request.tools) == 1, "initial tool definitions missing")
            _require(request.tools[0].name == "fixture_read", "initial tool name changed")
            _require(
                request.tools[0].input_schema == {"type": "object", "additionalProperties": False},
                "initial tool schema changed",
            )
            return

        _require(self.calls == 2, "unexpected model call after tool result")
        _require(not request.tools, "follow-up must not expose more tools")
        _require(request.tool_choice is LLMToolChoice.NONE, "follow-up tool choice changed")
        assistant, result = request.messages[1:]
        _require(assistant.content == "", "assistant content changed")
        _require(
            assistant.metadata.get("tool_calls")
            == [LLMToolCall(id="fixture-call-1", name="fixture_read", arguments={}).model_dump()],
            "assistant call ID/name/arguments changed",
        )
        _require(result.name == "fixture_read", "tool result name changed")
        _require(
            result.metadata.get("provider_tool_call_id") == "fixture-call-1"
            and result.metadata.get("provider_name") == self.name,
            "tool result provider correlation changed",
        )
        payload = json.loads(result.content)
        _require(isinstance(payload, dict), "tool result is not an object")
        internal_id = result.metadata.get("tool_call_id")
        _require(isinstance(internal_id, str) and bool(internal_id), "internal call ID missing")
        _require(
            payload
            == {
                "tool_call_id": internal_id,
                "provider_tool_call_id": "fixture-call-1",
                "tool_name": "fixture_read",
                "result": {"ok": True},
            },
            "tool result content or correlation changed",
        )


class _FixtureTool:
    def __init__(self, *, write: bool = False, failures: int = 0) -> None:
        self.calls = 0
        self.failures = failures
        self.contexts: list[ToolExecutionContext] = []
        self.metadata = ToolMetadata(
            name="fixture_write" if write else "fixture_read",
            description="In-memory regression fixture; performs no external I/O.",
            input_schema={"type": "object", "additionalProperties": False},
            risk_level=RiskLevel.EXTERNAL_WRITE if write else RiskLevel.READ_ONLY,
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("fixture tool unavailable")
        return {"ok": True}

    async def execute_with_context(
        self, arguments: dict[str, Any], *, context: ToolExecutionContext
    ) -> dict[str, Any]:
        self.contexts.append(context)
        return await self.execute(arguments)


async def execute_scenario(name: str) -> TimelineObservation:
    if name not in SCENARIOS:
        raise ValueError(f"Unknown timeline fixture {name!r}.")
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        Base.metadata.create_all(engine)
        return await _execute(name, create_session_factory(engine))
    finally:
        engine.dispose()


async def _execute(name: str, factory: sessionmaker[Session]) -> TimelineObservation:
    approval_case = name.startswith("approval-")
    tool = _FixtureTool(write=approval_case, failures=int(name == "tool-retry"))
    registry = ToolRegistry()
    registry.register(tool)
    primary = _FixtureProvider(
        "fixture",
        failures=2 if name == "model-fallback" else int(name == "model-retry"),
        native_tool=name == "native-tool",
        crash=name == "lease-recovery",
    )
    backup = _FixtureProvider("backup")
    service = RunExecutionService(
        router=ModelRouter({"fixture": primary, "backup": backup}),
        tool_registry=registry,
        retry_policy=RetryPolicy(provider_max_attempts=2, tool_max_attempts=2),
    )
    payload: dict[str, Any] = {"task": "timeline fixture", "model": "fixture:small"}
    if name == "model-fallback":
        payload["fallback_models"] = ["backup:small"]
    if approval_case or name == "tool-retry":
        payload["tool"] = {"name": tool.metadata.name, "arguments": {}}
    with factory() as session:
        agent = AgentRepository(session).create(name="timeline-fixture")
        repository = RunRepository(session)
        run = repository.create(agent_id=agent.id, input_payload=payload)
        repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

    facts: dict[str, Any] = {}
    if name == "lease-recovery":
        facts.update(await _recover_crashed_run(factory, service, run.id))
    else:
        with factory() as session:
            initial = await service.execute(run_id=run.id, repository=RunRepository(session))
            if approval_case:
                facts["paused_status"] = initial.status.value
                facts["tool_calls_before_decision"] = tool.calls
        if approval_case:
            # Reopen sessions at each boundary to exercise persisted resume state.
            with factory() as session:
                approvals = ApprovalRepository(session)
                approval = approvals.list_for_run(run.id)[0]
                decide = approvals.approve if name == "approval-approved" else approvals.reject
                decide(approval_id=approval.id, decision_note="fixture decision")
            with factory() as session:
                await service.resume(
                    run_id=run.id,
                    repository=RunRepository(session),
                    approval_repository=ApprovalRepository(session),
                    tool_call_repository=ToolCallRepository(session),
                    approval_id=approval.id,
                )

    facts.update(
        model_calls=primary.calls + backup.calls,
        primary_calls=primary.calls,
        backup_calls=backup.calls,
        tool_executions=tool.calls,
    )
    with factory() as session:
        stored_tools = ToolCallRepository(session).list_for_run(run.id)
        if name == "native-tool":
            _require(len(primary.requests) == 2, "native model/tool/model request missing")
            last = primary.requests[-1]
            _require(len(last.messages) == 3, "native follow-up message missing")
            _require(len(stored_tools) == 1, "persisted native call missing")
            _require(
                last.messages[-1].metadata.get("tool_call_id") == str(stored_tools[0].id),
                "follow-up does not reference the persisted tool call",
            )
            _require(
                json.loads(last.messages[-1].content).get("result") == stored_tools[0].result,
                "follow-up differs from persisted tool result",
            )
        facts["stable_tool_call_key"] = (
            len(tool.contexts) == tool.calls
            and all(
                context.run_id == run.id
                and context.tool_call_id in {stored.id for stored in stored_tools}
                for context in tool.contexts
            )
            and len({context.tool_call_id for context in tool.contexts}) <= 1
        )
    return _observe(factory, run.id, facts)


async def _recover_crashed_run(
    factory: sessionmaker[Session], service: RunExecutionService, run_id: UUID
) -> dict[str, Any]:
    """Isolated P2 integration boundary: acquire, interrupt, recover, restart.

    Runtime acquires its own lease. Claim races and fencing require separate
    PostgreSQL tests; this golden tests persisted crash/recovery behavior.
    """
    with factory() as session:
        try:
            await service.execute(run_id=run_id, repository=RunRepository(session))
        except _SimulatedProcessExit:
            pass
        else:
            raise AssertionError("Crash fixture did not interrupt execution.")
    with factory() as session:
        leases = WorkerLeaseRepository(session)
        assert leases.get_active(run_id=run_id) is None
        assert [lease.run_id for lease in leases.list_expired()] == [run_id]
    recovery = StuckRunRecoveryService(session_factory=factory)
    first = recovery.recover_once()
    second = recovery.recover_once()
    worker = QueuedRunWorker(session_factory=factory, execution_service=service)
    restarted = await worker.run_once()
    with factory() as session:
        active = WorkerLeaseRepository(session).get_active(run_id=run_id)
    return {
        "recovered_count": first.recovered_count,
        "second_recovery_count": second.recovered_count,
        "restart_processed_count": restarted.processed_count,
        "active_lease": active is not None,
    }


def _observe(
    factory: sessionmaker[Session], run_id: UUID, facts: dict[str, Any]
) -> TimelineObservation:
    with factory() as session:
        repository = RunRepository(session)
        run = repository.get(run_id)
        assert run is not None
        events = repository.list_events(run_id)
        tools = ToolCallRepository(session).list_for_run(run_id)
        approvals = ApprovalRepository(session).list_for_run(run_id)
        facts.update(
            tool_statuses=[tool.status.value for tool in tools],
            approval_statuses=[approval.status.value for approval in approvals],
            contiguous_sequence=[event.sequence for event in events]
            == list(range(1, len(events) + 1)),
            trace_consistent=bool(run.trace_id)
            and all(event.trace_id == run.trace_id for event in events),
            tool_results=[tool.result for tool in tools],
            provider_tool_call_ids=[tool.provider_tool_call_id for tool in tools],
        )
        return TimelineObservation(
            status=run.status.value,
            error_type=run.error_type,
            events=tuple(
                TimelineEvent(
                    type=event.type.value,
                    payload={
                        key: value
                        for key, value in event.payload.items()
                        if key in STABLE_PAYLOAD_FIELDS
                    },
                )
                for event in events
            ),
            facts=facts,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    args = parser.parse_args(argv)
    try:
        dataset = load_timeline_dataset(args.golden)
        names = {case.name for case in dataset.cases}
        if names != SCENARIOS:
            raise ValueError(
                f"Golden must cover all fixtures; missing={sorted(SCENARIOS - names)}, "
                f"unknown={sorted(names - SCENARIOS)}."
            )
        report = asyncio.run(run_timeline_dataset(dataset, execute_scenario))
    except (OSError, ValidationError, ValueError) as error:
        print(json.dumps({"passed": False, "error": "invalid_golden", "detail": str(error)}))
        return 2
    print(json.dumps(eval_report_to_dict(report), indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
