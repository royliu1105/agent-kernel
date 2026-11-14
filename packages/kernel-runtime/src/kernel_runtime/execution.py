"""Single-run deterministic execution service."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import random
from collections.abc import Awaitable, Callable
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass
from time import monotonic
from typing import Any
from uuid import UUID, uuid4

from kernel_core import (
    Approval,
    ApprovalStatus,
    RiskLevel,
    Run,
    RunEventType,
    RunStatus,
    ToolCall,
    ToolCallStatus,
)
from kernel_core.models import MemorySelection
from kernel_memory import MemoryContext, MemoryRetrievalService
from kernel_memory.retrieval import MEMORY_CONTEXT_POLICY, MEMORY_CONTEXT_VERSION
from kernel_observability import (
    LatencyTimer,
    MetricsRecorder,
    NoOpMetricsRecorder,
    ObservabilityContext,
    log_event,
    trace_operation,
)
from kernel_policy import PolicyDecisionType, ToolPolicyEvaluator
from kernel_providers import (
    LLMFinishReason,
    LLMMessage,
    LLMProvider,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMToolChoice,
    LLMUsage,
    MessageRole,
)
from kernel_storage import (
    ApprovalRepository,
    ExecutionOwnershipError,
    MemoryRepository,
    RunRepository,
    ToolCallRepository,
    WorkerLeaseRepository,
)
from kernel_tools import (
    ToolError,
    ToolExecutionContext,
    ToolExecutor,
    ToolRegistry,
    ToolRequest,
    create_default_tool_registry,
)
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker

from kernel_runtime.native_state import (
    ExecutionBudget,
    ExecutionLimitError,
    ExecutionLimits,
    NativeState,
)
from kernel_runtime.provider_tool_calls import persist_provider_tool_calls
from kernel_runtime.provider_tools import tool_registry_to_llm_tool_definitions
from kernel_runtime.retry import RetryDelayPolicy
from kernel_runtime.router import ModelRouter
from kernel_runtime.state_machine import RunStateMachine

LOGGER = logging.getLogger(__name__)
_ABANDONED_OPERATIONS: set[asyncio.Future[Any]] = set()


def _abandon_operation(task: asyncio.Future[Any]) -> None:
    """Discard late adapter results without waiting on cancellation-resistant code."""
    _ABANDONED_OPERATIONS.add(task)

    def discard(completed: asyncio.Future[Any]) -> None:
        _ABANDONED_OPERATIONS.discard(completed)
        with suppress(asyncio.CancelledError, Exception):
            completed.exception()

    task.add_done_callback(discard)
    task.cancel()


class RunExecutionError(RuntimeError):
    """Raised when a run cannot be executed."""


class RunNotFoundError(RunExecutionError):
    """Raised when execution is requested for a missing run."""


class RunAlreadyClaimedError(RunExecutionError):
    """Another executor owns the run, or its state no longer permits execution."""


@dataclass(frozen=True)
class ExplicitToolRequest:
    """A tool request embedded directly in run input."""

    name: str
    arguments: dict[str, Any]


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
        metrics_recorder: MetricsRecorder | None = None,
        retry_policy: RetryPolicy | None = None,
        default_model: str = "mock:mock-default",
        state_machine: RunStateMachine | None = None,
        lease_ttl_seconds: int = 60,
        execution_limits: ExecutionLimits | None = None,
        retry_delay_policy: RetryDelayPolicy | None = None,
        retry_sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        retry_random: Callable[[], float] = random.random,
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
        self._metrics_recorder = metrics_recorder or NoOpMetricsRecorder()
        self._retry_policy = retry_policy or RetryPolicy()
        self._execution_limits = execution_limits or ExecutionLimits.from_env()
        self._retry_delay_policy = retry_delay_policy or RetryDelayPolicy()
        self._retry_sleep = retry_sleep
        self._retry_random = retry_random
        self._default_model = default_model
        self._state_machine = state_machine or RunStateMachine()
        if lease_ttl_seconds < 1:
            raise ValueError("Lease TTL must be at least one second.")
        self._lease_ttl_seconds = lease_ttl_seconds
        self._worker_id = f"executor-{uuid4()}"

    async def execute(self, *, run_id: UUID, repository: RunRepository) -> Run:
        return await self._with_lease(
            run_id=run_id,
            repository=repository,
            expected_status=RunStatus.QUEUED,
            operation=lambda owned: self._execute_claimed(run_id=run_id, repository=owned),
        )

    async def resume(
        self,
        *,
        run_id: UUID,
        repository: RunRepository,
        approval_repository: ApprovalRepository,
        tool_call_repository: ToolCallRepository,
        approval_id: UUID | None = None,
    ) -> Run:
        return await self._with_lease(
            run_id=run_id,
            repository=repository,
            expected_status=RunStatus.WAITING_APPROVAL,
            operation=lambda owned: self._resume_claimed(
                run_id=run_id,
                repository=owned,
                approval_id=approval_id,
                approval_repository=ApprovalRepository(
                    owned.session,
                    lease_token=owned.lease_token,
                ),
                tool_call_repository=ToolCallRepository(
                    owned.session,
                    lease_token=owned.lease_token,
                ),
            ),
        )

    async def _with_lease(
        self,
        *,
        run_id: UUID,
        repository: RunRepository,
        expected_status: RunStatus,
        operation: Callable[[RunRepository], Awaitable[Run]],
    ) -> Run:
        existing = repository.get(run_id)
        if existing is None:
            raise RunNotFoundError(f"Run {run_id} was not found.")
        if existing.status is not expected_status:
            if expected_status is RunStatus.QUEUED:
                self._state_machine.start(existing)
            raise RunExecutionError(
                f"Run {run_id} is {existing.status.value}; only waiting_approval runs can resume."
            )
        lease = WorkerLeaseRepository(repository.session).acquire(
            run_id=run_id,
            worker_id=self._worker_id,
            ttl_seconds=self._lease_ttl_seconds,
            expected_status=expected_status,
        )
        if lease is None:
            repository.session.rollback()
            raise RunAlreadyClaimedError("Run is already claimed or no longer executable.")
        owned = RunRepository(repository.session, lease_token=lease.lease_token)
        factory = sessionmaker(bind=repository.session.get_bind(), expire_on_commit=False)

        async def heartbeat() -> None:
            while True:
                await asyncio.sleep(self._lease_ttl_seconds / 3)
                with factory() as session:
                    renewed = WorkerLeaseRepository(session).heartbeat(
                        lease_token=lease.lease_token,
                        ttl_seconds=self._lease_ttl_seconds,
                    )
                    if renewed is None:
                        raise ExecutionOwnershipError("Execution lease could not be renewed.")

        async def traced_operation() -> Run:
            with trace_operation(
                "agent.run",
                trace_id=existing.trace_id,
                attributes={"run_id": str(run_id)},
            ) as span:
                result = await operation(owned)
                if span is not None:
                    span.set_attribute("status", result.status.value)
                    if result.status is RunStatus.FAILED:
                        from opentelemetry.trace import StatusCode

                        span.set_status(StatusCode.ERROR)
                        span.add_event(
                            "agent.run.failed", {"error.type": result.error_type or "unknown"}
                        )
                return result

        work = asyncio.create_task(traced_operation())
        pulse = asyncio.create_task(heartbeat())
        started = monotonic()
        mode = "execute" if expected_status is RunStatus.QUEUED else "resume"
        outcome = "error"
        with suppress(Exception):
            self._metrics_recorder.increment(
                "agent_run_segments_started_total", labels={"execution_mode": mode}
            )
        try:
            done, _ = await asyncio.wait({work, pulse}, return_when=asyncio.FIRST_COMPLETED)
            if pulse in done:
                await pulse
            result = await work
            outcome = result.status.value
            return result
        except asyncio.CancelledError:
            outcome = "canceled"
            raise
        finally:
            labels = {"execution_mode": mode, "outcome": outcome}
            # A custom metrics sink must never prevent lease fencing/cleanup.
            with suppress(Exception):
                self._metrics_recorder.increment("agent_run_segments_total", labels=labels)
                self._metrics_recorder.observe(
                    "agent_run_segment_latency_ms", (monotonic() - started) * 1000, labels=labels
                )
            # Fence before canceling: a provider/tool may suppress CancelledError
            # and return a late result. Keep the expired lease for recovery.
            pulse.cancel()
            owned.revoke_local_ownership()
            repository.session.rollback()
            try:
                with factory() as session:
                    WorkerLeaseRepository(session).invalidate(lease_token=lease.lease_token)
            finally:
                work.cancel()
                await asyncio.gather(work, pulse, return_exceptions=True)
                repository.session.rollback()
            with factory() as session:
                current = RunRepository(session).get(run_id)
                if current is not None and current.status not in {
                    RunStatus.RUNNING,
                    RunStatus.RESUMING,
                }:
                    WorkerLeaseRepository(session).release(lease_token=lease.lease_token)

    async def _execute_claimed(self, *, run_id: UUID, repository: RunRepository) -> Run:
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
        log_event(
            LOGGER,
            level=logging.INFO,
            event="agent.run.started",
            context=_context_from_run(running),
            status=running.status.value,
        )

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
                tool_call_repository=ToolCallRepository(
                    repository.session,
                    lease_token=repository.lease_token,
                ),
                approval_repository=ApprovalRepository(
                    repository.session,
                    lease_token=repository.lease_token,
                ),
            )

        return await self._execute_model_request(running=running, repository=repository)

    async def _resume_claimed(
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
        pending_tool = tool_call_repository.get(approval.tool_call_id)
        if pending_tool is None or pending_tool.run_id != run.id:
            raise RunExecutionError("Approval has no matching run tool call.")
        state: NativeState | None = None
        checkpoint = repository.load_execution_checkpoint(run.id)
        if checkpoint is not None:
            try:
                state = NativeState.model_validate(checkpoint)
                if state.run_id != run.id or state.response is None:
                    raise ValueError("Invalid checkpoint identity.")
                if not 0 <= state.next_tool_index < len(state.pending_tool_ids):
                    raise ValueError("Invalid checkpoint cursor.")
            except ValueError:
                return self._fail_running_run(
                    running=run,
                    repository=repository,
                    error_type="invalid_execution_checkpoint",
                    error_message="Invalid saved continuation; review and create a new run.",
                )
            try:
                state.validate_memory_context(run)
            except ValueError:
                return self._fail_running_run(
                    running=run,
                    repository=repository,
                    error_type="unsupported_memory_checkpoint",
                    error_message=(
                        "Saved memory context is legacy or invalid; review and create a new run."
                    ),
                )
            if state.pending_tool_ids[state.next_tool_index] != approval.tool_call_id:
                raise RunExecutionError("Approval does not match the pending checkpoint call.")
        if pending_tool.status is not ToolCallStatus.WAITING_APPROVAL:
            raise RunExecutionError("Approval no longer matches a waiting tool call.")
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

        if pending_tool.provider_name is not None and state is None:
            return self._fail_running_run(
                running=run,
                repository=repository,
                error_type="missing_execution_checkpoint",
                error_message=(
                    "Legacy native approval has no saved history; create a reviewed new run."
                ),
            )
        continuation_provider: LLMProvider | None = None
        if state is not None:
            try:
                if self._router is None:
                    raise ValueError("No provider router.")
                route = self._router.route(state.model_ref)
                if route.provider.name != state.provider_name or route.model != state.request.model:
                    raise ValueError("Route changed.")
                if self._tool_contracts() != state.tool_contracts:
                    raise ValueError("Tool configuration changed.")
                continuation_provider = route.provider
                state.limits = state.limits.tightened(self._execution_limits)
            except ValueError:
                return self._fail_running_run(
                    running=run,
                    repository=repository,
                    error_type="continuation_config_changed",
                    error_message="Saved provider or tool configuration is unavailable or changed.",
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

        if state is not None and continuation_provider is not None:
            try:
                return await self._drive_native_loop(
                    running,
                    repository,
                    ExecutionBudget(state),
                    continuation_provider,
                    approved=approval,
                )
            except (ExecutionLimitError, LLMProviderError, ToolError) as error:
                return self._fail_running_run(
                    running=running,
                    repository=repository,
                    error_type=error.error_type,
                    error_message=str(error),
                )
            except (RunExecutionError, ValueError):
                return self._fail_running_run(
                    running=running,
                    repository=repository,
                    error_type="invalid_execution_checkpoint",
                    error_message="Saved continuation is inconsistent; review before a new run.",
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
            memory = self._memory_context_from_run(running=running, repository=repository)
            request = _request_from_run(
                running, default_model=self._default_model, memory_context=memory
            ).model_copy(
                update={
                    "tools": tool_registry_to_llm_tool_definitions(self._tool_registry),
                    "tool_choice": LLMToolChoice.AUTO,
                }
            )
            if self._router is None:
                raise RunExecutionError("Model execution requires a provider or router.")
            refs = _model_refs_from_run(running, default_model=self._default_model)
            state = NativeState(
                run_id=running.id,
                limits=self._execution_limits,
                request=request,
                model_ref=refs[0],
                memory_output=memory.to_output_payload() if memory is not None else None,
                memory_context_version=MEMORY_CONTEXT_VERSION if memory is not None else None,
                tool_contracts=self._tool_contracts(),
            )
            budget = ExecutionBudget(state)
            for index, model_ref in enumerate(refs):
                route = self._router.route(model_ref)
                state.model_ref = model_ref
                state.provider_name = route.provider.name
                state.request = request.model_copy(update={"model": route.model})
                state.fallback_used = index > 0
                try:
                    await self._call_native_model(
                        running, repository, budget, route.provider, followup=False
                    )
                except LLMProviderError as error:
                    if self._should_retry_provider(error) and index + 1 < len(refs):
                        await self._pause_before_retry(
                            running=running,
                            repository=repository,
                            budget=budget,
                            attempt=self._retry_policy.provider_max_attempts,
                            event_type=RunEventType.MODEL_FALLBACK_SELECTED,
                            payload={
                                "from_model": model_ref,
                                "to_model": refs[index + 1],
                                "error_type": error.error_type,
                                "error_message": str(error),
                            },
                            retry_after_seconds=error.retry_after_seconds,
                        )
                        log_event(
                            LOGGER,
                            level=logging.WARNING,
                            event="llm.model_fallback.selected",
                            context=_context_from_run(running),
                            status=running.status.value,
                            error_type=error.error_type,
                            extra={"from_model": model_ref, "to_model": refs[index + 1]},
                        )
                        continue
                    raise
                return await self._drive_native_loop(running, repository, budget, route.provider)
            raise RunExecutionError("No model route was attempted.")
        except (ExecutionLimitError, LLMProviderError, ToolError) as error:
            return self._fail_running_run(
                running=running,
                repository=repository,
                error_type=error.error_type,
                error_message=str(error),
            )
        except (RunExecutionError, ValueError) as error:
            return self._fail_running_run(
                running=running,
                repository=repository,
                error_type=type(error).__name__,
                error_message="Invalid execution configuration or continuation state."
                if isinstance(error, ValidationError)
                else str(error),
            )

    def _tool_contracts(self) -> dict[str, str]:
        return {
            metadata.name: hashlib.sha256(metadata.model_dump_json().encode()).hexdigest()
            for metadata in self._tool_registry.list_metadata()
        }

    def _checkpoint(self, repository: RunRepository, budget: ExecutionBudget) -> None:
        budget.tick()
        repository.save_execution_checkpoint(budget.state.run_id, budget.state.serialized())

    def _check_native_budget(
        self, repository: RunRepository, budget: ExecutionBudget, *, continuation: bool = True
    ) -> Run:
        repository.assert_owned(budget.state.run_id)
        persisted = repository.get(budget.state.run_id)
        if persisted is None:
            raise RunNotFoundError("Run no longer exists.")
        budget.check(persisted, continuation=continuation)
        return persisted

    async def _await_budgeted(
        self,
        budget: ExecutionBudget | None,
        operation: Callable[[], Awaitable[Any]],
        *,
        check_after: bool = True,
    ) -> Any:
        if budget is None:
            return await operation()
        remaining = budget.remaining_seconds()
        task = asyncio.ensure_future(operation())
        try:
            done, _ = await asyncio.wait({task}, timeout=remaining)
        except BaseException:
            _abandon_operation(task)
            raise
        if not done:
            # wait_for waits indefinitely when cancellation is suppressed. This
            # task has no runtime persistence path; late results are discarded.
            _abandon_operation(task)
            raise ExecutionLimitError("active_time")
        result = task.result()
        if check_after:
            budget.remaining_seconds()
        return result

    async def _pause_before_retry(
        self,
        *,
        running: Run,
        repository: RunRepository,
        attempt: int,
        event_type: RunEventType,
        payload: dict[str, Any],
        budget: ExecutionBudget | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        if budget is not None:
            state = budget.state
            if event_type in {
                RunEventType.MODEL_CALL_RETRYING,
                RunEventType.MODEL_FALLBACK_SELECTED,
            }:
                if state.model_calls >= state.limits.max_model_calls:
                    raise ExecutionLimitError("model_calls")
            elif state.tool_calls >= state.limits.max_tool_calls:
                raise ExecutionLimitError("tool_calls")
        delay = self._retry_delay_policy.delay(
            attempt, retry_after_seconds=retry_after_seconds, random_value=self._retry_random()
        )
        if delay is None:
            raise ExecutionLimitError("retry_delay")
        if budget is not None and delay >= budget.remaining_seconds():
            raise ExecutionLimitError("active_time")
        repository.append_event(
            run_id=running.id,
            event_type=event_type,
            payload={**payload, "delay_seconds": delay},
            trace_id=running.trace_id,
        )
        await self._await_budgeted(budget, lambda: self._retry_sleep(delay))
        repository.assert_owned(running.id)
        if budget is not None:
            self._check_native_budget(repository, budget)

    async def _call_native_model(
        self,
        running: Run,
        repository: RunRepository,
        budget: ExecutionBudget,
        provider: LLMProvider,
        *,
        followup: bool,
    ) -> None:
        state = budget.state
        for attempt in range(1, self._retry_policy.provider_max_attempts + 1):
            persisted = self._check_native_budget(repository, budget)
            if state.model_calls >= state.limits.max_model_calls:
                raise ExecutionLimitError("model_calls")
            state.request = state.request.model_copy(
                update={
                    "max_output_tokens": min(
                        state.limits.max_output_tokens,
                        state.limits.max_total_tokens
                        - persisted.input_tokens_total
                        - persisted.output_tokens_total,
                    )
                }
            )
            state.model_calls += 1
            self._checkpoint(repository, budget)
            timer = LatencyTimer.start()
            try:
                with trace_operation(
                    "llm.model_call",
                    attributes={"provider": state.provider_name, "model": state.request.model},
                ):
                    response = await self._await_budgeted(
                        budget, lambda: provider.complete(state.request), check_after=False
                    )
            except LLMProviderError as error:
                latency = timer.elapsed_ms()
                state.model_latency_ms += latency
                self._record_model_failure_metrics(
                    provider=state.provider_name,
                    model=state.request.model,
                    error_type=error.error_type,
                    latency_ms=latency,
                )
                if (
                    not self._should_retry_provider(error)
                    or attempt >= self._retry_policy.provider_max_attempts
                ):
                    raise
                payload: dict[str, Any] = {
                    "provider": state.provider_name,
                    "model": state.request.model,
                    "model_ref": state.model_ref,
                    "attempt": attempt + 1,
                    "max_attempts": self._retry_policy.provider_max_attempts,
                    "error_type": error.error_type,
                    "error_message": str(error),
                }
                if followup:
                    payload["phase"] = "tool_followup"
                    if state.last_tool_summary is not None:
                        payload.update(
                            {
                                key: state.last_tool_summary[key]
                                for key in ("tool_call_id", "provider_tool_call_id")
                            }
                        )
                log_event(
                    LOGGER,
                    level=logging.WARNING,
                    event="llm.model_call.retrying",
                    context=_context_from_run(running),
                    status=running.status.value,
                    provider=state.provider_name,
                    model=state.request.model,
                    error_type=error.error_type,
                    extra={"attempt": attempt + 1, "latency_ms": latency},
                )
                await self._pause_before_retry(
                    running=running,
                    repository=repository,
                    attempt=attempt,
                    event_type=RunEventType.MODEL_CALL_RETRYING,
                    payload=payload,
                    budget=budget,
                    retry_after_seconds=error.retry_after_seconds,
                )
                continue
            latency = timer.elapsed_ms()
            state.model_latency_ms += latency
            if response.provider != state.provider_name or any(
                not math.isfinite(value) or value < 0
                for value in (
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                    response.usage.estimated_cost,
                )
            ):
                raise LLMProviderError(
                    "Invalid provider response identity or usage.",
                    error_type="invalid_provider_response",
                )
            self._record_response_usage(repository, running.id, response, latency)
            budget.remaining_seconds()
            state.response = response
            self._checkpoint(repository, budget)
            return
        raise RunExecutionError("No model attempt was permitted.")

    async def _drive_native_loop(
        self,
        running: Run,
        repository: RunRepository,
        budget: ExecutionBudget,
        provider: LLMProvider,
        *,
        approved: Approval | None = None,
    ) -> Run:
        state = budget.state
        tools = ToolCallRepository(repository.session, lease_token=repository.lease_token)
        while True:
            response = state.response
            if response is None:
                raise RunExecutionError("Continuation is missing a model response.")
            if not response.tool_calls:
                if response.finish_reason is not LLMFinishReason.STOP:
                    raise LLMProviderError(
                        "Model did not produce a terminal answer.",
                        error_type="model_incomplete_response",
                    )
                persisted = self._check_native_budget(repository, budget, continuation=False)
                extra: dict[str, Any] = {}
                if state.last_tool_summary is not None:
                    extra["provider_tool_loop"] = state.last_tool_summary
                return self._complete_model_run(
                    running=running,
                    repository=repository,
                    response=response.model_copy(
                        update={
                            "usage": LLMUsage(
                                input_tokens=persisted.input_tokens_total,
                                output_tokens=persisted.output_tokens_total,
                                estimated_cost=persisted.estimated_cost_total,
                            )
                        }
                    ),
                    provider=state.provider_name,
                    model_ref=state.model_ref,
                    attempt_count=state.model_calls,
                    fallback_used=state.fallback_used,
                    memory_context=None,
                    memory_output=state.memory_output,
                    latency_ms=state.model_latency_ms,
                    extra_output=extra,
                )
            self._check_native_budget(repository, budget)
            if state.model_calls >= state.limits.max_model_calls:
                raise ExecutionLimitError("model_calls")
            if not state.pending_tool_ids:
                ids = [item.id for item in response.tool_calls]
                if (
                    any(
                        not item.id.strip() or not item.name.strip() for item in response.tool_calls
                    )
                    or len(set(ids)) != len(ids)
                    or set(ids).intersection(state.seen_call_ids)
                ):
                    raise LLMProviderError(
                        "Native calls require unique non-empty IDs and names.",
                        error_type="invalid_native_tool_calls",
                    )
                if state.tool_calls + len(ids) > state.limits.max_tool_calls:
                    raise ExecutionLimitError("tool_calls")
                persisted_calls = persist_provider_tool_calls(
                    running=running,
                    response=response,
                    tool_call_repository=tools,
                    tool_registry=self._tool_registry,
                )
                state.pending_tool_ids = [item.id for item in persisted_calls]
                state.next_tool_index = 0
                state.seen_call_ids.extend(ids)
                self._checkpoint(repository, budget)
            if len(state.pending_tool_ids) != len(response.tool_calls):
                raise RunExecutionError("Checkpoint batch is inconsistent.")
            while state.next_tool_index < len(state.pending_tool_ids):
                self._check_native_budget(repository, budget)
                tool_call = tools.get(state.pending_tool_ids[state.next_tool_index])
                requested = response.tool_calls[state.next_tool_index]
                if (
                    tool_call is None
                    or tool_call.run_id != running.id
                    or tool_call.provider_name != state.provider_name
                    or tool_call.provider_tool_call_id != requested.id
                    or tool_call.tool_name != requested.name
                    or tool_call.arguments != requested.arguments
                ):
                    raise RunExecutionError("Checkpoint tool identity or arguments changed.")
                if tool_call.status is ToolCallStatus.SUCCEEDED:
                    state.next_tool_index += 1
                    self._checkpoint(repository, budget)
                    continue
                if tool_call.status not in {
                    ToolCallStatus.REQUESTED,
                    ToolCallStatus.WAITING_APPROVAL,
                }:
                    raise RunExecutionError("Uncertain or failed tool cannot be replayed.")
                try:
                    tool = self._tool_registry.get(tool_call.tool_name)
                except ToolError as error:
                    tools.fail(
                        tool_call_id=tool_call.id,
                        error_type=error.error_type,
                        error_message=str(error),
                    )
                    raise
                if self._tool_contracts().get(tool_call.tool_name) != state.tool_contracts.get(
                    tool_call.tool_name
                ):
                    raise RunExecutionError("Tool contract changed; create a reviewed new run.")
                decision = self._policy_evaluator.evaluate(tool.metadata)
                if decision.decision is PolicyDecisionType.DENY:
                    tools.record_policy_decision(
                        tool_call_id=tool_call.id,
                        decision=decision.decision.value,
                        reason=decision.reason,
                        status=ToolCallStatus.DENIED,
                    )
                    raise ToolError(decision.reason, error_type="tool_denied")
                if tool_call.status is ToolCallStatus.WAITING_APPROVAL:
                    if (
                        approved is None
                        or approved.tool_call_id != tool_call.id
                        or approved.id != tool_call.approval_id
                        or approved.status is not ApprovalStatus.APPROVED
                    ):
                        raise RunExecutionError(
                            "Continuation requires its pending approved decision."
                        )
                elif decision.decision is PolicyDecisionType.REQUIRE_APPROVAL:
                    return self._pause_native_approval(
                        running, repository, budget, tools, tool_call, decision.reason
                    )
                else:
                    checked = tools.record_policy_decision(
                        tool_call_id=tool_call.id,
                        decision=decision.decision.value,
                        reason=decision.reason,
                        status=ToolCallStatus.POLICY_CHECKED,
                    )
                    if checked is None:
                        raise RunExecutionError("Tool disappeared during policy evaluation.")
                    tool_call = checked
                completed = await self._execute_tool_call_only(
                    running=running,
                    repository=repository,
                    tool_call=tool_call,
                    tool_call_repository=tools,
                    approval=approved,
                    budget=budget,
                )
                approved = None
                state.last_tool_summary = {
                    "tool_call_id": str(completed.id),
                    "provider_tool_call_id": completed.provider_tool_call_id,
                    "tool_name": completed.tool_name,
                    "tool_result": completed.result,
                }
                state.next_tool_index += 1
                self._checkpoint(repository, budget)
            completed_calls = [tools.get(identity) for identity in state.pending_tool_ids]
            if any(
                item is None or item.status is not ToolCallStatus.SUCCEEDED
                for item in completed_calls
            ):
                raise RunExecutionError("A batch result is missing.")
            first = completed_calls[0]
            assert first is not None
            state.request = _request_with_tool_result(
                initial_request=state.request, initial_response=response, tool_call=first
            )
            for batch_result in completed_calls[1:]:
                assert batch_result is not None
                state.request = state.request.model_copy(
                    update={
                        "messages": (*state.request.messages, _tool_result_message(batch_result))
                    }
                )
            state.pending_tool_ids = []
            state.next_tool_index = 0
            state.response = None
            self._checkpoint(repository, budget)
            await self._call_native_model(running, repository, budget, provider, followup=True)

    def _pause_native_approval(
        self,
        running: Run,
        repository: RunRepository,
        budget: ExecutionBudget,
        tools: ToolCallRepository,
        tool_call: ToolCall,
        reason: str,
    ) -> Run:
        checked = tools.record_policy_decision(
            tool_call_id=tool_call.id,
            decision=PolicyDecisionType.REQUIRE_APPROVAL.value,
            reason=reason,
            status=ToolCallStatus.WAITING_APPROVAL,
            requires_approval=True,
        )
        if checked is None:
            raise RunExecutionError("Tool disappeared before approval.")
        approval = ApprovalRepository(
            repository.session, lease_token=repository.lease_token
        ).create_requested(tool_call_id=checked.id, reason=reason)
        if approval is None:
            raise RunExecutionError("Approval could not be created.")
        self._checkpoint(repository, budget)
        transition = self._state_machine.wait_for_approval(running)
        waiting = repository.apply_transition(
            run_id=running.id,
            status=transition.to_status,
            event_type=transition.event_type,
            payload={
                "from_status": transition.from_status.value,
                "to_status": transition.to_status.value,
                "approval_id": str(approval.id),
                "tool_call_id": str(checked.id),
                "tool_name": checked.tool_name,
                "provider": budget.state.provider_name,
                "provider_tool_call_id": checked.provider_tool_call_id,
                "reason": reason,
            },
        )
        if waiting is None:
            raise RunNotFoundError("Run disappeared before approval.")
        return waiting

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
        latency_ms: int,
        extra_output: dict[str, Any] | None = None,
        memory_output: dict[str, Any] | None = None,
    ) -> Run:
        succeed_transition = self._state_machine.succeed(running)
        output_payload: dict[str, Any] = {
            "text": response.text,
            "provider": response.provider,
            "model": response.model,
            "usage": response.usage.model_dump(),
        }
        if extra_output:
            output_payload.update(extra_output)
        if memory_context is not None:
            output_payload["memory"] = memory_context.to_output_payload()
        elif memory_output is not None:
            output_payload["memory"] = memory_output

        log_event(
            LOGGER,
            level=logging.INFO,
            event="llm.model_call.completed",
            context=_context_from_run(running),
            status=RunStatus.SUCCEEDED.value,
            provider=response.provider,
            model=response.model,
            extra={
                "latency_ms": latency_ms,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                "estimated_cost": response.usage.estimated_cost,
                "attempt_count": attempt_count,
                "fallback_used": fallback_used,
            },
        )
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
                **(extra_output or {}),
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
            repository=MemoryRepository(repository.session, workspace_id=running.workspace_id),
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
        log_event(
            LOGGER,
            level=logging.INFO,
            event="tool.call.requested",
            context=_context_from_run(running, tool_call_id=tool_call.id),
            status=tool_call.status.value,
            tool_name=tool_call.tool_name,
            extra={
                "risk_level": tool_call.risk_level.value,
                "requires_approval": tool_call.requires_approval,
            },
        )

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
            log_event(
                LOGGER,
                level=logging.INFO,
                event="approval.requested",
                context=_context_from_run(
                    running,
                    tool_call_id=waiting_tool_call.id,
                    approval_id=approval.id,
                ),
                status=approval.status.value,
                tool_name=waiting_tool_call.tool_name,
                extra={
                    "risk_level": waiting_tool_call.risk_level.value,
                    "requires_approval": waiting_tool_call.requires_approval,
                },
            )

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
        try:
            completed_tool_call = await self._execute_tool_call_only(
                running=running,
                repository=repository,
                tool_call=tool_call,
                tool_call_repository=tool_call_repository,
                approval=approval,
            )
        except (ToolError, ExecutionLimitError) as error:
            return self._fail_running_run(
                running=running,
                repository=repository,
                error_type=error.error_type,
                error_message=str(error),
            )

        return self._complete_tool_run(
            running=running,
            repository=repository,
            completed_tool_call=completed_tool_call,
            approval=approval,
        )

    async def _execute_tool_call_only(
        self,
        *,
        running: Run,
        repository: RunRepository,
        tool_call: ToolCall,
        tool_call_repository: ToolCallRepository,
        approval: Approval | None = None,
        budget: ExecutionBudget | None = None,
    ) -> ToolCall:
        running_tool_call = tool_call_repository.mark_running(tool_call_id=tool_call.id)
        if running_tool_call is None:
            raise RunExecutionError(f"Tool call {tool_call.id} was not found.")

        tool_timer = LatencyTimer.start()
        try:
            result = await self._execute_tool_with_retry(
                running=running,
                repository=repository,
                tool_call=running_tool_call,
                budget=budget,
            )
        except (ToolError, ExecutionLimitError) as error:
            latency_ms = tool_timer.elapsed_ms()
            tool_call_repository.fail(
                tool_call_id=running_tool_call.id,
                error_type=error.error_type,
                error_message=str(error),
                latency_ms=latency_ms,
            )
            self._record_tool_failure_metrics(
                tool_name=running_tool_call.tool_name,
                error_type=error.error_type,
                latency_ms=latency_ms,
            )
            raise

        latency_ms = tool_timer.elapsed_ms()
        completed_tool_call = tool_call_repository.complete(
            tool_call_id=running_tool_call.id,
            result=result.output,
            latency_ms=latency_ms,
        )
        if completed_tool_call is None:
            raise RunExecutionError(f"Tool call {running_tool_call.id} was not found.")
        log_event(
            LOGGER,
            level=logging.INFO,
            event="tool.call.completed",
            context=_context_from_run(
                running,
                tool_call_id=completed_tool_call.id,
                approval_id=approval.id if approval is not None else None,
            ),
            status=completed_tool_call.status.value,
            tool_name=completed_tool_call.tool_name,
            extra={
                "latency_ms": latency_ms,
                "risk_level": completed_tool_call.risk_level.value,
                "requires_approval": completed_tool_call.requires_approval,
            },
        )
        self._record_tool_success_metrics(
            tool_name=completed_tool_call.tool_name,
            latency_ms=latency_ms,
        )
        return completed_tool_call

    def _complete_tool_run(
        self,
        *,
        running: Run,
        repository: RunRepository,
        completed_tool_call: ToolCall,
        approval: Approval | None,
    ) -> Run:

        succeed_transition = self._state_machine.succeed(running)
        persisted = repository.get(running.id)
        if persisted is None:
            raise RunNotFoundError(f"Run {running.id} was not found.")
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
            input_tokens_total=persisted.input_tokens_total,
            output_tokens_total=persisted.output_tokens_total,
            estimated_cost_total=persisted.estimated_cost_total,
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
        budget: ExecutionBudget | None = None,
    ) -> Any:
        request = ToolRequest(
            tool_name=tool_call.tool_name,
            arguments=tool_call.arguments,
            context=ToolExecutionContext(
                run_id=running.id,
                workspace_id=running.workspace_id,
                tool_call_id=tool_call.id,
            ),
        )
        for attempt in range(1, self._retry_policy.tool_max_attempts + 1):
            attempt_timer = LatencyTimer.start()
            try:
                repository.assert_owned(running.id)
                if budget is not None:
                    self._check_native_budget(repository, budget)
                    if budget.state.tool_calls >= budget.state.limits.max_tool_calls:
                        raise ExecutionLimitError("tool_calls")
                    budget.state.tool_calls += 1
                    self._checkpoint(repository, budget)
                with trace_operation("tool.call", attributes={"tool_name": tool_call.tool_name}):
                    return await self._await_budgeted(
                        budget, lambda: self._tool_executor.execute(request)
                    )
            except ToolError as error:
                attempt_latency_ms = attempt_timer.elapsed_ms()
                if self._should_retry_tool(error, tool_call) and (
                    attempt < self._retry_policy.tool_max_attempts
                ):
                    log_event(
                        LOGGER,
                        level=logging.WARNING,
                        event="tool.call.retrying",
                        context=_context_from_run(running, tool_call_id=tool_call.id),
                        status=tool_call.status.value,
                        tool_name=tool_call.tool_name,
                        error_type=error.error_type,
                        extra={
                            "latency_ms": attempt_latency_ms,
                            "attempt": attempt + 1,
                            "max_attempts": self._retry_policy.tool_max_attempts,
                            "risk_level": tool_call.risk_level.value,
                        },
                    )
                    await self._pause_before_retry(
                        running=running,
                        repository=repository,
                        attempt=attempt,
                        budget=budget,
                        event_type=RunEventType.TOOL_CALL_RETRYING,
                        payload={
                            "tool_call_id": str(tool_call.id),
                            "tool_name": tool_call.tool_name,
                            "attempt": attempt + 1,
                            "max_attempts": self._retry_policy.tool_max_attempts,
                            "error_type": error.error_type,
                            "error_message": str(error),
                        },
                    )
                    continue
                raise

        raise RunExecutionError("Tool retry loop exited without a result or error.")

    def _record_response_usage(
        self,
        repository: RunRepository,
        run_id: UUID,
        response: LLMResponse,
        latency_ms: int,
    ) -> None:
        repository.record_usage(
            run_id,
            provider=response.provider,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            estimated_cost=response.usage.estimated_cost,
        )
        self._record_model_success_metrics(
            provider=response.provider,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            estimated_cost=response.usage.estimated_cost,
            latency_ms=latency_ms,
        )

    def _should_retry_provider(self, error: LLMProviderError) -> bool:
        return error.error_type in self._retry_policy.retryable_provider_error_types

    def _should_retry_tool(self, error: ToolError, tool_call: ToolCall) -> bool:
        if self._tool_registry.get(tool_call.tool_name).metadata.retry_safe is False:
            return False
        return (
            error.error_type in self._retry_policy.retryable_tool_error_types
            and tool_call.risk_level in self._retry_policy.retryable_tool_risk_levels
            and not tool_call.requires_approval
        )

    def _record_model_success_metrics(
        self,
        *,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost: float,
        latency_ms: int,
    ) -> None:
        labels = {"provider": provider, "model": model, "status": RunStatus.SUCCEEDED.value}
        self._metrics_recorder.increment("llm_model_calls_total", labels=labels)
        self._metrics_recorder.observe("llm_model_call_latency_ms", latency_ms, labels=labels)
        self._metrics_recorder.increment(
            "llm_tokens_input_total",
            value=float(input_tokens),
            labels={"provider": provider, "model": model},
        )
        self._metrics_recorder.increment(
            "llm_tokens_output_total",
            value=float(output_tokens),
            labels={"provider": provider, "model": model},
        )
        self._metrics_recorder.increment(
            "llm_tokens_total",
            value=float(input_tokens + output_tokens),
            labels={"provider": provider, "model": model},
        )
        self._metrics_recorder.increment(
            "llm_estimated_cost_total",
            value=estimated_cost,
            labels={"provider": provider, "model": model},
        )

    def _record_model_failure_metrics(
        self,
        *,
        provider: str,
        model: str,
        error_type: str,
        latency_ms: int,
    ) -> None:
        labels = {
            "provider": provider,
            "model": model,
            "status": RunStatus.FAILED.value,
            "error_type": error_type,
        }
        self._metrics_recorder.increment("llm_model_calls_total", labels=labels)
        self._metrics_recorder.observe("llm_model_call_latency_ms", latency_ms, labels=labels)

    def _record_tool_success_metrics(self, *, tool_name: str, latency_ms: int) -> None:
        labels = {"tool_name": tool_name, "status": ToolCallStatus.SUCCEEDED.value}
        self._metrics_recorder.increment("tool_calls_total", labels=labels)
        self._metrics_recorder.observe("tool_call_latency_ms", latency_ms, labels=labels)

    def _record_tool_failure_metrics(
        self,
        *,
        tool_name: str,
        error_type: str,
        latency_ms: int,
    ) -> None:
        labels = {
            "tool_name": tool_name,
            "status": ToolCallStatus.FAILED.value,
            "error_type": error_type,
        }
        self._metrics_recorder.increment("tool_calls_total", labels=labels)
        self._metrics_recorder.increment("tool_call_failure_total", labels=labels)
        self._metrics_recorder.observe("tool_call_latency_ms", latency_ms, labels=labels)

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

        log_event(
            LOGGER,
            level=logging.ERROR,
            event="agent.run.failed",
            context=_context_from_run(running),
            status=RunStatus.FAILED.value,
            provider=provider,
            error_type=error_type,
        )
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
        log_event(
            LOGGER,
            level=logging.ERROR,
            event="agent.run.failed",
            context=_context_from_run(
                waiting,
                tool_call_id=approval.tool_call_id,
                approval_id=approval.id,
            ),
            status=RunStatus.FAILED.value,
            error_type="approval_rejected",
        )
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


def _context_from_run(
    run: Run,
    *,
    tool_call_id: UUID | None = None,
    approval_id: UUID | None = None,
) -> ObservabilityContext:
    return ObservabilityContext.create(
        trace_id=run.trace_id,
        run_id=run.id,
        agent_id=run.agent_id,
        tool_call_id=tool_call_id,
        approval_id=approval_id,
    )


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
                content=MEMORY_CONTEXT_POLICY,
                name="memory_policy",
            ),
            LLMMessage(
                role=MessageRole.USER,
                content=memory_context.to_prompt_text(),
                name="memory_context",
                metadata={
                    "memory_item_ids": [str(item_id) for item_id in memory_context.item_ids],
                    "trust": "untrusted",
                    "memory_context_version": MEMORY_CONTEXT_VERSION,
                },
            ),
            *messages,
        )
    return LLMRequest(
        model=model,
        messages=messages,
        metadata={"run_id": str(run.id), "agent_id": str(run.agent_id)},
    )


def _request_with_tool_result(
    *,
    initial_request: LLMRequest,
    initial_response: LLMResponse,
    tool_call: ToolCall,
) -> LLMRequest:
    return initial_request.model_copy(
        update={
            "messages": (
                *initial_request.messages,
                LLMMessage(
                    role=MessageRole.ASSISTANT,
                    content=initial_response.text,
                    name="provider_tool_call_request",
                    metadata={
                        "finish_reason": initial_response.finish_reason.value,
                        "provider_name": initial_response.provider,
                        "provider_response_output": deepcopy(initial_response.raw.get("output")),
                        "tool_calls": [
                            requested_tool_call.model_dump(mode="json")
                            for requested_tool_call in initial_response.tool_calls
                        ],
                    },
                ),
                _tool_result_message(tool_call),
            ),
            "tool_choice": LLMToolChoice.AUTO,
        }
    )


def _tool_result_message(tool_call: ToolCall) -> LLMMessage:
    return LLMMessage(
        role=MessageRole.TOOL,
        content=json.dumps(
            {
                "tool_call_id": str(tool_call.id),
                "provider_tool_call_id": tool_call.provider_tool_call_id,
                "tool_name": tool_call.tool_name,
                "result": tool_call.result or {},
            },
            sort_keys=True,
        ),
        name=tool_call.tool_name,
        metadata={
            "tool_call_id": str(tool_call.id),
            "provider_name": tool_call.provider_name,
            "provider_tool_call_id": tool_call.provider_tool_call_id,
        },
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


def _explicit_memory_request_from_run(run: Run) -> MemorySelection | None:
    raw_memory = run.input.get("memory")
    if raw_memory is None:
        return None
    try:
        return MemorySelection.model_validate(raw_memory)
    except ValidationError as error:
        raise RunExecutionError(
            "Invalid memory selection: check memory.scopes, memory.types and memory.limit."
        ) from error


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
