"""Single-run deterministic execution service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from kernel_core import (
    Approval,
    ApprovalStatus,
    MemoryType,
    RiskLevel,
    Run,
    RunEventType,
    RunStatus,
    ToolCall,
    ToolCallStatus,
)
from kernel_memory import MemoryContext, MemoryRetrievalService
from kernel_policy import PolicyDecisionType, ToolPolicyEvaluator
from kernel_providers import (
    LLMMessage,
    LLMProvider,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    MessageRole,
)
from kernel_storage import ApprovalRepository, MemoryRepository, RunRepository, ToolCallRepository
from kernel_tools import (
    ToolError,
    ToolExecutor,
    ToolRegistry,
    ToolRequest,
    create_default_tool_registry,
)

from kernel_runtime.router import ModelRouter
from kernel_runtime.state_machine import RunStateMachine


class RunExecutionError(RuntimeError):
    """Raised when a run cannot be executed."""


class RunNotFoundError(RunExecutionError):
    """Raised when execution is requested for a missing run."""


@dataclass(frozen=True)
class ExplicitToolRequest:
    """A tool request embedded directly in run input."""

    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ExplicitMemoryRequest:
    """Explicit memory retrieval request embedded directly in run input."""

    scopes: tuple[str, ...]
    types: tuple[MemoryType, ...] | None = None
    limit: int = 10


@dataclass(frozen=True)
class RetryPolicy:
    """Conservative in-process retry/fallback policy."""

    provider_max_attempts: int = 2
    tool_max_attempts: int = 2
    retryable_provider_error_types: tuple[str, ...] = (
        "provider_timeout",
        "provider_unavailable",
        "rate_limit",
        "mock_transient",
    )
    retryable_tool_error_types: tuple[str, ...] = (
        "tool_execution_failed",
        "tool_timeout",
    )
    retryable_tool_risk_levels: tuple[RiskLevel, ...] = (RiskLevel.READ_ONLY,)


class RunExecutionService:
    """Execute one queued or resumable run."""

    def __init__(
        self,
        *,
        provider: LLMProvider | None = None,
        router: ModelRouter | None = None,
        tool_registry: ToolRegistry | None = None,
        tool_executor: ToolExecutor | None = None,
        policy_evaluator: ToolPolicyEvaluator | None = None,
        memory_retrieval_service: MemoryRetrievalService | None = None,
        retry_policy: RetryPolicy | None = None,
        default_model: str = "mock:mock-default",
        state_machine: RunStateMachine | None = None,
    ) -> None:
        self._router: ModelRouter | None
        if router is not None:
            self._router = router
        elif provider is not None:
            self._router = ModelRouter({provider.name: provider})
        else:
            self._router = None
        self._tool_registry = tool_registry or create_default_tool_registry()
        self._tool_executor = tool_executor or ToolExecutor(registry=self._tool_registry)
        self._policy_evaluator = policy_evaluator or ToolPolicyEvaluator()
        self._memory_retrieval_service = memory_retrieval_service or MemoryRetrievalService()
        self._retry_policy = retry_policy or RetryPolicy()
        self._default_model = default_model
        self._state_machine = state_machine or RunStateMachine()

    async def execute(self, *, run_id: UUID, repository: RunRepository) -> Run:
        run = repository.get(run_id)
        if run is None:
            raise RunNotFoundError(f"Run {run_id} was not found.")

        start_transition = self._state_machine.start(run)
        running = repository.apply_transition(
            run_id=run.id,
            status=start_transition.to_status,
            event_type=start_transition.event_type,
            payload={
                "from_status": start_transition.from_status.value,
                "to_status": start_transition.to_status.value,
            },
        )
        if running is None:
            raise RunNotFoundError(f"Run {run_id} was not found.")

        try:
            tool_request = _explicit_tool_request_from_run(running)
        except (RunExecutionError, ValueError) as error:
            return self._fail_running_run(
                running=running,
                repository=repository,
                error_type=type(error).__name__,
                error_message=str(error),
            )

        if tool_request is not None:
            return await self._execute_explicit_tool_request(
                running=running,
                request=tool_request,
                repository=repository,
                tool_call_repository=ToolCallRepository(repository.session),
                approval_repository=ApprovalRepository(repository.session),
            )

        return await self._execute_model_request(running=running, repository=repository)

    async def resume(
        self,
        *,
        run_id: UUID,
        repository: RunRepository,
        approval_repository: ApprovalRepository,
        tool_call_repository: ToolCallRepository,
        approval_id: UUID | None = None,
    ) -> Run:
        run = repository.get(run_id)
        if run is None:
            raise RunNotFoundError(f"Run {run_id} was not found.")
        if run.status is not RunStatus.WAITING_APPROVAL:
            raise RunExecutionError(
                f"Run {run.id} is {run.status.value}; only waiting_approval runs can resume."
            )

        approval = _resolve_resume_approval(
            run_id=run.id,
            approval_id=approval_id,
            approval_repository=approval_repository,
        )
        if approval.status is ApprovalStatus.REQUESTED:
            raise RunExecutionError(f"Approval {approval.id} has not been decided yet.")
        if approval.status is ApprovalStatus.REJECTED:
            return self._fail_waiting_run_for_rejected_approval(
                waiting=run,
                repository=repository,
                approval=approval,
            )
        if approval.status is not ApprovalStatus.APPROVED:
            raise RunExecutionError(
                f"Approval {approval.id} has unsupported status {approval.status.value}."
            )

        resume_transition = self._state_machine.resume(run)
        resuming = repository.apply_transition(
            run_id=run.id,
            status=resume_transition.to_status,
            event_type=resume_transition.event_type,
            payload={
                "from_status": resume_transition.from_status.value,
                "to_status": resume_transition.to_status.value,
                "approval_id": str(approval.id),
                "tool_call_id": str(approval.tool_call_id),
            },
        )
        if resuming is None:
            raise RunNotFoundError(f"Run {run_id} was not found.")

        start_transition = self._state_machine.start(resuming)
        running = repository.apply_transition(
            run_id=run.id,
            status=start_transition.to_status,
            event_type=start_transition.event_type,
            payload={
                "from_status": start_transition.from_status.value,
                "to_status": start_transition.to_status.value,
                "approval_id": str(approval.id),
                "tool_call_id": str(approval.tool_call_id),
            },
        )
        if running is None:
            raise RunNotFoundError(f"Run {run_id} was not found.")

        tool_call = tool_call_repository.get(approval.tool_call_id)
        if tool_call is None:
            return self._fail_running_run(
                running=running,
                repository=repository,
                error_type="missing_tool_call",
                error_message=f"Tool call {approval.tool_call_id} was not found.",
            )
        if tool_call.run_id != run.id:
            return self._fail_running_run(
                running=running,
                repository=repository,
                error_type="approval_run_mismatch",
                error_message=f"Approval {approval.id} does not belong to run {run.id}.",
            )

        return await self._execute_approved_tool_call(
            running=running,
            approval=approval,
            tool_call=tool_call,
            repository=repository,
            tool_call_repository=tool_call_repository,
        )

    async def _execute_model_request(self, *, running: Run, repository: RunRepository) -> Run:
        try:
            memory_context = self._memory_context_from_run(
                running=running,
                repository=repository,
            )
            request = _request_from_run(
                running,
                default_model=self._default_model,
                memory_context=memory_context,
            )
            if self._router is None:
                raise RunExecutionError("Model execution requires a provider or router.")
            model_refs = _model_refs_from_run(running, default_model=self._default_model)
        except (RunExecutionError, ValueError) as error:
            return self._fail_running_run(
                running=running,
                repository=repository,
                error_type=type(error).__name__,
                error_message=str(error),
            )

        last_error: LLMProviderError | None = None
        last_provider: str | None = None
        attempt_count = 0
        for model_index, model_ref in enumerate(model_refs):
            try:
                route = self._router.route(model_ref)
            except ValueError as error:
                return self._fail_running_run(
                    running=running,
                    repository=repository,
                    error_type=type(error).__name__,
                    error_message=str(error),
                )

            routed_request = request.model_copy(update={"model": route.model})
            for attempt in range(1, self._retry_policy.provider_max_attempts + 1):
                attempt_count += 1
                try:
                    response = await route.provider.complete(routed_request)
                except LLMProviderError as error:
                    last_error = error
                    last_provider = route.provider_name
                    if self._should_retry_provider(error) and (
                        attempt < self._retry_policy.provider_max_attempts
                    ):
                        repository.append_event(
                            run_id=running.id,
                            event_type=RunEventType.MODEL_CALL_RETRYING,
                            payload={
                                "provider": route.provider_name,
                                "model": route.model,
                                "model_ref": model_ref,
                                "attempt": attempt + 1,
                                "max_attempts": self._retry_policy.provider_max_attempts,
                                "error_type": error.error_type,
                                "error_message": str(error),
                            },
                            trace_id=running.trace_id,
                        )
                        continue
                    break
                return self._complete_model_run(
                    running=running,
                    repository=repository,
                    response=response,
                    provider=route.provider_name,
                    model_ref=model_ref,
                    attempt_count=attempt_count,
                    fallback_used=model_index > 0,
                    memory_context=memory_context,
                )

            if last_error is not None and not self._should_retry_provider(last_error):
                break

            next_model_ref = _next_model_ref(model_refs=model_refs, current_index=model_index)
            if next_model_ref is not None and last_error is not None:
                repository.append_event(
                    run_id=running.id,
                    event_type=RunEventType.MODEL_FALLBACK_SELECTED,
                    payload={
                        "from_model": model_ref,
                        "to_model": next_model_ref,
                        "error_type": last_error.error_type,
                        "error_message": str(last_error),
                    },
                    trace_id=running.trace_id,
                )

        if last_error is None:
            return self._fail_running_run(
                running=running,
                repository=repository,
                error_type="model_execution_failed",
                error_message="Model execution failed without a provider error.",
            )
        return self._fail_running_run(
            running=running,
            repository=repository,
            error_type=last_error.error_type,
            error_message=str(last_error),
            provider=last_provider,
        )

    def _complete_model_run(
        self,
        *,
        running: Run,
        repository: RunRepository,
        response: LLMResponse,
        provider: str,
        model_ref: str,
        attempt_count: int,
        fallback_used: bool,
        memory_context: MemoryContext | None,
    ) -> Run:
        succeed_transition = self._state_machine.succeed(running)
        output_payload: dict[str, Any] = {
            "text": response.text,
            "provider": response.provider,
            "model": response.model,
            "usage": response.usage.model_dump(),
        }
        if memory_context is not None:
            output_payload["memory"] = memory_context.to_output_payload()

        completed = repository.complete(
            run_id=running.id,
            output_payload=output_payload,
            input_tokens_total=response.usage.input_tokens,
            output_tokens_total=response.usage.output_tokens,
            estimated_cost_total=response.usage.estimated_cost,
            event_payload={
                "from_status": succeed_transition.from_status.value,
                "to_status": succeed_transition.to_status.value,
                "provider": response.provider,
                "model": response.model,
                "model_ref": model_ref,
                "attempt_count": attempt_count,
                "fallback_used": fallback_used,
            },
        )
        if completed is None:
            raise RunNotFoundError(f"Run {running.id} was not found.")
        return completed

    def _memory_context_from_run(
        self,
        *,
        running: Run,
        repository: RunRepository,
    ) -> MemoryContext | None:
        memory_request = _explicit_memory_request_from_run(running)
        if memory_request is None:
            return None

        memory_context = self._memory_retrieval_service.retrieve(
            repository=MemoryRepository(repository.session),
            scopes=memory_request.scopes,
            types=memory_request.types,
            limit=memory_request.limit,
        )
        repository.append_event(
            run_id=running.id,
            event_type=RunEventType.MEMORY_RETRIEVED,
            payload={
                **memory_context.to_event_payload(),
                "requested_scopes": list(memory_request.scopes),
                "requested_types": (
                    [memory_type.value for memory_type in memory_request.types]
                    if memory_request.types is not None
                    else None
                ),
                "limit": memory_request.limit,
            },
            trace_id=running.trace_id,
        )
        return memory_context

    async def _execute_explicit_tool_request(
        self,
        *,
        running: Run,
        request: ExplicitToolRequest,
        repository: RunRepository,
        tool_call_repository: ToolCallRepository,
        approval_repository: ApprovalRepository,
    ) -> Run:
        try:
            tool = self._tool_registry.get(request.name)
        except ToolError as error:
            return self._fail_running_run(
                running=running,
                repository=repository,
                error_type=error.error_type,
                error_message=str(error),
            )

        tool_call = tool_call_repository.create_requested(
            run_id=running.id,
            tool_name=request.name,
            arguments=request.arguments,
            risk_level=tool.metadata.risk_level,
            trace_id=running.trace_id,
        )
        if tool_call is None:
            raise RunNotFoundError(f"Run {running.id} was not found.")

        decision = self._policy_evaluator.evaluate(tool.metadata)
        if decision.decision is PolicyDecisionType.DENY:
            tool_call_repository.record_policy_decision(
                tool_call_id=tool_call.id,
                decision=decision.decision.value,
                reason=decision.reason,
                status=ToolCallStatus.DENIED,
            )
            return self._fail_running_run(
                running=running,
                repository=repository,
                error_type="tool_denied",
                error_message=decision.reason,
            )

        if decision.decision is PolicyDecisionType.REQUIRE_APPROVAL:
            waiting_tool_call = tool_call_repository.record_policy_decision(
                tool_call_id=tool_call.id,
                decision=decision.decision.value,
                reason=decision.reason,
                status=ToolCallStatus.WAITING_APPROVAL,
                requires_approval=True,
            )
            if waiting_tool_call is None:
                raise RunExecutionError(f"Tool call {tool_call.id} was not found.")
            approval = approval_repository.create_requested(
                tool_call_id=waiting_tool_call.id,
                reason=decision.reason,
            )
            if approval is None:
                raise RunExecutionError(f"Approval could not be created for {tool_call.id}.")

            wait_transition = self._state_machine.wait_for_approval(running)
            waiting = repository.apply_transition(
                run_id=running.id,
                status=wait_transition.to_status,
                event_type=wait_transition.event_type,
                payload={
                    "from_status": wait_transition.from_status.value,
                    "to_status": wait_transition.to_status.value,
                    "approval_id": str(approval.id),
                    "tool_call_id": str(waiting_tool_call.id),
                    "tool_name": waiting_tool_call.tool_name,
                    "reason": decision.reason,
                },
            )
            if waiting is None:
                raise RunNotFoundError(f"Run {running.id} was not found.")
            return waiting

        checked_tool_call = tool_call_repository.record_policy_decision(
            tool_call_id=tool_call.id,
            decision=decision.decision.value,
            reason=decision.reason,
            status=ToolCallStatus.POLICY_CHECKED,
        )
        if checked_tool_call is None:
            raise RunExecutionError(f"Tool call {tool_call.id} was not found.")
        return await self._execute_approved_tool_call(
            running=running,
            approval=None,
            tool_call=checked_tool_call,
            repository=repository,
            tool_call_repository=tool_call_repository,
        )

    async def _execute_approved_tool_call(
        self,
        *,
        running: Run,
        approval: Approval | None,
        tool_call: ToolCall,
        repository: RunRepository,
        tool_call_repository: ToolCallRepository,
    ) -> Run:
        running_tool_call = tool_call_repository.mark_running(tool_call_id=tool_call.id)
        if running_tool_call is None:
            raise RunExecutionError(f"Tool call {tool_call.id} was not found.")

        try:
            result = await self._execute_tool_with_retry(
                running=running,
                repository=repository,
                tool_call=running_tool_call,
            )
        except ToolError as error:
            tool_call_repository.fail(
                tool_call_id=running_tool_call.id,
                error_type=error.error_type,
                error_message=str(error),
            )
            return self._fail_running_run(
                running=running,
                repository=repository,
                error_type=error.error_type,
                error_message=str(error),
            )

        completed_tool_call = tool_call_repository.complete(
            tool_call_id=running_tool_call.id,
            result=result.output,
        )
        if completed_tool_call is None:
            raise RunExecutionError(f"Tool call {running_tool_call.id} was not found.")

        succeed_transition = self._state_machine.succeed(running)
        completed = repository.complete(
            run_id=running.id,
            output_payload={
                "tool": {
                    "tool_call_id": str(completed_tool_call.id),
                    "approval_id": str(approval.id) if approval is not None else None,
                    "name": completed_tool_call.tool_name,
                    "result": completed_tool_call.result,
                }
            },
            input_tokens_total=0,
            output_tokens_total=0,
            estimated_cost_total=0.0,
            event_payload={
                "from_status": succeed_transition.from_status.value,
                "to_status": succeed_transition.to_status.value,
                "tool_call_id": str(completed_tool_call.id),
                "approval_id": str(approval.id) if approval is not None else None,
            },
        )
        if completed is None:
            raise RunNotFoundError(f"Run {running.id} was not found.")
        return completed

    async def _execute_tool_with_retry(
        self,
        *,
        running: Run,
        repository: RunRepository,
        tool_call: ToolCall,
    ) -> Any:
        request = ToolRequest(tool_name=tool_call.tool_name, arguments=tool_call.arguments)
        for attempt in range(1, self._retry_policy.tool_max_attempts + 1):
            try:
                return await self._tool_executor.execute(request)
            except ToolError as error:
                if self._should_retry_tool(error, tool_call) and (
                    attempt < self._retry_policy.tool_max_attempts
                ):
                    repository.append_event(
                        run_id=running.id,
                        event_type=RunEventType.TOOL_CALL_RETRYING,
                        payload={
                            "tool_call_id": str(tool_call.id),
                            "tool_name": tool_call.tool_name,
                            "attempt": attempt + 1,
                            "max_attempts": self._retry_policy.tool_max_attempts,
                            "error_type": error.error_type,
                            "error_message": str(error),
                        },
                        trace_id=tool_call.trace_id,
                    )
                    continue
                raise

        raise RunExecutionError("Tool retry loop exited without a result or error.")

    def _should_retry_provider(self, error: LLMProviderError) -> bool:
        return error.error_type in self._retry_policy.retryable_provider_error_types

    def _should_retry_tool(self, error: ToolError, tool_call: ToolCall) -> bool:
        return (
            error.error_type in self._retry_policy.retryable_tool_error_types
            and tool_call.risk_level in self._retry_policy.retryable_tool_risk_levels
            and not tool_call.requires_approval
        )

    def _fail_running_run(
        self,
        *,
        running: Run,
        repository: RunRepository,
        error_type: str,
        error_message: str,
        provider: str | None = None,
    ) -> Run:
        fail_transition = self._state_machine.fail(running)
        event_payload = {
            "from_status": fail_transition.from_status.value,
            "to_status": fail_transition.to_status.value,
            "error_type": error_type,
            "error_message": error_message,
        }
        if provider is not None:
            event_payload["provider"] = provider

        failed = repository.fail(
            run_id=running.id,
            error_type=error_type,
            error_message=error_message,
            event_payload=event_payload,
        )
        if failed is None:
            raise RunNotFoundError(f"Run {running.id} was not found.")
        return failed

    def _fail_waiting_run_for_rejected_approval(
        self,
        *,
        waiting: Run,
        repository: RunRepository,
        approval: Approval,
    ) -> Run:
        fail_transition = self._state_machine.fail(waiting)
        failed = repository.fail(
            run_id=waiting.id,
            error_type="approval_rejected",
            error_message=approval.decision_note or f"Approval {approval.id} was rejected.",
            event_payload={
                "from_status": fail_transition.from_status.value,
                "to_status": fail_transition.to_status.value,
                "approval_id": str(approval.id),
                "tool_call_id": str(approval.tool_call_id),
                "error_type": "approval_rejected",
                "error_message": approval.decision_note,
            },
        )
        if failed is None:
            raise RunNotFoundError(f"Run {waiting.id} was not found.")
        return failed


def _request_from_run(
    run: Run,
    *,
    default_model: str,
    memory_context: MemoryContext | None = None,
) -> LLMRequest:
    model = _string_from_input(run.input, "model", default_model)
    messages = _messages_from_input(run.input)
    if memory_context is not None:
        messages = (
            LLMMessage(
                role=MessageRole.SYSTEM,
                content=memory_context.to_prompt_text(),
                name="memory_context",
                metadata={"memory_item_ids": [str(item_id) for item_id in memory_context.item_ids]},
            ),
            *messages,
        )
    return LLMRequest(
        model=model,
        messages=messages,
        metadata={"run_id": str(run.id), "agent_id": str(run.agent_id)},
    )


def _model_refs_from_run(run: Run, *, default_model: str) -> tuple[str, ...]:
    primary_model = _string_from_input(run.input, "model", default_model)
    raw_fallback_models = run.input.get("fallback_models", [])
    if not isinstance(raw_fallback_models, list):
        raise RunExecutionError("Run input field 'fallback_models' must be a list of strings.")

    fallback_models: list[str] = []
    for index, value in enumerate(raw_fallback_models):
        if not isinstance(value, str) or value == "":
            raise RunExecutionError(
                f"Run input field 'fallback_models[{index}]' must be a non-empty string."
            )
        if value != primary_model and value not in fallback_models:
            fallback_models.append(value)

    return (primary_model, *fallback_models)


def _next_model_ref(*, model_refs: tuple[str, ...], current_index: int) -> str | None:
    next_index = current_index + 1
    if next_index >= len(model_refs):
        return None
    return model_refs[next_index]


def _explicit_tool_request_from_run(run: Run) -> ExplicitToolRequest | None:
    raw_tool = run.input.get("tool")
    if raw_tool is None:
        return None
    if not isinstance(raw_tool, dict):
        raise RunExecutionError("Run input field 'tool' must be a JSON object.")

    raw_name = raw_tool.get("name")
    if not isinstance(raw_name, str) or raw_name == "":
        raise RunExecutionError("Run input field 'tool.name' must be a non-empty string.")

    raw_arguments = raw_tool.get("arguments", {})
    if not isinstance(raw_arguments, dict):
        raise RunExecutionError("Run input field 'tool.arguments' must be a JSON object.")

    return ExplicitToolRequest(name=raw_name, arguments=raw_arguments)


def _explicit_memory_request_from_run(run: Run) -> ExplicitMemoryRequest | None:
    raw_memory = run.input.get("memory")
    if raw_memory is None:
        return None
    if not isinstance(raw_memory, dict):
        raise RunExecutionError("Run input field 'memory' must be a JSON object.")

    raw_scopes = raw_memory.get("scopes")
    if not isinstance(raw_scopes, list) or not raw_scopes:
        raise RunExecutionError("Run input field 'memory.scopes' must be a non-empty list.")
    scopes: list[str] = []
    for index, scope in enumerate(raw_scopes):
        if not isinstance(scope, str) or scope == "":
            raise RunExecutionError(
                f"Run input field 'memory.scopes[{index}]' must be a non-empty string."
            )
        scopes.append(scope)

    raw_types = raw_memory.get("types")
    memory_types: list[MemoryType] | None = None
    if raw_types is not None:
        if not isinstance(raw_types, list):
            raise RunExecutionError("Run input field 'memory.types' must be a list.")
        memory_types = []
        for index, raw_type in enumerate(raw_types):
            if not isinstance(raw_type, str):
                raise RunExecutionError(
                    f"Run input field 'memory.types[{index}]' must be a string."
                )
            try:
                memory_types.append(MemoryType(raw_type))
            except ValueError as error:
                raise RunExecutionError(
                    f"Run input field 'memory.types[{index}]' has unsupported value {raw_type!r}."
                ) from error

    raw_limit = raw_memory.get("limit", 10)
    if not isinstance(raw_limit, int) or raw_limit < 1:
        raise RunExecutionError("Run input field 'memory.limit' must be an integer >= 1.")

    return ExplicitMemoryRequest(
        scopes=tuple(scopes),
        types=tuple(memory_types) if memory_types is not None else None,
        limit=raw_limit,
    )


def _resolve_resume_approval(
    *,
    run_id: UUID,
    approval_id: UUID | None,
    approval_repository: ApprovalRepository,
) -> Approval:
    if approval_id is not None:
        approval = approval_repository.get(approval_id)
        if approval is None:
            raise RunExecutionError(f"Approval {approval_id} was not found.")
        if approval.run_id != run_id:
            raise RunExecutionError(f"Approval {approval_id} does not belong to run {run_id}.")
        return approval

    approvals = approval_repository.list_for_run(run_id)
    if not approvals:
        raise RunExecutionError(f"Run {run_id} has no approval to resume from.")
    return approvals[-1]


def _messages_from_input(input_payload: dict[str, Any]) -> tuple[LLMMessage, ...]:
    raw_messages = input_payload.get("messages")
    if isinstance(raw_messages, list):
        return tuple(_message_from_mapping(item) for item in raw_messages)

    task = input_payload.get("task")
    if isinstance(task, str):
        return (LLMMessage(role=MessageRole.USER, content=task),)

    return (
        LLMMessage(
            role=MessageRole.USER,
            content=json.dumps(input_payload, sort_keys=True),
        ),
    )


def _message_from_mapping(value: object) -> LLMMessage:
    if not isinstance(value, dict):
        raise RunExecutionError("Run input messages must be JSON objects.")

    role = value.get("role", MessageRole.USER.value)
    content = value.get("content")
    if not isinstance(content, str):
        raise RunExecutionError("Run input message content must be a string.")

    return LLMMessage(role=MessageRole(str(role)), content=content)


def _string_from_input(input_payload: dict[str, Any], key: str, default: str) -> str:
    value = input_payload.get(key, default)
    if not isinstance(value, str):
        raise RunExecutionError(f"Run input field {key!r} must be a string.")
    return value
