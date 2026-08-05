from __future__ import annotations

from typing import Any

import pytest
from kernel_core import RiskLevel, RunEventType, RunStatus
from kernel_evals import (
    ToolCallEvalCase,
    ToolCallEvalObservation,
    ToolCallEvalRunner,
    ToolCallEvalToolCall,
)
from kernel_providers import (
    LLMFinishReason,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMUsage,
)
from kernel_runtime import ModelRouter, RunExecutionService
from kernel_storage import AgentRepository, RunRepository, ToolCallRepository
from kernel_tools import ToolMetadata, ToolRegistry, create_default_tool_registry
from sqlalchemy.orm import Session, sessionmaker


@pytest.mark.asyncio
async def test_tool_call_eval_runner_passes_provider_native_runtime_cases(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    report = await ToolCallEvalRunner(name="native-tool-smoke").run(
        cases=(
            ToolCallEvalCase(
                name="safe-native-tool",
                expected_run_status=RunStatus.SUCCEEDED.value,
                expected_tool_call_count=1,
                expected_tool_name="echo",
                expected_tool_status="succeeded",
                expected_provider_tool_call_id="call_echo_001",
                expected_event_types=(
                    RunEventType.RUN_CREATED.value,
                    RunEventType.RUN_QUEUED.value,
                    RunEventType.RUN_STARTED.value,
                    RunEventType.TOOL_CALL_REQUESTED.value,
                    RunEventType.POLICY_EVALUATED.value,
                    RunEventType.TOOL_CALL_COMPLETED.value,
                    RunEventType.RUN_COMPLETED.value,
                ),
                expected_model_call_count=2,
                requires_provider_tool_loop=True,
                output_must_contain=("native hello", "final answer"),
            ),
            ToolCallEvalCase(
                name="approval-native-tool",
                expected_run_status=RunStatus.WAITING_APPROVAL.value,
                expected_tool_call_count=1,
                expected_tool_name="external_write",
                expected_tool_status="waiting_approval",
                expected_provider_tool_call_id="call_write_001",
                expected_event_types=(
                    RunEventType.RUN_CREATED.value,
                    RunEventType.RUN_QUEUED.value,
                    RunEventType.RUN_STARTED.value,
                    RunEventType.TOOL_CALL_REQUESTED.value,
                    RunEventType.POLICY_EVALUATED.value,
                    RunEventType.APPROVAL_REQUESTED.value,
                    RunEventType.RUN_WAITING_APPROVAL.value,
                ),
                expected_model_call_count=1,
            ),
            ToolCallEvalCase(
                name="unknown-native-tool",
                expected_run_status=RunStatus.FAILED.value,
                expected_error_type="unknown_tool",
                expected_tool_call_count=1,
                expected_tool_name="unknown_tool",
                expected_tool_status="failed",
                expected_provider_tool_call_id="call_unknown_001",
                expected_event_types=(
                    RunEventType.RUN_CREATED.value,
                    RunEventType.RUN_QUEUED.value,
                    RunEventType.RUN_STARTED.value,
                    RunEventType.TOOL_CALL_REQUESTED.value,
                    RunEventType.TOOL_CALL_FAILED.value,
                    RunEventType.RUN_FAILED.value,
                ),
                expected_model_call_count=1,
            ),
        ),
        execute=lambda case: _execute_native_tool_case(
            sqlite_session_factory=sqlite_session_factory,
            case=case,
        ),
    )

    failures = {
        result.case_name: [
            (assertion.name, assertion.message)
            for assertion in result.assertions
            if not assertion.passed
        ]
        for result in report.case_results
        if not result.passed
    }
    assert failures == {}
    assert report.passed_count == 3
    assert report.failed_count == 0


@pytest.mark.asyncio
async def test_tool_call_eval_runner_reports_readable_failures() -> None:
    report = await ToolCallEvalRunner().run(
        cases=(
            ToolCallEvalCase(
                name="bad-native-tool-output",
                expected_run_status="succeeded",
                expected_tool_call_count=1,
                expected_tool_name="echo",
                expected_tool_status="succeeded",
                expected_provider_tool_call_id="call_echo_001",
                expected_event_types=("run_created", "run_completed"),
                expected_model_call_count=2,
                requires_provider_tool_loop=True,
                output_must_contain=("missing term",),
            ),
        ),
        execute=lambda _case: _fake_bad_observation(),
    )

    assert report.passed is False
    failed = {
        assertion.name: assertion.message
        for assertion in report.case_results[0].assertions
        if not assertion.passed
    }
    assert failed["event_sequence"].startswith("Event sequence was")
    assert "missing term" in failed["output_content"]


async def _execute_native_tool_case(
    *,
    sqlite_session_factory: sessionmaker[Session],
    case: ToolCallEvalCase,
) -> ToolCallEvalObservation:
    provider = _provider_for_case(case.name)
    tool_registry = (
        _approval_tool_registry()
        if case.name == "approval-native-tool"
        else create_default_tool_registry()
    )
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name=f"{case.name}-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": case.name, "model": "native:mock-native"},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

        result = await RunExecutionService(
            router=ModelRouter({"native": provider}),
            tool_registry=tool_registry,
        ).execute(run_id=run.id, repository=run_repository)
        events = run_repository.list_events(run.id)
        tool_calls = ToolCallRepository(session).list_for_run(run.id)

    return ToolCallEvalObservation(
        run_status=result.status.value,
        output=result.output,
        error_type=result.error_type,
        events=tuple(event.type.value for event in events),
        tool_calls=tuple(
            ToolCallEvalToolCall(
                tool_name=tool_call.tool_name,
                status=tool_call.status.value,
                provider_name=tool_call.provider_name,
                provider_tool_call_id=tool_call.provider_tool_call_id,
                result=tool_call.result,
            )
            for tool_call in tool_calls
        ),
        model_call_count=provider.call_count,
    )


