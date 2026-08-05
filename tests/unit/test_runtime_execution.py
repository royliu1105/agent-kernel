import logging
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
    ToolCallStatus,
)
from kernel_observability import InMemoryMetricsRecorder
from kernel_providers import (
    LLMFinishReason,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMToolChoice,
    LLMUsage,
    MessageRole,
    MockLLMProvider,
)
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
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics_recorder = InMemoryMetricsRecorder()
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

        with caplog.at_level(logging.INFO, logger="kernel_runtime.execution"):
            completed = await RunExecutionService(
                provider=MockLLMProvider(),
                metrics_recorder=metrics_recorder,
            ).execute(
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
    structured_logs = _structured_logs(caplog)
    assert {
        log["event"] for log in structured_logs
    } >= {"agent.run.started", "llm.model_call.completed"}
    model_log = _single_log(structured_logs, "llm.model_call.completed")
    assert model_log["trace_id"] == completed.trace_id
    assert model_log["run_id"] == str(completed.id)
    assert model_log["agent_id"] == str(completed.agent_id)
    assert model_log["provider"] == "mock"
    assert model_log["model"] == "mock-small"
    assert model_log["input_tokens"] == 2
    assert model_log["output_tokens"] == 4
    assert model_log["estimated_cost"] == 0.0
    assert isinstance(model_log["latency_ms"], int)
    assert model_log["latency_ms"] >= 0
    metric_labels = {"provider": "mock", "model": "mock-small", "status": "succeeded"}
    token_labels = {"provider": "mock", "model": "mock-small"}
    assert metrics_recorder.counter_value("llm_model_calls_total", labels=metric_labels) == 1
    assert metrics_recorder.counter_value("llm_tokens_input_total", labels=token_labels) == 2
    assert metrics_recorder.counter_value("llm_tokens_output_total", labels=token_labels) == 4
    assert metrics_recorder.counter_value("llm_tokens_total", labels=token_labels) == 6
    assert metrics_recorder.counter_value("llm_estimated_cost_total", labels=token_labels) == 0.0
    assert len(
        metrics_recorder.observations("llm_model_call_latency_ms", labels=metric_labels)
    ) == 1
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
async def test_provider_retry_events_remain_visible_after_session_reopen(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="durable-retry-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "retry persistently", "model": "flaky:mock-retry"},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        provider = FlakyProvider(
            name="flaky",
            failures=[LLMProviderError("temporary outage", error_type="mock_transient")],
        )

        completed = await RunExecutionService(router=ModelRouter({"flaky": provider})).execute(
            run_id=run.id,
            repository=run_repository,
        )

    with sqlite_session_factory() as reopened_session:
        reopened_repository = RunRepository(reopened_session)
        loaded = reopened_repository.get(run.id)
        events = reopened_repository.list_events(run.id)

    assert completed.status is RunStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status is RunStatus.SUCCEEDED
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.MODEL_CALL_RETRYING,
        RunEventType.RUN_COMPLETED,
    ]
    retry_event = events[3]
    assert retry_event.payload["attempt"] == 2
    assert retry_event.payload["error_type"] == "mock_transient"
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
async def test_execution_service_completes_provider_native_tool_loop(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    provider = NativeToolLoopProvider(
        tool_call=LLMToolCall(
            id="call_echo_001",
            name="echo",
            arguments={"message": "native hello"},
            raw={
                "type": "function_call",
                "call_id": "call_echo_001",
                "name": "echo",
                "arguments": '{"message":"native hello"}',
            },
        ),
        final_text="final answer with tool result",
    )
    metrics_recorder = InMemoryMetricsRecorder()
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="native-tool-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "use native tool", "model": "native:mock-native"},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

        completed = await RunExecutionService(
            router=ModelRouter({"native": provider}),
            metrics_recorder=metrics_recorder,
        ).execute(run_id=run.id, repository=run_repository)
        events = run_repository.list_events(run.id)
        tool_calls = ToolCallRepository(session).list_for_run(run.id)

    assert completed.status is RunStatus.SUCCEEDED
    assert completed.input_tokens_total == 12
    assert completed.output_tokens_total == 3
    assert completed.output is not None
    assert completed.output["text"] == "final answer with tool result"
    assert completed.output["provider_tool_loop"] == {
        "tool_call_id": str(tool_calls[0].id),
        "provider_tool_call_id": "call_echo_001",
        "tool_name": "echo",
        "tool_result": {"message": "native hello"},
    }
    assert provider.call_count == 2
    assert provider.requests[0].tools[0].name == "echo"
    assert provider.requests[0].tool_choice is LLMToolChoice.AUTO
    assert provider.requests[1].tools == ()
    assert provider.requests[1].tool_choice is LLMToolChoice.NONE
    assert provider.requests[1].messages[-1].role is MessageRole.TOOL
    assert provider.requests[1].messages[-1].name == "echo"
    assert "native hello" in provider.requests[1].messages[-1].content
    assert tool_calls[0].provider_name == "native"
    assert tool_calls[0].provider_tool_call_id == "call_echo_001"
    assert tool_calls[0].status is ToolCallStatus.SUCCEEDED
    assert tool_calls[0].result == {"message": "native hello"}
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.TOOL_CALL_REQUESTED,
        RunEventType.POLICY_EVALUATED,
        RunEventType.TOOL_CALL_COMPLETED,
        RunEventType.RUN_COMPLETED,
    ]
    assert events[-1].payload["provider_tool_loop"]["provider_tool_call_id"] == "call_echo_001"
    model_labels = {"provider": "native", "model": "mock-native", "status": "succeeded"}
    assert metrics_recorder.counter_value("llm_model_calls_total", labels=model_labels) == 1


