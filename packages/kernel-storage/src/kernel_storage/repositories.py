"""Repository layer for persisted Agent Kernel execution state."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from kernel_core import (
    Agent,
    AgentStatus,
    RiskLevel,
    Run,
    RunEvent,
    RunEventType,
    RunStatus,
    ToolCall,
    ToolCallStatus,
    utc_now,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kernel_storage.models import AgentRecord, RunEventRecord, RunRecord, ToolCallRecord


class AgentRepository:
    """Persistence operations for agents."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, name: str, description: str = "") -> Agent:
        agent = Agent(name=name, description=description)
        self._session.add(_agent_to_record(agent))
        self._session.commit()
        return agent

    def get(self, agent_id: UUID) -> Agent | None:
        record = self._session.get(AgentRecord, str(agent_id))
        if record is None:
            return None
        return _agent_from_record(record)


class RunRepository:
    """Persistence operations for runs and run event timelines."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, agent_id: UUID, input_payload: dict[str, Any]) -> Run:
        run = Run(agent_id=agent_id, input=input_payload)
        self._session.add(_run_to_record(run))
        self._session.add(
            RunEventRecord(
                id=str(RunEvent(run_id=run.id, sequence=1, type=RunEventType.RUN_CREATED).id),
                run_id=str(run.id),
                sequence=1,
                type=RunEventType.RUN_CREATED.value,
                payload={"status": run.status.value},
                trace_id=run.trace_id,
            )
        )
        self._session.commit()
        return run

    def get(self, run_id: UUID) -> Run | None:
        record = self._session.get(RunRecord, str(run_id))
        if record is None:
            return None
        return _run_from_record(record)

    def list_events(self, run_id: UUID) -> list[RunEvent]:
        statement = (
            select(RunEventRecord)
            .where(RunEventRecord.run_id == str(run_id))
            .order_by(RunEventRecord.sequence)
        )
        return [_run_event_from_record(record) for record in self._session.scalars(statement)]

    def update_status(self, *, run_id: UUID, status: RunStatus) -> Run | None:
        record = self._session.get(RunRecord, str(run_id))
        if record is None:
            return None

        _apply_status(record, status)
        self._session.commit()
        return _run_from_record(record)

    def append_event(
        self,
        *,
        run_id: UUID,
        event_type: RunEventType,
        payload: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> RunEvent | None:
        if self._session.get(RunRecord, str(run_id)) is None:
            return None

        sequence = self._next_event_sequence(run_id)
        event = RunEvent(
            run_id=run_id,
            sequence=sequence,
            type=event_type,
            payload=payload or {},
            trace_id=trace_id,
        )
        self._session.add(
            RunEventRecord(
                id=str(event.id),
                run_id=str(event.run_id),
                sequence=event.sequence,
                type=event.type.value,
                payload=event.payload,
                trace_id=event.trace_id,
                created_at=event.created_at,
            )
        )
        self._session.commit()
        return event

    def apply_transition(
        self,
        *,
        run_id: UUID,
        status: RunStatus,
        event_type: RunEventType,
        payload: dict[str, Any],
    ) -> Run | None:
        record = self._session.get(RunRecord, str(run_id))
        if record is None:
            return None

        _apply_status(record, status)
        sequence = self._next_event_sequence(run_id)
        self._session.add(
            RunEventRecord(
                id=str(RunEvent(run_id=run_id, sequence=sequence, type=event_type).id),
                run_id=str(run_id),
                sequence=sequence,
                type=event_type.value,
                payload=payload,
                trace_id=record.trace_id,
            )
        )
        self._session.commit()
        return _run_from_record(record)

    def complete(
        self,
        *,
        run_id: UUID,
        output_payload: dict[str, Any],
        input_tokens_total: int,
        output_tokens_total: int,
        estimated_cost_total: float,
        event_payload: dict[str, Any],
    ) -> Run | None:
        record = self._session.get(RunRecord, str(run_id))
        if record is None:
            return None

        _apply_status(record, RunStatus.SUCCEEDED)
        record.output_payload = output_payload
        record.input_tokens_total = input_tokens_total
        record.output_tokens_total = output_tokens_total
        record.estimated_cost_total = estimated_cost_total
        self._add_event_record(
            run_id=run_id,
            event_type=RunEventType.RUN_COMPLETED,
            payload=event_payload,
            trace_id=record.trace_id,
        )
        self._session.commit()
        return _run_from_record(record)

    def fail(
        self,
        *,
        run_id: UUID,
        error_type: str,
        error_message: str,
        event_payload: dict[str, Any],
    ) -> Run | None:
        record = self._session.get(RunRecord, str(run_id))
        if record is None:
            return None

        _apply_status(record, RunStatus.FAILED)
        record.error_type = error_type
        record.error_message = error_message
        self._add_event_record(
            run_id=run_id,
            event_type=RunEventType.RUN_FAILED,
            payload=event_payload,
            trace_id=record.trace_id,
        )
        self._session.commit()
        return _run_from_record(record)

    def list_queued(self, *, limit: int = 100) -> list[Run]:
        statement = (
            select(RunRecord)
            .where(RunRecord.status == RunStatus.QUEUED.value)
            .order_by(RunRecord.created_at)
            .limit(limit)
        )
        return [_run_from_record(record) for record in self._session.scalars(statement)]

    def _next_event_sequence(self, run_id: UUID) -> int:
        statement = select(func.max(RunEventRecord.sequence)).where(
            RunEventRecord.run_id == str(run_id)
        )
        current = self._session.scalar(statement)
        if current is None:
            return 1
        return int(current) + 1

    def _add_event_record(
        self,
        *,
        run_id: UUID,
        event_type: RunEventType,
        payload: dict[str, Any],
        trace_id: str | None,
    ) -> None:
        sequence = self._next_event_sequence(run_id)
        self._session.add(
            RunEventRecord(
                id=str(RunEvent(run_id=run_id, sequence=sequence, type=event_type).id),
                run_id=str(run_id),
                sequence=sequence,
                type=event_type.value,
                payload=payload,
                trace_id=trace_id,
            )
        )


class ToolCallRepository:
    """Persistence operations for tool calls and audit timeline events."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_requested(
        self,
        *,
        run_id: UUID,
        tool_name: str,
        arguments: dict[str, Any],
        risk_level: RiskLevel,
        requires_approval: bool = False,
        step_id: UUID | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> ToolCall | None:
        run = self._session.get(RunRecord, str(run_id))
        if run is None:
            return None

        tool_call = ToolCall(
            run_id=run_id,
            step_id=step_id,
            tool_name=tool_name,
            arguments=arguments,
            risk_level=risk_level,
            requires_approval=requires_approval,
            trace_id=trace_id or run.trace_id,
            span_id=span_id,
        )
        self._session.add(_tool_call_to_record(tool_call))
        self._add_event_record(
            run_id=run_id,
            event_type=RunEventType.TOOL_CALL_REQUESTED,
            payload={
                "tool_call_id": str(tool_call.id),
                "tool_name": tool_name,
                "risk_level": risk_level.value,
                "requires_approval": requires_approval,
            },
            trace_id=tool_call.trace_id,
        )
        self._session.commit()
        return tool_call

    def get(self, tool_call_id: UUID) -> ToolCall | None:
        record = self._session.get(ToolCallRecord, str(tool_call_id))
        if record is None:
            return None
        return _tool_call_from_record(record)

    def list_for_run(self, run_id: UUID) -> list[ToolCall]:
        statement = (
            select(ToolCallRecord)
            .where(ToolCallRecord.run_id == str(run_id))
            .order_by(ToolCallRecord.created_at)
        )
        return [_tool_call_from_record(record) for record in self._session.scalars(statement)]

    def record_policy_decision(
        self,
        *,
        tool_call_id: UUID,
        decision: str,
        reason: str,
        status: ToolCallStatus,
        requires_approval: bool = False,
    ) -> ToolCall | None:
        record = self._session.get(ToolCallRecord, str(tool_call_id))
        if record is None:
            return None

        record.status = status.value
        record.requires_approval = requires_approval
        self._add_event_record(
            run_id=UUID(record.run_id),
            event_type=RunEventType.POLICY_EVALUATED,
            payload={
                "tool_call_id": record.id,
                "tool_name": record.tool_name,
                "decision": decision,
                "reason": reason,
                "status": status.value,
                "requires_approval": requires_approval,
            },
            trace_id=record.trace_id,
        )
        self._session.commit()
        return _tool_call_from_record(record)

    def complete(
        self,
        *,
        tool_call_id: UUID,
        result: dict[str, Any],
        latency_ms: int | None = None,
    ) -> ToolCall | None:
        record = self._session.get(ToolCallRecord, str(tool_call_id))
        if record is None:
            return None

        record.status = ToolCallStatus.SUCCEEDED.value
        record.result = result
        record.latency_ms = latency_ms
        self._add_event_record(
            run_id=UUID(record.run_id),
            event_type=RunEventType.TOOL_CALL_COMPLETED,
            payload={
                "tool_call_id": record.id,
                "tool_name": record.tool_name,
                "status": ToolCallStatus.SUCCEEDED.value,
                "latency_ms": latency_ms,
            },
            trace_id=record.trace_id,
        )
        self._session.commit()
        return _tool_call_from_record(record)

    def fail(
        self,
        *,
        tool_call_id: UUID,
        error_type: str,
        error_message: str,
        latency_ms: int | None = None,
    ) -> ToolCall | None:
        record = self._session.get(ToolCallRecord, str(tool_call_id))
        if record is None:
            return None

        record.status = ToolCallStatus.FAILED.value
        record.error_type = error_type
        record.error_message = error_message
        record.latency_ms = latency_ms
        self._add_event_record(
            run_id=UUID(record.run_id),
            event_type=RunEventType.TOOL_CALL_FAILED,
            payload={
                "tool_call_id": record.id,
                "tool_name": record.tool_name,
                "status": ToolCallStatus.FAILED.value,
                "error_type": error_type,
                "error_message": error_message,
                "latency_ms": latency_ms,
            },
            trace_id=record.trace_id,
        )
        self._session.commit()
        return _tool_call_from_record(record)

    def _next_event_sequence(self, run_id: UUID) -> int:
        statement = select(func.max(RunEventRecord.sequence)).where(
            RunEventRecord.run_id == str(run_id)
        )
        current = self._session.scalar(statement)
        if current is None:
            return 1
        return int(current) + 1

    def _add_event_record(
        self,
        *,
        run_id: UUID,
        event_type: RunEventType,
        payload: dict[str, Any],
        trace_id: str | None,
    ) -> None:
        sequence = self._next_event_sequence(run_id)
        self._session.add(
            RunEventRecord(
                id=str(RunEvent(run_id=run_id, sequence=sequence, type=event_type).id),
                run_id=str(run_id),
                sequence=sequence,
                type=event_type.value,
                payload=payload,
                trace_id=trace_id,
            )
        )


