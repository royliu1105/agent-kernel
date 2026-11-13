from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from kernel_core import RiskLevel, RunEventType, RunStatus, ToolCallStatus
from kernel_providers import LLMFinishReason, LLMRequest, LLMResponse, LLMToolCall, LLMUsage
from kernel_runtime import ExecutionLimits, ModelRouter, RunExecutionService
from kernel_runtime.execution import RunAlreadyClaimedError, RunExecutionError
from kernel_storage import AgentRepository, ApprovalRepository, RunRepository, ToolCallRepository
from kernel_storage.base import Base
from kernel_storage.models import RunRecord
from kernel_tools import ToolMetadata, ToolRegistry
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(params=["sqlite", "postgres"])
def continuation_db(
    request: pytest.FixtureRequest, tmp_path: Any
) -> Iterator[sessionmaker[Session]]:
    if request.param == "sqlite":
        engine = create_engine(f"sqlite:///{tmp_path / 'continuation.db'}")
        Base.metadata.create_all(engine)
        try:
            yield sessionmaker(engine, expire_on_commit=False)
        finally:
            engine.dispose()
        return
    url = os.getenv("AGENT_KERNEL_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set AGENT_KERNEL_TEST_POSTGRES_URL for native continuation contracts.")
    schema = f"test_continuation_{uuid4().hex}"
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(make_url(url).update_query_dict({"options": f"-csearch_path={schema}"}))
    try:
        Base.metadata.create_all(engine)
        yield sessionmaker(engine, expire_on_commit=False)
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


class ScriptedProvider:
    name = "scripted"

    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = list(responses)
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        assert self.responses, "Unexpected extra provider call"
        return self.responses.pop(0)


