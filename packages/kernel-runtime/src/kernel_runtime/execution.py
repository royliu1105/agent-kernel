"""Single-run deterministic execution service."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from kernel_core import Run
from kernel_providers import LLMMessage, LLMProvider, LLMProviderError, LLMRequest, MessageRole
from kernel_storage import RunRepository

from kernel_runtime.router import ModelRouter
from kernel_runtime.state_machine import RunStateMachine


class RunExecutionError(RuntimeError):
    """Raised when a run cannot be executed."""


class RunNotFoundError(RunExecutionError):
    """Raised when execution is requested for a missing run."""


class RunExecutionService:
    """Execute one queued run with one provider call."""

    def __init__(
        self,
        *,
        provider: LLMProvider | None = None,
        router: ModelRouter | None = None,
        default_model: str = "mock:mock-default",
        state_machine: RunStateMachine | None = None,
    ) -> None:
        if router is None and provider is None:
            raise ValueError("RunExecutionService requires a provider or router.")
        if router is not None:
            self._router = router
        elif provider is not None:
            self._router = ModelRouter({provider.name: provider})
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
            request = _request_from_run(running, default_model=self._default_model)
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
            raise RunNotFoundError(f"Run {run_id} was not found.")
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


def _request_from_run(run: Run, *, default_model: str) -> LLMRequest:
    model = _string_from_input(run.input, "model", default_model)
    return LLMRequest(
        model=model,
        messages=_messages_from_input(run.input),
        metadata={"run_id": str(run.id), "agent_id": str(run.agent_id)},
    )


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
