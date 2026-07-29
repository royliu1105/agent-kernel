from typing import Any
from uuid import UUID

import pytest
from kernel_core import (
    ApprovalStatus,
    DocumentChunk,
    DocumentStatus,
    MemoryType,
    RiskLevel,
    RunEventType,
    RunStatus,
)
from kernel_providers import LLMProviderError, LLMRequest, LLMResponse, LLMUsage, MockLLMProvider
from kernel_rag import DocumentIndexingService, create_rag_tool_registry
from kernel_runtime import ModelRouter, RunExecutionError, RunExecutionService
from kernel_storage import (
    AgentRepository,
    ApprovalRepository,
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
    MemoryRepository,
    RunRepository,
    ToolCallRepository,
)
from kernel_tools import ToolMetadata, ToolRegistry, create_default_tool_registry
from sqlalchemy.orm import Session, sessionmaker


@pytest.mark.asyncio
async def test_execution_service_completes_queued_run(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="research-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "summarize notes", "model": "mock:mock-small"},
        )
        queued = run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        assert queued is not None

        completed = await RunExecutionService(provider=MockLLMProvider()).execute(
            run_id=run.id,
            repository=run_repository,
        )
        events = run_repository.list_events(run.id)

    assert completed.status is RunStatus.SUCCEEDED
    assert completed.output == {
        "text": "Mock response: summarize notes",
        "provider": "mock",
        "model": "mock-small",
        "usage": {
            "input_tokens": 2,
            "output_tokens": 4,
            "estimated_cost": 0.0,
        },
    }
    assert completed.input_tokens_total == 2
    assert completed.output_tokens_total == 4
    assert completed.estimated_cost_total == 0.0
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.RUN_COMPLETED,
    ]


@pytest.mark.asyncio
async def test_execution_service_injects_explicit_memory_context(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    provider = CapturingProvider()
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="memory-agent")
        memory = MemoryRepository(session).create(
            type=MemoryType.USER_PREFERENCE,
            scope="user:roy",
            content={"language": "zh", "style": "concise"},
            confidence=0.9,
        )
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={
                "task": "summarize notes",
                "model": "capture:memory",
                "memory": {
                    "scopes": ["user:roy"],
                    "types": ["user_preference"],
                    "limit": 5,
                },
            },
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

        completed = await RunExecutionService(provider=provider).execute(
            run_id=run.id,
            repository=run_repository,
        )
        events = run_repository.list_events(run.id)

    assert completed.status is RunStatus.SUCCEEDED
    assert completed.output is not None
    assert completed.output["memory"] == {
        "used": True,
        "item_count": 1,
        "item_ids": [str(memory.id)],
    }
    assert provider.last_request is not None
    assert provider.last_request.messages[0].role.value == "system"
    assert provider.last_request.messages[0].name == "memory_context"
    assert "type=user_preference" in provider.last_request.messages[0].content
    assert '"language": "zh"' in provider.last_request.messages[0].content
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.MEMORY_RETRIEVED,
        RunEventType.RUN_COMPLETED,
    ]
    assert events[3].payload["item_ids"] == [str(memory.id)]
    assert events[3].payload["requested_scopes"] == ["user:roy"]


@pytest.mark.asyncio
async def test_execution_service_fails_invalid_memory_config(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="memory-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={
                "task": "summarize notes",
                "memory": {"scopes": []},
            },
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

        failed = await RunExecutionService(provider=MockLLMProvider()).execute(
            run_id=run.id,
            repository=run_repository,
        )
        events = run_repository.list_events(run.id)

    assert failed.status is RunStatus.FAILED
    assert failed.error_type == "RunExecutionError"
    assert failed.error_message is not None
    assert "memory.scopes" in failed.error_message
    assert events[-1].type is RunEventType.RUN_FAILED


@pytest.mark.asyncio
async def test_execution_service_marks_run_failed_on_provider_error(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="research-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(agent_id=agent.id, input_payload={"task": "summarize notes"})
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        provider = MockLLMProvider(
            fail_with=LLMProviderError("provider unavailable", error_type="mock_failure")
        )

        failed = await RunExecutionService(provider=provider).execute(
            run_id=run.id,
            repository=run_repository,
        )
        events = run_repository.list_events(run.id)

    assert failed.status is RunStatus.FAILED
    assert failed.error_type == "mock_failure"
    assert failed.error_message == "provider unavailable"
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.RUN_FAILED,
    ]
    assert events[-1].payload["error_type"] == "mock_failure"