def _agent_to_record(agent: Agent) -> AgentRecord:
    return AgentRecord(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        status=agent.status.value,
        prompt_id=str(agent.prompt_id) if agent.prompt_id is not None else None,
        default_model_policy_id=(
            str(agent.default_model_policy_id)
            if agent.default_model_policy_id is not None
            else None
        ),
        memory_policy=agent.memory_policy,
        tool_policy=agent.tool_policy,
        extra_metadata=agent.metadata,
        created_at=agent.created_at,
    )


def _agent_from_record(record: AgentRecord) -> Agent:
    return Agent(
        id=UUID(record.id),
        name=record.name,
        description=record.description,
        status=AgentStatus(record.status),
        prompt_id=UUID(record.prompt_id) if record.prompt_id is not None else None,
        default_model_policy_id=(
            UUID(record.default_model_policy_id)
            if record.default_model_policy_id is not None
            else None
        ),
        memory_policy=record.memory_policy,
        tool_policy=record.tool_policy,
        metadata=record.extra_metadata,
        created_at=record.created_at,
    )


def _run_to_record(run: Run) -> RunRecord:
    return RunRecord(
        id=str(run.id),
        agent_id=str(run.agent_id),
        status=run.status.value,
        input_payload=run.input,
        output_payload=run.output,
        trace_id=run.trace_id,
        error_type=run.error_type,
        error_message=run.error_message,
        input_tokens_total=run.input_tokens_total,
        output_tokens_total=run.output_tokens_total,
        estimated_cost_total=run.estimated_cost_total,
        started_at=run.started_at,
        ended_at=run.ended_at,
        created_at=run.created_at,
    )


