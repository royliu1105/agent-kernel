import pytest
from kernel_core import RiskLevel, RunEventType, RunStatus
from kernel_providers import (
    LLMFinishReason,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMUsage,
    MockLLMProvider,
)
from kernel_runtime import RunExecutionService
from kernel_storage import AgentRepository, ApprovalRepository, RunRepository, ToolCallRepository
from kernel_tools import ToolMetadata, ToolRegistry
from kernel_tools.builtins import EchoTool
from sqlalchemy.orm import Session, sessionmaker


class PaidNativeProvider(MockLLMProvider):
    def __init__(self, tool_name: str) -> None:
        super().__init__()
        self.tool_name = tool_name
        self.calls = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        if self.calls > 1:
            assert self.calls == 2
            assert request.messages[-1].role.value == "tool"
            return LLMResponse(
                provider=self.name,
                model=request.model,
                text="approved result synthesized",
                usage=LLMUsage(input_tokens=10, output_tokens=2, estimated_cost=0.25),
            )
        return LLMResponse(
            provider=self.name,
            model=request.model,
            text="",
            finish_reason=LLMFinishReason.TOOL_CALLS,
            usage=LLMUsage(input_tokens=10, output_tokens=2, estimated_cost=0.25),
            tool_calls=(
                LLMToolCall(id="call-paid", name=self.tool_name, arguments={"message": "x"}),
            ),
        )


class ApprovedEcho(EchoTool):
    @property
    def metadata(self) -> ToolMetadata:
        return super().metadata.model_copy(update={"risk_level": RiskLevel.EXTERNAL_WRITE})


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", ["missing", "echo"])
async def test_usage_survives_native_failure_and_approval_resume(
    sqlite_session_factory: sessionmaker[Session],
    tool_name: str,
) -> None:
    registry = ToolRegistry()
    registry.register(ApprovedEcho())
    service = RunExecutionService(provider=PaidNativeProvider(tool_name), tool_registry=registry)
    with sqlite_session_factory() as session:
        repo = RunRepository(session)
        agent = AgentRepository(session).create(name="cost")
        run = repo.create(agent_id=agent.id, input_payload={"task": "call tool"})
        repo.apply_transition(
            run_id=run.id, status=RunStatus.QUEUED, event_type=RunEventType.RUN_QUEUED, payload={}
        )
        result = await service.execute(run_id=run.id, repository=repo)
        assert (
            result.input_tokens_total,
            result.output_tokens_total,
            result.estimated_cost_total,
        ) == (
            10,
            2,
            0.25,
        )
        if tool_name == "echo":
            assert result.status is RunStatus.WAITING_APPROVAL
            approvals = ApprovalRepository(session)
            approval = approvals.list_for_run(run.id)[0]
            approvals.approve(approval_id=approval.id)
            result = await service.resume(
                run_id=run.id,
                repository=repo,
                approval_repository=approvals,
                tool_call_repository=ToolCallRepository(session),
            )
            assert result.status is RunStatus.SUCCEEDED
        else:
            assert result.status is RunStatus.FAILED
        response_count = 2 if tool_name == "echo" else 1
        assert repo.usage_summary() == {
            "run_count": 1,
            "input_tokens": 10 * response_count,
            "output_tokens": 2 * response_count,
            "estimated_cost": 0.25 * response_count,
        }
        models = repo.usage_breakdown(group_by="model", run_id=run.id)
        assert len(models) == 1
        assert models[0]["provider"] == "mock"
        assert models[0]["estimated_cost"] == 0.25 * response_count
        assert models[0]["input_tokens"] == 10 * response_count
