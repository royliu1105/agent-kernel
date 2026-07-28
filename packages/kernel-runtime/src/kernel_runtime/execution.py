"""Single-run deterministic execution service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from kernel_core import Approval, ApprovalStatus, Run, RunStatus, ToolCall, ToolCallStatus
from kernel_policy import PolicyDecisionType, ToolPolicyEvaluator
from kernel_providers import LLMMessage, LLMProvider, LLMProviderError, LLMRequest, MessageRole
from kernel_storage import ApprovalRepository, RunRepository, ToolCallRepository
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
            request = _request_from_run(running, default_model=self._default_model)
            if self._router is None:
                raise RunExecutionError("Model execution requires a provider or router.")
            route = self._router.route(request.model)
        except (RunExecutionError, ValueError) as error:
            return self._fail_running_run(
                running=running,
                repository=repository,
                error_type=type(error).__name__,
                error_message=str(error),
            )

        routed_request = request.model_copy(update={"model": route.model})
        try:
            response = await route.provider.complete(routed_request)
        except LLMProviderError as error:
            return self._fail_running_run(
                running=running,
                repository=repository,
                error_type=error.error_type,
                error_message=str(error),
                provider=route.provider_name,
            )

        succeed_transition = self._state_machine.succeed(running)
        completed = repository.complete(
            run_id=running.id,
            output_payload={
                "text": response.text,
                "provider": response.provider,
                "model": response.model,
                "usage": response.usage.model_dump(),
            },
            input_tokens_total=response.usage.input_tokens,
            output_tokens_total=response.usage.output_tokens,
            estimated_cost_total=response.usage.estimated_cost,
            event_payload={
                "from_status": succeed_transition.from_status.value,
                "to_status": succeed_transition.to_status.value,
                "provider": response.provider,
                "model": response.model,
            },
        )
        if completed is None:
            raise RunNotFoundError(f"Run {running.id} was not found.")
        return completed

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
            result = await self._tool_executor.execute(
                ToolRequest(
                    tool_name=running_tool_call.tool_name,
                    arguments=running_tool_call.arguments,
                )
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


def _request_from_run(run: Run, *, default_model: str) -> LLMRequest:
    model = _string_from_input(run.input, "model", default_model)
    return LLMRequest(
        model=model,
        messages=_messages_from_input(run.input),
        metadata={"run_id": str(run.id), "agent_id": str(run.agent_id)},
    )


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