@pytest.mark.asyncio
async def test_execution_service_pauses_provider_native_risky_tool_for_approval(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    provider = NativeToolLoopProvider(
        tool_call=LLMToolCall(
            id="call_write_001",
            name="external_write",
            arguments={"value": "draft"},
            raw={"type": "function_call", "call_id": "call_write_001"},
        ),
        final_text="unused",
    )
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="native-approval-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "write through native tool", "model": "native:mock-native"},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

        waiting = await RunExecutionService(
            router=ModelRouter({"native": provider}),
            tool_registry=_approval_tool_registry(),
        ).execute(run_id=run.id, repository=run_repository)
        approvals = ApprovalRepository(session).list_for_run(run.id)
        tool_calls = ToolCallRepository(session).list_for_run(run.id)
        events = run_repository.list_events(run.id)

    assert waiting.status is RunStatus.WAITING_APPROVAL
    assert provider.call_count == 1
    assert len(approvals) == 1
    assert approvals[0].tool_call_id == tool_calls[0].id
    assert tool_calls[0].provider_name == "native"
    assert tool_calls[0].provider_tool_call_id == "call_write_001"
    assert tool_calls[0].status is ToolCallStatus.WAITING_APPROVAL
    assert events[-1].type is RunEventType.RUN_WAITING_APPROVAL
    assert events[-1].payload["provider_tool_call_id"] == "call_write_001"


@pytest.mark.asyncio
async def test_execution_service_fails_unknown_provider_native_tool(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    provider = NativeToolLoopProvider(
        tool_call=LLMToolCall(
            id="call_unknown_001",
            name="unknown_tool",
            arguments={},
            raw={"type": "function_call", "call_id": "call_unknown_001"},
        ),
        final_text="unused",
    )
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="native-unknown-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "unknown native tool", "model": "native:mock-native"},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

        failed = await RunExecutionService(router=ModelRouter({"native": provider})).execute(
            run_id=run.id,
            repository=run_repository,
        )
        tool_calls = ToolCallRepository(session).list_for_run(run.id)
        events = run_repository.list_events(run.id)

    assert failed.status is RunStatus.FAILED
    assert failed.error_type == "unknown_tool"
    assert provider.call_count == 1
    assert tool_calls[0].risk_level is RiskLevel.DANGEROUS
    assert tool_calls[0].status is ToolCallStatus.FAILED
    assert tool_calls[0].provider_tool_call_id == "call_unknown_001"
    assert events[-1].type is RunEventType.RUN_FAILED


@pytest.mark.asyncio
async def test_execution_service_completes_safe_explicit_tool_run(
    sqlite_session_factory: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics_recorder = InMemoryMetricsRecorder()
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

        with caplog.at_level(logging.INFO, logger="kernel_runtime.execution"):
            completed = await RunExecutionService(metrics_recorder=metrics_recorder).execute(
                run_id=run.id,
                repository=run_repository,
            )
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
    assert tool_calls[0].trace_id == run.trace_id
    assert {event.trace_id for event in events} == {run.trace_id}
    structured_logs = _structured_logs(caplog)
    requested_log = _single_log(structured_logs, "tool.call.requested")
    completed_log = _single_log(structured_logs, "tool.call.completed")
    assert requested_log["trace_id"] == completed.trace_id
    assert requested_log["run_id"] == str(completed.id)
    assert requested_log["tool_call_id"] == str(tool_calls[0].id)
    assert requested_log["tool_name"] == "echo"
    assert requested_log["risk_level"] == "read_only"
    assert completed_log["tool_call_id"] == str(tool_calls[0].id)
    assert completed_log["status"] == "succeeded"
    assert isinstance(completed_log["latency_ms"], int)
    assert completed_log["latency_ms"] >= 0
    assert tool_calls[0].latency_ms is not None
    assert tool_calls[0].latency_ms >= 0
    tool_labels = {"tool_name": "echo", "status": "succeeded"}
    assert metrics_recorder.counter_value("tool_calls_total", labels=tool_labels) == 1
    assert len(metrics_recorder.observations("tool_call_latency_ms", labels=tool_labels)) == 1
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
    assert tool_calls[0].trace_id == run.trace_id
    assert {event.trace_id for event in events} == {run.trace_id}
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
async def test_tool_retry_events_remain_visible_after_session_reopen(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    registry = create_default_tool_registry()
    flaky_tool = FlakyReadOnlyTool()
    registry.register(flaky_tool)
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="durable-tool-retry-agent")
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

    with sqlite_session_factory() as reopened_session:
        reopened_repository = RunRepository(reopened_session)
        loaded = reopened_repository.get(run.id)
        events = reopened_repository.list_events(run.id)
        tool_calls = ToolCallRepository(reopened_session).list_for_run(run.id)

    assert completed.status is RunStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status is RunStatus.SUCCEEDED
    assert RunEventType.TOOL_CALL_RETRYING in [event.type for event in events]
    retry_event = next(event for event in events if event.type is RunEventType.TOOL_CALL_RETRYING)
    assert retry_event.payload["attempt"] == 2
    assert retry_event.payload["error_type"] == "tool_execution_failed"
    assert tool_calls[0].result == {"value": "stable", "attempts": 2}


@pytest.mark.asyncio
async def test_execution_service_does_not_retry_invalid_tool_arguments(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    metrics_recorder = InMemoryMetricsRecorder()
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

        failed = await RunExecutionService(metrics_recorder=metrics_recorder).execute(
            run_id=run.id,
            repository=run_repository,
        )
        events = run_repository.list_events(run.id)
        tool_calls = ToolCallRepository(session).list_for_run(run.id)

    assert failed.status is RunStatus.FAILED
    assert failed.error_type == "invalid_tool_arguments"
    assert tool_calls[0].status is ToolCallStatus.FAILED
    assert tool_calls[0].latency_ms is not None
    assert tool_calls[0].latency_ms >= 0
    labels = {
        "tool_name": "echo",
        "status": "failed",
        "error_type": "invalid_tool_arguments",
    }
    assert metrics_recorder.counter_value("tool_calls_total", labels=labels) == 1
    assert metrics_recorder.counter_value("tool_call_failure_total", labels=labels) == 1
    assert len(metrics_recorder.observations("tool_call_latency_ms", labels=labels)) == 1
    assert RunEventType.TOOL_CALL_RETRYING not in [event.type for event in events]
    assert events[-1].type is RunEventType.RUN_FAILED


@pytest.mark.asyncio
async def test_execution_service_pauses_risky_explicit_tool_for_approval(
    sqlite_session_factory: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
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

        with caplog.at_level(logging.INFO, logger="kernel_runtime.execution"):
            waiting = await RunExecutionService(tool_registry=_approval_tool_registry()).execute(
                run_id=run.id,
                repository=run_repository,
            )
        approvals = ApprovalRepository(session).list_for_run(run.id)
        tool_calls = ToolCallRepository(session).list_for_run(run.id)
        events = run_repository.list_events(run.id)

    assert waiting.status is RunStatus.WAITING_APPROVAL
    assert len(approvals) == 1
    assert approvals[0].status is ApprovalStatus.REQUESTED
    assert approvals[0].trace_id == run.trace_id
    assert tool_calls[0].trace_id == run.trace_id
    assert {event.trace_id for event in events} == {run.trace_id}
    approval_log = _single_log(_structured_logs(caplog), "approval.requested")
    assert approval_log["trace_id"] == waiting.trace_id
    assert approval_log["run_id"] == str(waiting.id)
    assert approval_log["tool_call_id"] == str(tool_calls[0].id)
    assert approval_log["approval_id"] == str(approvals[0].id)
    assert approval_log["tool_name"] == "external_write"
    assert approval_log["requires_approval"] is True
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
    assert tool_calls[0].trace_id == run.trace_id
    assert {event.trace_id for event in events} == {run.trace_id}
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


def _structured_logs(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    for record in caplog.records:
        structured = getattr(record, "structured", None)
        if isinstance(structured, dict):
            logs.append(structured)
    return logs


def _single_log(logs: list[dict[str, Any]], event: str) -> dict[str, Any]:
    matches = [log for log in logs if log.get("event") == event]
    assert len(matches) == 1
    return matches[0]


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


class NativeToolLoopProvider:
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