@pytest.mark.asyncio
async def test_execution_service_rejects_unqueued_run(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="research-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(agent_id=agent.id, input_payload={"task": "summarize notes"})

        with pytest.raises(ValueError, match="Cannot transition run from created to running"):
            await RunExecutionService(provider=MockLLMProvider()).execute(
                run_id=run.id,
                repository=run_repository,
            )


@pytest.mark.asyncio
async def test_execution_service_can_execute_through_model_router(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="research-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "route me", "model": "mock:mock-routed"},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        router = ModelRouter({"mock": MockLLMProvider(response_prefix="Routed")})

        completed = await RunExecutionService(router=router).execute(
            run_id=run.id,
            repository=run_repository,
        )

    assert completed.output is not None
    assert completed.output["text"] == "Routed: route me"
    assert completed.output["model"] == "mock-routed"


@pytest.mark.asyncio
async def test_execution_service_retries_retryable_provider_error(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="retry-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "retry me", "model": "flaky:mock-retry"},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        provider = FlakyProvider(
            name="flaky",
            failures=[
                LLMProviderError("temporary outage", error_type="mock_transient"),
            ],
        )

        completed = await RunExecutionService(router=ModelRouter({"flaky": provider})).execute(
            run_id=run.id, repository=run_repository
        )
        events = run_repository.list_events(run.id)

    assert completed.status is RunStatus.SUCCEEDED
    assert completed.output is not None
    assert completed.output["text"] == "flaky success: retry me"
    assert provider.call_count == 2
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.MODEL_CALL_RETRYING,
        RunEventType.RUN_COMPLETED,
    ]
    assert events[-1].payload["attempt_count"] == 2


@pytest.mark.asyncio
async def test_execution_service_falls_back_after_retryable_provider_error(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="fallback-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={
                "task": "fallback me",
                "model": "primary:mock-primary",
                "fallback_models": ["backup:mock-backup"],
            },
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        primary = FlakyProvider(
            name="primary",
            failures=[
                LLMProviderError("temporary outage", error_type="mock_transient"),
                LLMProviderError("still down", error_type="mock_transient"),
            ],
        )
        backup = FlakyProvider(name="backup")

        completed = await RunExecutionService(
            router=ModelRouter({"primary": primary, "backup": backup})
        ).execute(run_id=run.id, repository=run_repository)
        events = run_repository.list_events(run.id)

    assert completed.status is RunStatus.SUCCEEDED
    assert completed.output is not None
    assert completed.output["provider"] == "backup"
    assert completed.output["model"] == "mock-backup"
    assert primary.call_count == 2
    assert backup.call_count == 1
    assert RunEventType.MODEL_FALLBACK_SELECTED in [event.type for event in events]
    assert events[-1].payload["fallback_used"] is True


@pytest.mark.asyncio
async def test_execution_service_completes_safe_explicit_tool_run(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="tool-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "echo", "arguments": {"message": "hello"}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

        completed = await RunExecutionService().execute(run_id=run.id, repository=run_repository)
        events = run_repository.list_events(run.id)
        tool_calls = ToolCallRepository(session).list_for_run(run.id)

    assert completed.status is RunStatus.SUCCEEDED
    assert completed.output == {
        "tool": {
            "tool_call_id": str(tool_calls[0].id),
            "approval_id": None,
            "name": "echo",
            "result": {"message": "hello"},
        }
    }
    assert tool_calls[0].result == {"message": "hello"}
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.TOOL_CALL_REQUESTED,
        RunEventType.POLICY_EVALUATED,
        RunEventType.TOOL_CALL_COMPLETED,
        RunEventType.RUN_COMPLETED,
    ]


@pytest.mark.asyncio
async def test_execution_service_completes_explicit_kb_search_tool_run(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    knowledge_base_id, chunk_id = _create_indexed_document(
        sqlite_session_factory,
        content="alpha deployment rollback checklist",
    )
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="rag-tool-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={
                "tool": {
                    "name": "kb_search",
                    "arguments": {
                        "knowledge_base_id": str(knowledge_base_id),
                        "query": "alpha deployment rollback checklist",
                        "top_k": 1,
                    },
                }
            },
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

        completed = await RunExecutionService(
            tool_registry=create_rag_tool_registry(session_factory=sqlite_session_factory)
        ).execute(run_id=run.id, repository=run_repository)
        events = run_repository.list_events(run.id)
        tool_calls = ToolCallRepository(session).list_for_run(run.id)

    assert completed.status is RunStatus.SUCCEEDED
    assert completed.output is not None
    tool_output = completed.output["tool"]
    assert tool_output["name"] == "kb_search"
    result = tool_output["result"]["results"][0]
    assert result["content"] == "alpha deployment rollback checklist"
    assert result["citation"]["chunk_id"] == str(chunk_id)
    assert tool_calls[0].tool_name == "kb_search"
    assert tool_calls[0].risk_level is RiskLevel.READ_ONLY
    assert tool_calls[0].result == tool_output["result"]
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.TOOL_CALL_REQUESTED,
        RunEventType.POLICY_EVALUATED,
        RunEventType.TOOL_CALL_COMPLETED,
        RunEventType.RUN_COMPLETED,
    ]