class CountingTool:
    def __init__(self, name: str, *, write: bool = False) -> None:
        self.calls: list[dict[str, Any]] = []
        self.metadata = ToolMetadata(
            name=name,
            description="Counting fixture; no external effects.",
            input_schema={"type": "object", "properties": {"value": {"type": "string"}}},
            risk_level=RiskLevel.EXTERNAL_WRITE if write else RiskLevel.READ_ONLY,
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(arguments)
        return {"value": arguments.get("value", ""), "call_number": len(self.calls)}


def reply(*calls: LLMToolCall, text: str = "") -> LLMResponse:
    return LLMResponse(
        provider="scripted",
        model="small",
        text=text,
        tool_calls=calls,
        finish_reason=LLMFinishReason.TOOL_CALLS if calls else LLMFinishReason.STOP,
        usage=LLMUsage(input_tokens=2, output_tokens=1, estimated_cost=0.01),
    )


def call(identity: str, name: str = "read", value: str = "") -> LLMToolCall:
    return LLMToolCall(id=identity, name=name, arguments={"value": value})


def queued(session: Session, *, payload: dict[str, Any] | None = None) -> UUID:
    agent = AgentRepository(session).create(name="bounded-loop")
    repository = RunRepository(session)
    run = repository.create(
        agent_id=agent.id,
        input_payload=payload or {"task": "retain original task", "model": "scripted:small"},
    )
    repository.apply_transition(
        run_id=run.id,
        status=RunStatus.QUEUED,
        event_type=RunEventType.RUN_QUEUED,
        payload={"from_status": "created", "to_status": "queued"},
    )
    return run.id


@pytest.mark.asyncio
async def test_multiple_rounds_and_ordered_batch_reach_real_final_answer(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    tool = CountingTool("read")
    registry = ToolRegistry()
    registry.register(tool)
    provider = ScriptedProvider(
        [
            reply(call("one", value="first")),
            reply(call("two", value="second"), call("three", value="third")),
            reply(text="final answer after all three results"),
        ]
    )
    with sqlite_session_factory() as session:
        run_id = queued(session)
        result = await RunExecutionService(provider=provider, tool_registry=registry).execute(
            run_id=run_id, repository=RunRepository(session)
        )
        stored = ToolCallRepository(session).list_for_run(run_id)
    assert result.status is RunStatus.SUCCEEDED
    assert result.output is not None
    assert result.output["text"] == "final answer after all three results"
    assert len(provider.requests) == 3
    assert tool.calls == [{"value": value} for value in ["first", "second", "third"]]
    assert [item.provider_tool_call_id for item in stored] == ["one", "two", "three"]
    assert all(item.status is ToolCallStatus.SUCCEEDED for item in stored)
    assert provider.requests[-1].messages[0].content == "retain original task"
    outputs = [m for m in provider.requests[-1].messages if m.role.value == "tool"]
    assert [m.metadata["provider_tool_call_id"] for m in outputs] == ["one", "two", "three"]
    assert [json.loads(m.content)["result"]["value"] for m in outputs] == [
        "first",
        "second",
        "third",
    ]
    assert result.input_tokens_total == 6
    assert result.output_tokens_total == 3
    assert result.estimated_cost_total == pytest.approx(0.03)


@pytest.mark.asyncio
async def test_two_approval_rounds_resume_with_new_executor_and_no_replayed_tools(
    continuation_db: sessionmaker[Session],
) -> None:
    read, write = CountingTool("read"), CountingTool("write", write=True)
    registry = ToolRegistry()
    registry.register(read)
    registry.register(write)
    initial = ScriptedProvider([reply(call("r1"), call("w1", "write"), call("r2"))])
    with continuation_db() as session:
        run_id = queued(session)
        waiting = await RunExecutionService(provider=initial, tool_registry=registry).execute(
            run_id=run_id, repository=RunRepository(session)
        )
    assert waiting.status is RunStatus.WAITING_APPROVAL
    assert len(read.calls) == 1
    assert write.calls == []

    for response, expected_status in [
        (reply(call("w2", "write")), RunStatus.WAITING_APPROVAL),
        (reply(text="approved final answer"), RunStatus.SUCCEEDED),
    ]:
        resumed_provider = ScriptedProvider([response])
        with continuation_db() as session:
            approvals = ApprovalRepository(session)
            approval = approvals.list_for_run(run_id)[-1]
            approvals.approve(approval_id=approval.id)
            result = await RunExecutionService(
                provider=resumed_provider, tool_registry=registry
            ).resume(
                run_id=run_id,
                repository=RunRepository(session),
                approval_repository=approvals,
                tool_call_repository=ToolCallRepository(session),
                approval_id=approval.id,
            )
        assert result.status is expected_status
        assert resumed_provider.requests[0].messages[0].content == "retain original task"
    assert len(read.calls) == 2
    assert len(write.calls) == 2
    assert result.output is not None and result.output["text"] == "approved final answer"
    assert result.input_tokens_total == 6
    assert result.estimated_cost_total == pytest.approx(0.03)


@pytest.mark.asyncio
async def test_duplicate_native_ids_are_rejected_before_any_batch_side_effect(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    tool = CountingTool("read")
    registry = ToolRegistry()
    registry.register(tool)
    provider = ScriptedProvider([reply(call("duplicate"), call("duplicate"))])
    with sqlite_session_factory() as session:
        result = await RunExecutionService(provider=provider, tool_registry=registry).execute(
            run_id=queued(session), repository=RunRepository(session)
        )
    assert result.status is RunStatus.FAILED
    assert result.error_type == "invalid_native_tool_calls"
    assert tool.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limits", "responses", "error_type", "model_count", "tool_count"),
    [
        (
            ExecutionLimits(max_model_calls=2),
            [reply(call("a")), reply(call("b"))],
            "execution_model_calls_limit",
            2,
            1,
        ),
        (
            ExecutionLimits(max_tool_calls=1),
            [reply(call("a"), call("b"))],
            "execution_tool_calls_limit",
            1,
            0,
        ),
        (
            ExecutionLimits(max_tool_calls=1),
            [reply(call("a")), reply(call("b"))],
            "execution_tool_calls_limit",
            2,
            1,
        ),
        (ExecutionLimits(max_total_tokens=3), [reply(call("a"))], "execution_tokens_limit", 1, 0),
        (
            ExecutionLimits(max_estimated_cost=0.01),
            [reply(call("a"))],
            "execution_estimated_cost_limit",
            1,
            0,
        ),
        (
            ExecutionLimits(max_history_bytes=64),
            [reply(call("a"))],
            "execution_history_bytes_limit",
            0,
            0,
        ),
        (
            ExecutionLimits(),
            [reply(call("a")), reply(call("a"))],
            "invalid_native_tool_calls",
            2,
            1,
        ),
        (ExecutionLimits(), [reply(call(" "))], "invalid_native_tool_calls", 1, 0),
        (ExecutionLimits(), [reply(call("a", name=" "))], "invalid_native_tool_calls", 1, 0),
        (
            ExecutionLimits(),
            [reply().model_copy(update={"finish_reason": LLMFinishReason.LENGTH})],
            "model_incomplete_response",
            1,
            0,
        ),
    ],
)
async def test_budgets_and_invalid_responses_stop_before_more_effects(
    sqlite_session_factory: sessionmaker[Session],
    limits: ExecutionLimits,
    responses: list[LLMResponse],
    error_type: str,
    model_count: int,
    tool_count: int,
) -> None:
    provider = ScriptedProvider(responses)
    tool = CountingTool("read")
    registry = ToolRegistry()
    registry.register(tool)
    with sqlite_session_factory() as session:
        run_id = queued(
            session,
            payload={
                "task": "retain original task",
                "model": "scripted:small",
                "max_model_calls": 1000,
                "max_tool_calls": 1000,
                "execution_limits": {"max_total_tokens": 999999},
            },
        )
        result = await RunExecutionService(
            provider=provider,
            tool_registry=registry,
            execution_limits=limits,
        ).execute(run_id=run_id, repository=RunRepository(session))
    assert result.status is RunStatus.FAILED
    assert result.error_type == error_type
    assert len(provider.requests) == model_count
    assert len(tool.calls) == tool_count
    assert all(
        request.max_output_tokens is not None
        and request.max_output_tokens <= limits.max_output_tokens
        for request in provider.requests
    )


@pytest.mark.asyncio
async def test_terminal_answer_at_exact_token_budget_and_output_cap(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    provider = ScriptedProvider([reply(text="done")])
    with sqlite_session_factory() as session:
        result = await RunExecutionService(
            provider=provider,
            execution_limits=ExecutionLimits(max_total_tokens=3),
        ).execute(run_id=queued(session), repository=RunRepository(session))
    assert result.status is RunStatus.SUCCEEDED
    assert provider.requests[0].max_output_tokens == 3


@pytest.mark.asyncio
async def test_route_alias_preserves_canonical_provider_identity_through_resume(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    write = CountingTool("write", write=True)
    registry = ToolRegistry()
    registry.register(write)
    provider = ScriptedProvider([reply(call("w", "write")), reply(text="done")])
    service = RunExecutionService(
        router=ModelRouter({"configured-alias": provider}),
        tool_registry=registry,
    )
    with sqlite_session_factory() as session:
        run_id = queued(
            session, payload={"task": "alias fixture", "model": "configured-alias:small"}
        )
        result = await service.execute(run_id=run_id, repository=RunRepository(session))
        assert result.status is RunStatus.WAITING_APPROVAL
        approvals = ApprovalRepository(session)
        approval = approvals.list_for_run(run_id)[0]
        approvals.approve(approval_id=approval.id)
        result = await service.resume(
            run_id=run_id,
            repository=RunRepository(session),
            approval_id=approval.id,
            approval_repository=approvals,
            tool_call_repository=ToolCallRepository(session),
        )
        assert result.status is RunStatus.SUCCEEDED
        assert all(
            t.provider_name == "scripted" for t in ToolCallRepository(session).list_for_run(run_id)
        )
    assert len(write.calls) == 1
    assert len(provider.requests) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("current_limit", [1, 100])
async def test_approval_cannot_reset_or_increase_original_tool_budget(
    continuation_db: sessionmaker[Session],
    current_limit: int,
) -> None:
    read, write = CountingTool("read"), CountingTool("write", write=True)
    registry = ToolRegistry()
    registry.register(read)
    registry.register(write)
    with continuation_db() as session:
        run_id = queued(session)
        waiting = await RunExecutionService(
            provider=ScriptedProvider([reply(call("r1"), call("w1", "write"))]),
            tool_registry=registry,
            execution_limits=ExecutionLimits(max_tool_calls=2),
        ).execute(run_id=run_id, repository=RunRepository(session))
    assert waiting.status is RunStatus.WAITING_APPROVAL
    provider = ScriptedProvider([reply(call("r2"))])
    with continuation_db() as session:
        approvals = ApprovalRepository(session)
        approval = approvals.list_for_run(run_id)[0]
        approvals.approve(approval_id=approval.id)
        result = await RunExecutionService(
            provider=provider,
            tool_registry=registry,
            execution_limits=ExecutionLimits(max_tool_calls=current_limit),
        ).resume(
            run_id=run_id,
            repository=RunRepository(session),
            approval_id=approval.id,
            approval_repository=approvals,
            tool_call_repository=ToolCallRepository(session),
        )
    assert result.status is RunStatus.FAILED
    assert result.error_type == "execution_tool_calls_limit"
    assert len(read.calls) == 1
    assert len(write.calls) == (0 if current_limit == 1 else 1)
    assert len(provider.requests) == (0 if current_limit == 1 else 1)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["reject", "missing", "invalid", "changed_tool", "changed_args"])
async def test_unusable_approval_state_never_runs_a_tool_or_model(
    continuation_db: sessionmaker[Session],
    case: str,
) -> None:
    write = CountingTool("write", write=True)
    registry = ToolRegistry()
    registry.register(write)
    with continuation_db() as session:
        run_id = queued(session)
        waiting = await RunExecutionService(
            provider=ScriptedProvider([reply(call("w1", "write"))]),
            tool_registry=registry,
        ).execute(run_id=run_id, repository=RunRepository(session))
    assert waiting.status is RunStatus.WAITING_APPROVAL
    provider = ScriptedProvider([])
    with continuation_db() as session:
        approvals = ApprovalRepository(session)
        approval = approvals.list_for_run(run_id)[0]
        if case == "reject":
            approvals.reject(approval_id=approval.id, decision_note="not authorized")
        else:
            approvals.approve(approval_id=approval.id)
        record = session.get(RunRecord, str(run_id))
        assert record is not None
        if case == "missing":
            record.execution_checkpoint = None
        elif case == "invalid":
            record.execution_checkpoint = {"version": 999}
        elif case == "changed_args":
            checkpoint = json.loads(json.dumps(record.execution_checkpoint))
            checkpoint["response"]["tool_calls"][0]["arguments"] = {"value": "tampered"}
            record.execution_checkpoint = checkpoint
        elif case == "changed_tool":
            write.metadata = write.metadata.model_copy(update={"description": "changed contract"})
        session.commit()
        result = await RunExecutionService(provider=provider, tool_registry=registry).resume(
            run_id=run_id,
            repository=RunRepository(session),
            approval_id=approval.id,
            approval_repository=approvals,
            tool_call_repository=ToolCallRepository(session),
        )
    assert result.status is RunStatus.FAILED
    expected = {
        "missing": "missing_execution_checkpoint",
        "invalid": "invalid_execution_checkpoint",
        "changed_args": "invalid_execution_checkpoint",
        "changed_tool": "continuation_config_changed",
        "reject": "approval_rejected",
    }
    assert result.error_type == expected[case]
    assert write.calls == []
    assert provider.requests == []


@pytest.mark.asyncio
async def test_old_approval_cannot_resume_new_pending_call(
    continuation_db: sessionmaker[Session],
) -> None:
    write = CountingTool("write", write=True)
    registry = ToolRegistry()
    registry.register(write)
    provider = ScriptedProvider([reply(call("w1", "write")), reply(call("w2", "write"))])
    service = RunExecutionService(provider=provider, tool_registry=registry)
    with continuation_db() as session:
        run_id = queued(session)
        await service.execute(run_id=run_id, repository=RunRepository(session))
        approvals = ApprovalRepository(session)
        first = approvals.list_for_run(run_id)[0]
        approvals.approve(approval_id=first.id)
        result = await service.resume(
            run_id=run_id,
            repository=RunRepository(session),
            approval_id=first.id,
            approval_repository=approvals,
            tool_call_repository=ToolCallRepository(session),
        )
        assert result.status is RunStatus.WAITING_APPROVAL
        with pytest.raises(RunExecutionError, match="pending checkpoint"):
            await service.resume(
                run_id=run_id,
                repository=RunRepository(session),
                approval_id=first.id,
                approval_repository=approvals,
                tool_call_repository=ToolCallRepository(session),
            )
        stored = RunRepository(session).get(run_id)
        assert stored is not None and stored.status is RunStatus.WAITING_APPROVAL
    assert len(write.calls) == 1
    assert len(provider.requests) == 2


@pytest.mark.asyncio
async def test_concurrent_native_resume_has_one_owner_and_one_effect(
    continuation_db: sessionmaker[Session],
) -> None:
    entered, release = asyncio.Event(), asyncio.Event()

    class BlockingWrite(CountingTool):
        async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
            entered.set()
            await release.wait()
            return await super().execute(arguments)

    write = BlockingWrite("write", write=True)
    registry = ToolRegistry()
    registry.register(write)
    with continuation_db() as session:
        run_id = queued(session)
        await RunExecutionService(
            provider=ScriptedProvider([reply(call("w1", "write"))]),
            tool_registry=registry,
        ).execute(run_id=run_id, repository=RunRepository(session))
        approvals = ApprovalRepository(session)
        approval = approvals.list_for_run(run_id)[0]
        approvals.approve(approval_id=approval.id)

    async def resume(provider: ScriptedProvider) -> Any:
        with continuation_db() as session:
            return await RunExecutionService(provider=provider, tool_registry=registry).resume(
                run_id=run_id,
                repository=RunRepository(session),
                approval_id=approval.id,
                approval_repository=ApprovalRepository(session),
                tool_call_repository=ToolCallRepository(session),
            )

    winner, loser = ScriptedProvider([reply(text="done")]), ScriptedProvider([])
    task = asyncio.create_task(resume(winner))
    try:
        await asyncio.wait_for(entered.wait(), timeout=5)
        with pytest.raises((RunAlreadyClaimedError, RunExecutionError)):
            await resume(loser)
    finally:
        release.set()
        result = await task
    assert result.status is RunStatus.SUCCEEDED
    assert len(write.calls) == 1
    assert len(winner.requests) == 1
    assert loser.requests == []