def _provider_for_case(case_name: str) -> _NativeToolLoopProvider:
    if case_name == "safe-native-tool":
        return _NativeToolLoopProvider(
            tool_call=LLMToolCall(
                id="call_echo_001",
                name="echo",
                arguments={"message": "native hello"},
                raw={"type": "function_call", "call_id": "call_echo_001"},
            ),
            final_text="final answer",
        )
    if case_name == "approval-native-tool":
        return _NativeToolLoopProvider(
            tool_call=LLMToolCall(
                id="call_write_001",
                name="external_write",
                arguments={"value": "draft"},
                raw={"type": "function_call", "call_id": "call_write_001"},
            ),
            final_text="unused",
        )
    if case_name == "unknown-native-tool":
        return _NativeToolLoopProvider(
            tool_call=LLMToolCall(
                id="call_unknown_001",
                name="unknown_tool",
                arguments={},
                raw={"type": "function_call", "call_id": "call_unknown_001"},
            ),
            final_text="unused",
        )
    raise AssertionError(f"Unknown eval case {case_name}.")


async def _fake_bad_observation() -> ToolCallEvalObservation:
    return ToolCallEvalObservation(
        run_status="succeeded",
        output={"text": "final answer", "provider_tool_loop": {}},
        events=("run_created", "tool_call_requested", "run_completed"),
        tool_calls=(
            ToolCallEvalToolCall(
                tool_name="echo",
                status="succeeded",
                provider_tool_call_id="call_echo_001",
            ),
        ),
        model_call_count=2,
    )


class _NativeToolLoopProvider:
    def __init__(self, *, tool_call: LLMToolCall, final_text: str) -> None:
        self._tool_call = tool_call
        self._final_text = final_text
        self.requests: list[LLMRequest] = []

    @property
    def name(self) -> str:
        return "native"

    @property
    def call_count(self) -> int:
        return len(self.requests)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            return LLMResponse(
                provider=self.name,
                model=request.model,
                text="",
                usage=LLMUsage(input_tokens=5, output_tokens=0, estimated_cost=0.0),
                finish_reason=LLMFinishReason.TOOL_CALLS,
                tool_calls=(self._tool_call,),
            )
        return LLMResponse(
            provider=self.name,
            model=request.model,
            text=self._final_text,
            usage=LLMUsage(input_tokens=7, output_tokens=3, estimated_cost=0.0),
        )


class _ExternalWriteTool:
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="external_write",
            description="Test write operation that requires approval.",
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
                "additionalProperties": False,
            },
            output_schema={"type": "object"},
            risk_level=RiskLevel.EXTERNAL_WRITE,
            timeout_ms=1_000,
            enabled=True,
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"value": arguments["value"]}


def _approval_tool_registry() -> ToolRegistry:
    registry = create_default_tool_registry()
    registry.register(_ExternalWriteTool())
    return registry