@pytest.mark.asyncio
async def test_execution_service_retries_safe_tool_failure(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    registry = create_default_tool_registry()
    flaky_tool = FlakyReadOnlyTool()
    registry.register(flaky_tool)
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="tool-retry-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "flaky_read", "arguments": {"value": "stable"}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

        completed = await RunExecutionService(tool_registry=registry).execute(
            run_id=run.id,
            repository=run_repository,
        )
        events = run_repository.list_events(run.id)

    assert completed.status is RunStatus.SUCCEEDED
    assert completed.output is not None
    assert completed.output["tool"]["result"] == {"value": "stable", "attempts": 2}
    assert flaky_tool.call_count == 2
    assert RunEventType.TOOL_CALL_RETRYING in [event.type for event in events]
    assert events[-1].type is RunEventType.RUN_COMPLETED


@pytest.mark.asyncio
async def test_execution_service_does_not_retry_invalid_tool_arguments(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="tool-validation-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "echo", "arguments": {}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

        failed = await RunExecutionService().execute(run_id=run.id, repository=run_repository)
        events = run_repository.list_events(run.id)

    assert failed.status is RunStatus.FAILED
    assert failed.error_type == "invalid_tool_arguments"
    assert RunEventType.TOOL_CALL_RETRYING not in [event.type for event in events]
    assert events[-1].type is RunEventType.RUN_FAILED


@pytest.mark.asyncio
async def test_execution_service_pauses_risky_explicit_tool_for_approval(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="approval-tool-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "external_write", "arguments": {"value": "draft"}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

        waiting = await RunExecutionService(tool_registry=_approval_tool_registry()).execute(
            run_id=run.id,
            repository=run_repository,
        )
        approvals = ApprovalRepository(session).list_for_run(run.id)
        events = run_repository.list_events(run.id)

    assert waiting.status is RunStatus.WAITING_APPROVAL
    assert len(approvals) == 1
    assert approvals[0].status is ApprovalStatus.REQUESTED
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.TOOL_CALL_REQUESTED,
        RunEventType.POLICY_EVALUATED,
        RunEventType.APPROVAL_REQUESTED,
        RunEventType.RUN_WAITING_APPROVAL,
    ]


@pytest.mark.asyncio
async def test_execution_service_resumes_approved_tool_with_persisted_arguments(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="approval-tool-agent")
        run_repository = RunRepository(session)
        approval_repository = ApprovalRepository(session)
        tool_call_repository = ToolCallRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "external_write", "arguments": {"value": "original"}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        service = RunExecutionService(tool_registry=_approval_tool_registry())
        waiting = await service.execute(run_id=run.id, repository=run_repository)
        approval = approval_repository.list_for_run(run.id)[0]
        approval_repository.approve(
            approval_id=approval.id,
            decision_note="Approved for test.",
        )

        resumed = await service.resume(
            run_id=waiting.id,
            repository=run_repository,
            approval_repository=approval_repository,
            tool_call_repository=tool_call_repository,
            approval_id=approval.id,
        )
        events = run_repository.list_events(run.id)
        tool_calls = tool_call_repository.list_for_run(run.id)

    assert resumed.status is RunStatus.SUCCEEDED
    assert resumed.output is not None
    assert resumed.output["tool"]["result"] == {"written": "original"}
    assert tool_calls[0].arguments == {"value": "original"}
    assert tool_calls[0].result == {"written": "original"}
    assert RunEventType.RUN_RESUMING in [event.type for event in events]
    assert events[-1].type is RunEventType.RUN_COMPLETED


@pytest.mark.asyncio
async def test_execution_service_fails_rejected_approval_on_resume(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="approval-tool-agent")
        run_repository = RunRepository(session)
        approval_repository = ApprovalRepository(session)
        tool_call_repository = ToolCallRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "external_write", "arguments": {"value": "draft"}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        service = RunExecutionService(tool_registry=_approval_tool_registry())
        waiting = await service.execute(run_id=run.id, repository=run_repository)
        approval = approval_repository.list_for_run(run.id)[0]
        approval_repository.reject(approval_id=approval.id, decision_note="Do not write.")

        failed = await service.resume(
            run_id=waiting.id,
            repository=run_repository,
            approval_repository=approval_repository,
            tool_call_repository=tool_call_repository,
            approval_id=approval.id,
        )
        events = run_repository.list_events(run.id)

    assert failed.status is RunStatus.FAILED
    assert failed.error_type == "approval_rejected"
    assert failed.error_message == "Do not write."
    assert events[-1].type is RunEventType.RUN_FAILED


@pytest.mark.asyncio
async def test_execution_service_rejects_resume_before_approval_decision(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="approval-tool-agent")
        run_repository = RunRepository(session)
        approval_repository = ApprovalRepository(session)
        tool_call_repository = ToolCallRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "external_write", "arguments": {"value": "draft"}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        service = RunExecutionService(tool_registry=_approval_tool_registry())
        waiting = await service.execute(run_id=run.id, repository=run_repository)
        approval = approval_repository.list_for_run(run.id)[0]

        with pytest.raises(RunExecutionError, match="has not been decided yet"):
            await service.resume(
                run_id=waiting.id,
                repository=run_repository,
                approval_repository=approval_repository,
                tool_call_repository=tool_call_repository,
                approval_id=approval.id,
            )


class ExternalWriteTool:
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="external_write",
            description="Test-only external write tool.",
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
                "additionalProperties": False,
            },
            risk_level=RiskLevel.EXTERNAL_WRITE,
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"written": arguments["value"]}