def _run_from_record(record: RunRecord) -> Run:
    return Run(
        id=UUID(record.id),
        agent_id=UUID(record.agent_id),
        status=RunStatus(record.status),
        input=record.input_payload,
        output=record.output_payload,
        trace_id=record.trace_id,
        error_type=record.error_type,
        error_message=record.error_message,
        input_tokens_total=record.input_tokens_total,
        output_tokens_total=record.output_tokens_total,
        estimated_cost_total=record.estimated_cost_total,
        started_at=record.started_at,
        ended_at=record.ended_at,
        created_at=record.created_at,
    )


def _apply_status(record: RunRecord, status: RunStatus) -> None:
    record.status = status.value
    if status is RunStatus.RUNNING:
        record.started_at = record.started_at or utc_now()
    if status in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELED}:
        record.ended_at = utc_now()


def _run_event_from_record(record: RunEventRecord) -> RunEvent:
    return RunEvent(
        id=UUID(record.id),
        run_id=UUID(record.run_id),
        sequence=record.sequence,
        type=RunEventType(record.type),
        payload=record.payload,
        trace_id=record.trace_id,
        created_at=record.created_at,
    )


def _tool_call_to_record(tool_call: ToolCall) -> ToolCallRecord:
    return ToolCallRecord(
        id=str(tool_call.id),
        run_id=str(tool_call.run_id),
        step_id=str(tool_call.step_id) if tool_call.step_id is not None else None,
        tool_name=tool_call.tool_name,
        arguments=tool_call.arguments,
        result=tool_call.result,
        status=tool_call.status.value,
        risk_level=tool_call.risk_level.value,
        requires_approval=tool_call.requires_approval,
        approval_id=str(tool_call.approval_id) if tool_call.approval_id is not None else None,
        trace_id=tool_call.trace_id,
        span_id=tool_call.span_id,
        error_type=tool_call.error_type,
        error_message=tool_call.error_message,
        latency_ms=tool_call.latency_ms,
        created_at=tool_call.created_at,
    )


def _tool_call_from_record(record: ToolCallRecord) -> ToolCall:
    return ToolCall(
        id=UUID(record.id),
        run_id=UUID(record.run_id),
        step_id=UUID(record.step_id) if record.step_id is not None else None,
        tool_name=record.tool_name,
        arguments=record.arguments,
        result=record.result,
        status=ToolCallStatus(record.status),
        risk_level=RiskLevel(record.risk_level),
        requires_approval=record.requires_approval,
        approval_id=UUID(record.approval_id) if record.approval_id is not None else None,
        trace_id=record.trace_id,
        span_id=record.span_id,
        error_type=record.error_type,
        error_message=record.error_message,
        latency_ms=record.latency_ms,
        created_at=record.created_at,
    )