class FlakyReadOnlyTool:
    def __init__(self) -> None:
        self.call_count = 0

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="flaky_read",
            description="Test-only flaky read tool.",
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
                "additionalProperties": False,
            },
            risk_level=RiskLevel.READ_ONLY,
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self.call_count += 1
        if self.call_count == 1:
            raise RuntimeError("temporary tool failure")
        return {"value": arguments["value"], "attempts": self.call_count}


class CapturingProvider:
    def __init__(self) -> None:
        self.last_request: LLMRequest | None = None

    @property
    def name(self) -> str:
        return "capture"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        return LLMResponse(
            provider=self.name,
            model=request.model,
            text="captured",
            usage=LLMUsage(input_tokens=1, output_tokens=1, estimated_cost=0.0),
        )


class FlakyProvider:
    def __init__(
        self,
        *,
        name: str,
        failures: list[LLMProviderError] | None = None,
    ) -> None:
        self._name = name
        self._failures = failures or []
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        if self._failures:
            raise self._failures.pop(0)

        prompt = request.messages[-1].content
        return LLMResponse(
            provider=self.name,
            model=request.model,
            text=f"{self.name} success: {prompt}",
            usage=LLMUsage(input_tokens=1, output_tokens=1, estimated_cost=0.0),
        )


def _approval_tool_registry() -> ToolRegistry:
    registry = create_default_tool_registry()
    registry.register(ExternalWriteTool())
    return registry


def _create_indexed_document(
    sqlite_session_factory: sessionmaker[Session],
    *,
    content: str,
) -> tuple[UUID, UUID]:
    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="kb")
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Deploy Guide",
            source_uri="object://local/docs/deploy.md",
            status=DocumentStatus.CHUNKED,
        )
        assert document is not None
        chunks = DocumentChunkRepository(session).replace_for_document(
            document_id=document.id,
            chunks=[
                DocumentChunk(
                    document_id=document.id,
                    index=0,
                    content=content,
                    start_char=0,
                    end_char=len(content),
                    token_count_estimate=4,
                    checksum="sha256:chunk",
                )
            ],
        )
        assert chunks is not None
        DocumentIndexingService().index_document(
            document_id=document.id,
            document_repository=DocumentRepository(session),
            chunk_repository=DocumentChunkRepository(session),
            embedding_repository=ChunkEmbeddingRepository(session),
        )
        return knowledge_base.id, chunks[0].id
