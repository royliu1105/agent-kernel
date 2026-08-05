"""Repository layer for persisted Agent Kernel execution state."""

from __future__ import annotations

import builtins
import math
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from kernel_core import (
    Agent,
    AgentStatus,
    Approval,
    ApprovalStatus,
    ChunkEmbedding,
    Document,
    DocumentChunk,
    DocumentStatus,
    IngestionJob,
    IngestionJobStatus,
    KnowledgeBase,
    KnowledgeBaseStatus,
    MemoryItem,
    MemoryType,
    RiskLevel,
    Run,
    RunEvent,
    RunEventType,
    RunStatus,
    ToolCall,
    ToolCallStatus,
    WorkerLease,
    utc_now,
)
from kernel_identity import (
    ApiKey,
    ApiKeyCredential,
    ApiKeyStatus,
    Principal,
    PrincipalType,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
    WorkspaceStatus,
    api_key_prefix,
    generate_api_key,
    hash_api_key,
)
from kernel_observability import ensure_trace_id
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from kernel_storage.config import get_vector_store_mode
from kernel_storage.models import (
    AgentRecord,
    ApiKeyRecord,
    ApprovalRecord,
    ChunkEmbeddingRecord,
    DocumentChunkRecord,
    DocumentRecord,
    IngestionJobRecord,
    KnowledgeBaseRecord,
    MemoryItemRecord,
    PrincipalRecord,
    RunEventRecord,
    RunRecord,
    ToolCallRecord,
    WorkerLeaseRecord,
    WorkspaceMembershipRecord,
    WorkspaceRecord,
)


class ApprovalDecisionError(ValueError):
    """Raised when an approval cannot be decided."""


class KnowledgeBaseNotFoundError(ValueError):
    """Raised when a knowledge base does not exist."""


class IngestionJobStateError(ValueError):
    """Raised when an ingestion job cannot transition as requested."""


class DocumentChunkingError(ValueError):
    """Raised when document chunks cannot be persisted."""


class VectorStoreConfigError(ValueError):
    """Raised when vector store configuration is not valid for the database."""


class MemoryNotFoundError(ValueError):
    """Raised when a memory item does not exist."""


class PrincipalRepository:
    """Persistence operations for authenticated principals."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        type: PrincipalType,
        display_name: str,
        disabled: bool = False,
    ) -> Principal:
        principal = Principal(type=type, display_name=display_name, disabled=disabled)
        self._session.add(_principal_to_record(principal))
        self._session.commit()
        return principal

    def get(self, principal_id: UUID) -> Principal | None:
        record = self._session.get(PrincipalRecord, str(principal_id))
        if record is None:
            return None
        return _principal_from_record(record)

    def set_disabled(self, *, principal_id: UUID, disabled: bool) -> Principal | None:
        record = self._session.get(PrincipalRecord, str(principal_id))
        if record is None:
            return None
        record.disabled = disabled
        self._session.commit()
        return _principal_from_record(record)


class WorkspaceRepository:
    """Persistence operations for workspace boundaries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        name: str,
        slug: str,
        status: WorkspaceStatus = WorkspaceStatus.ACTIVE,
    ) -> Workspace:
        workspace = Workspace(name=name, slug=slug, status=status)
        self._session.add(_workspace_to_record(workspace))
        self._session.commit()
        return workspace

    def get(self, workspace_id: UUID) -> Workspace | None:
        record = self._session.get(WorkspaceRecord, str(workspace_id))
        if record is None:
            return None
        return _workspace_from_record(record)

    def get_by_slug(self, slug: str) -> Workspace | None:
        record = self._session.scalar(select(WorkspaceRecord).where(WorkspaceRecord.slug == slug))
        if record is None:
            return None
        return _workspace_from_record(record)


class WorkspaceMembershipRepository:
    """Persistence operations for workspace role assignments."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def assign(
        self,
        *,
        principal_id: UUID,
        workspace_id: UUID,
        role: WorkspaceRole,
    ) -> WorkspaceMembership | None:
        if self._session.get(PrincipalRecord, str(principal_id)) is None:
            return None
        if self._session.get(WorkspaceRecord, str(workspace_id)) is None:
            return None

        record = self._session.get(
            WorkspaceMembershipRecord,
            (str(principal_id), str(workspace_id)),
        )
        if record is None:
            membership = WorkspaceMembership(
                principal_id=principal_id,
                workspace_id=workspace_id,
                role=role,
            )
            self._session.add(_membership_to_record(membership))
            self._session.commit()
            return membership

        record.role = role.value
        self._session.commit()
        return _membership_from_record(record)

    def get(self, *, principal_id: UUID, workspace_id: UUID) -> WorkspaceMembership | None:
        record = self._session.get(
            WorkspaceMembershipRecord,
            (str(principal_id), str(workspace_id)),
        )
        if record is None:
            return None
        return _membership_from_record(record)

    def list_for_principal(self, principal_id: UUID) -> list[WorkspaceMembership]:
        statement = (
            select(WorkspaceMembershipRecord)
            .where(WorkspaceMembershipRecord.principal_id == str(principal_id))
            .order_by(WorkspaceMembershipRecord.created_at)
        )
        return [_membership_from_record(record) for record in self._session.scalars(statement)]


class ApiKeyRepository:
    """Persistence operations for hashed API keys."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def issue(
        self,
        *,
        workspace_id: UUID,
        principal_id: UUID,
        name: str,
        plaintext_key: str | None = None,
        expires_at: datetime | None = None,
    ) -> ApiKeyCredential | None:
        if self._session.get(PrincipalRecord, str(principal_id)) is None:
            return None
        if self._session.get(WorkspaceRecord, str(workspace_id)) is None:
            return None
        if (
            self._session.get(
                WorkspaceMembershipRecord,
                (str(principal_id), str(workspace_id)),
            )
            is None
        ):
            return None

        secret = plaintext_key or generate_api_key()
        api_key = ApiKey(
            workspace_id=workspace_id,
            principal_id=principal_id,
            name=name,
            key_prefix=api_key_prefix(secret),
            key_hash=hash_api_key(secret),
            expires_at=expires_at,
        )
        self._session.add(_api_key_to_record(api_key))
        self._session.commit()
        return ApiKeyCredential(api_key=api_key, plaintext_key=secret)

    def get(self, api_key_id: UUID) -> ApiKey | None:
        record = self._session.get(ApiKeyRecord, str(api_key_id))
        if record is None:
            return None
        return _api_key_from_record(record)

    def authenticate(self, plaintext_key: str) -> ApiKey | None:
        key_hash = hash_api_key(plaintext_key)
        record = self._session.scalar(select(ApiKeyRecord).where(ApiKeyRecord.key_hash == key_hash))
        if record is None:
            return None
        api_key = _api_key_from_record(record)
        if api_key.status is not ApiKeyStatus.ACTIVE:
            return None
        now = utc_now()
        expires_at = api_key.expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            now = now.replace(tzinfo=None)
        if expires_at is not None and expires_at <= now:
            record.status = ApiKeyStatus.EXPIRED.value
            self._session.commit()
            return None

        record.last_used_at = now
        self._session.commit()
        return _api_key_from_record(record)

    def revoke(self, api_key_id: UUID) -> bool:
        record = self._session.get(ApiKeyRecord, str(api_key_id))
        if record is None:
            return False
        record.status = ApiKeyStatus.REVOKED.value
        self._session.commit()
        return True


class AgentRepository:
    """Persistence operations for agents."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        name: str,
        description: str = "",
        workspace_id: UUID | None = None,
    ) -> Agent:
        agent = Agent(name=name, description=description, workspace_id=workspace_id)
        self._session.add(_agent_to_record(agent))
        self._session.commit()
        return agent

    def get(self, agent_id: UUID, *, workspace_id: UUID | None = None) -> Agent | None:
        record = self._session.get(AgentRecord, str(agent_id))
        if record is None:
            return None
        if workspace_id is not None and record.workspace_id != str(workspace_id):
            return None
        return _agent_from_record(record)


class RunRepository:
    """Persistence operations for runs and run event timelines."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    def create(
        self,
        *,
        agent_id: UUID,
        input_payload: dict[str, Any],
        trace_id: str | None = None,
        workspace_id: UUID | None = None,
    ) -> Run:
        run = Run(
            agent_id=agent_id,
            workspace_id=workspace_id,
            input=input_payload,
            trace_id=ensure_trace_id(trace_id),
        )
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

    def get(self, run_id: UUID, *, workspace_id: UUID | None = None) -> Run | None:
        record = self._session.get(RunRecord, str(run_id))
        if record is None:
            return None
        if workspace_id is not None and record.workspace_id != str(workspace_id):
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
        record = self._session.get(RunRecord, str(run_id))
        if record is None:
            return None

        sequence = self._next_event_sequence(run_id)
        event = RunEvent(
            run_id=run_id,
            sequence=sequence,
            type=event_type,
            payload=payload or {},
            trace_id=trace_id or record.trace_id,
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


class WorkerLeaseRepository:
    """Persistence operations for worker run leases."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def acquire(
        self,
        *,
        run_id: UUID,
        worker_id: str,
        ttl_seconds: int = 60,
    ) -> WorkerLease | None:
        if ttl_seconds < 1:
            raise ValueError("Lease ttl_seconds must be at least 1.")
        if not worker_id.strip():
            raise ValueError("Lease worker_id must not be empty.")

        run = self._session.get(RunRecord, str(run_id))
        if run is None or RunStatus(run.status) is not RunStatus.QUEUED:
            return None

        now = utc_now()
        active_lease = self._active_record_for_run(run_id=run_id, now=now)
        if active_lease is not None:
            return None

        self._release_expired_records(run_id=run_id, now=now)
        lease = WorkerLease(
            run_id=run_id,
            worker_id=worker_id.strip(),
            lease_token=str(uuid4()),
            acquired_at=now,
            heartbeat_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        self._session.add(_worker_lease_to_record(lease))
        self._session.commit()
        return lease

    def get_active(self, *, run_id: UUID) -> WorkerLease | None:
        record = self._active_record_for_run(run_id=run_id, now=utc_now())
        if record is None:
            return None
        return _worker_lease_from_record(record)

    def list_expired(self, *, limit: int = 100) -> list[WorkerLease]:
        if limit < 1:
            raise ValueError("Lease list limit must be at least 1.")

        now = utc_now()
        statement = (
            select(WorkerLeaseRecord)
            .where(
                WorkerLeaseRecord.released_at.is_(None),
                WorkerLeaseRecord.expires_at <= now,
            )
            .order_by(WorkerLeaseRecord.expires_at)
            .limit(limit)
        )
        return [_worker_lease_from_record(record) for record in self._session.scalars(statement)]

    def heartbeat(
        self,
        *,
        lease_token: str,
        ttl_seconds: int = 60,
    ) -> WorkerLease | None:
        if ttl_seconds < 1:
            raise ValueError("Lease ttl_seconds must be at least 1.")

        now = utc_now()
        record = self._session.scalar(
            select(WorkerLeaseRecord).where(WorkerLeaseRecord.lease_token == lease_token)
        )
        if record is None or not _worker_lease_record_is_active(record, now):
            return None

        record.heartbeat_at = now
        record.expires_at = now + timedelta(seconds=ttl_seconds)
        self._session.commit()
        return _worker_lease_from_record(record)

    def release(self, *, lease_token: str) -> WorkerLease | None:
        now = utc_now()
        record = self._session.scalar(
            select(WorkerLeaseRecord).where(WorkerLeaseRecord.lease_token == lease_token)
        )
        if record is None or record.released_at is not None:
            return None

        record.released_at = now
        self._session.commit()
        return _worker_lease_from_record(record)

    def _active_record_for_run(self, *, run_id: UUID, now: datetime) -> WorkerLeaseRecord | None:
        statement = (
            select(WorkerLeaseRecord)
            .where(
                WorkerLeaseRecord.run_id == str(run_id),
                WorkerLeaseRecord.released_at.is_(None),
            )
            .order_by(WorkerLeaseRecord.acquired_at.desc())
        )
        for record in self._session.scalars(statement):
            if _worker_lease_record_is_active(record, now):
                return record
        return None

    def _release_expired_records(self, *, run_id: UUID, now: datetime) -> None:
        statement = select(WorkerLeaseRecord).where(
            WorkerLeaseRecord.run_id == str(run_id),
            WorkerLeaseRecord.released_at.is_(None),
        )
        for record in self._session.scalars(statement):
            if not _worker_lease_record_is_active(record, now):
                record.released_at = now


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
        provider_name: str | None = None,
        provider_tool_call_id: str | None = None,
        raw_provider_payload: dict[str, Any] | None = None,
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
            provider_name=provider_name,
            provider_tool_call_id=provider_tool_call_id,
            raw_provider_payload=raw_provider_payload,
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
                "provider_name": provider_name,
                "provider_tool_call_id": provider_tool_call_id,
            },
            trace_id=tool_call.trace_id,
        )
        self._session.commit()
        return tool_call

    def create_provider_requested(
        self,
        *,
        run_id: UUID,
        provider_name: str,
        provider_tool_call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        risk_level: RiskLevel,
        raw_provider_payload: dict[str, Any],
        trace_id: str | None = None,
    ) -> ToolCall | None:
        return self.create_requested(
            run_id=run_id,
            tool_name=tool_name,
            arguments=arguments,
            risk_level=risk_level,
            provider_name=provider_name,
            provider_tool_call_id=provider_tool_call_id,
            raw_provider_payload=raw_provider_payload,
            trace_id=trace_id,
        )

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

    def mark_running(self, *, tool_call_id: UUID) -> ToolCall | None:
        record = self._session.get(ToolCallRecord, str(tool_call_id))
        if record is None:
            return None

        record.status = ToolCallStatus.RUNNING.value
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


class ApprovalRepository:
    """Persistence operations for approvals and decision audit events."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_requested(
        self,
        *,
        tool_call_id: UUID,
        reason: str,
        requested_by: UUID | None = None,
    ) -> Approval | None:
        tool_call = self._session.get(ToolCallRecord, str(tool_call_id))
        if tool_call is None:
            return None

        approval = Approval(
            run_id=UUID(tool_call.run_id),
            tool_call_id=tool_call_id,
            reason=reason,
            requested_by=requested_by,
            trace_id=tool_call.trace_id,
        )
        self._session.add(_approval_to_record(approval))
        tool_call.requires_approval = True
        tool_call.status = ToolCallStatus.WAITING_APPROVAL.value
        tool_call.approval_id = str(approval.id)
        self._add_event_record(
            run_id=approval.run_id,
            event_type=RunEventType.APPROVAL_REQUESTED,
            payload={
                "approval_id": str(approval.id),
                "tool_call_id": str(tool_call_id),
                "tool_name": tool_call.tool_name,
                "reason": reason,
                "status": approval.status.value,
            },
            trace_id=approval.trace_id,
        )
        self._session.commit()
        return approval

    def list(
        self,
        *,
        status: ApprovalStatus | None = None,
        workspace_id: UUID | None = None,
    ) -> list[Approval]:
        statement = select(ApprovalRecord).order_by(ApprovalRecord.requested_at)
        if status is not None:
            statement = statement.where(ApprovalRecord.status == status.value)
        if workspace_id is not None:
            statement = statement.join(
                RunRecord,
                ApprovalRecord.run_id == RunRecord.id,
            ).where(RunRecord.workspace_id == str(workspace_id))
        return [_approval_from_record(record) for record in self._session.scalars(statement)]

    def list_for_run(
        self,
        run_id: UUID,
        *,
        workspace_id: UUID | None = None,
    ) -> builtins.list[Approval]:
        statement = (
            select(ApprovalRecord)
            .where(ApprovalRecord.run_id == str(run_id))
            .order_by(ApprovalRecord.requested_at)
        )
        if workspace_id is not None:
            statement = statement.join(
                RunRecord,
                ApprovalRecord.run_id == RunRecord.id,
            ).where(RunRecord.workspace_id == str(workspace_id))
        return [_approval_from_record(record) for record in self._session.scalars(statement)]

    def get(self, approval_id: UUID, *, workspace_id: UUID | None = None) -> Approval | None:
        record = self._get_record(approval_id=approval_id, workspace_id=workspace_id)
        if record is None:
            return None
        return _approval_from_record(record)

    def approve(
        self,
        *,
        approval_id: UUID,
        reviewed_by: UUID | None = None,
        decision_note: str | None = None,
        workspace_id: UUID | None = None,
    ) -> Approval | None:
        return self._decide(
            approval_id=approval_id,
            status=ApprovalStatus.APPROVED,
            reviewed_by=reviewed_by,
            decision_note=decision_note,
            event_type=RunEventType.APPROVAL_APPROVED,
            workspace_id=workspace_id,
        )

    def reject(
        self,
        *,
        approval_id: UUID,
        decision_note: str,
        reviewed_by: UUID | None = None,
        workspace_id: UUID | None = None,
    ) -> Approval | None:
        return self._decide(
            approval_id=approval_id,
            status=ApprovalStatus.REJECTED,
            reviewed_by=reviewed_by,
            decision_note=decision_note,
            event_type=RunEventType.APPROVAL_REJECTED,
            workspace_id=workspace_id,
        )

    def _decide(
        self,
        *,
        approval_id: UUID,
        status: ApprovalStatus,
        reviewed_by: UUID | None,
        decision_note: str | None,
        event_type: RunEventType,
        workspace_id: UUID | None,
    ) -> Approval | None:
        record = self._get_record(approval_id=approval_id, workspace_id=workspace_id)
        if record is None:
            return None
        if ApprovalStatus(record.status) is not ApprovalStatus.REQUESTED:
            raise ApprovalDecisionError(
                f"Approval {approval_id} has already been decided as {record.status}."
            )

        record.status = status.value
        record.reviewed_by = str(reviewed_by) if reviewed_by is not None else None
        record.decision_note = decision_note
        record.resolved_at = utc_now()
        self._add_event_record(
            run_id=UUID(record.run_id),
            event_type=event_type,
            payload={
                "approval_id": record.id,
                "tool_call_id": record.tool_call_id,
                "status": status.value,
                "decision_note": decision_note,
                "reviewed_by": str(reviewed_by) if reviewed_by is not None else None,
            },
            trace_id=record.trace_id,
        )
        self._session.commit()
        return _approval_from_record(record)

    def _get_record(
        self,
        *,
        approval_id: UUID,
        workspace_id: UUID | None = None,
    ) -> ApprovalRecord | None:
        if workspace_id is None:
            return self._session.get(ApprovalRecord, str(approval_id))

        statement = (
            select(ApprovalRecord)
            .join(RunRecord, ApprovalRecord.run_id == RunRecord.id)
            .where(
                ApprovalRecord.id == str(approval_id),
                RunRecord.workspace_id == str(workspace_id),
            )
        )
        return self._session.scalar(statement)

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


class KnowledgeBaseRepository:
    """Persistence operations for knowledge bases."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        name: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeBase:
        knowledge_base = KnowledgeBase(
            name=name,
            description=description,
            metadata=metadata or {},
        )
        self._session.add(_knowledge_base_to_record(knowledge_base))
        self._session.commit()
        return knowledge_base

    def get(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        record = self._session.get(KnowledgeBaseRecord, str(knowledge_base_id))
        if record is None:
            return None
        return _knowledge_base_from_record(record)

    def list(self) -> list[KnowledgeBase]:
        statement = select(KnowledgeBaseRecord).order_by(KnowledgeBaseRecord.created_at)
        return [_knowledge_base_from_record(record) for record in self._session.scalars(statement)]


class DocumentRepository:
    """Persistence operations for document metadata."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        knowledge_base_id: UUID,
        title: str,
        source_uri: str,
        mime_type: str | None = None,
        checksum: str | None = None,
        size_bytes: int | None = None,
        status: DocumentStatus = DocumentStatus.REGISTERED,
        metadata: dict[str, Any] | None = None,
    ) -> Document | None:
        if self._session.get(KnowledgeBaseRecord, str(knowledge_base_id)) is None:
            return None

        document = Document(
            knowledge_base_id=knowledge_base_id,
            title=title,
            source_uri=source_uri,
            mime_type=mime_type,
            checksum=checksum,
            size_bytes=size_bytes,
            status=status,
            metadata=metadata or {},
        )
        self._session.add(_document_to_record(document))
        self._session.commit()
        return document

    def get(self, document_id: UUID) -> Document | None:
        record = self._session.get(DocumentRecord, str(document_id))
        if record is None:
            return None
        return _document_from_record(record)

    def list_for_knowledge_base(self, knowledge_base_id: UUID) -> list[Document] | None:
        if self._session.get(KnowledgeBaseRecord, str(knowledge_base_id)) is None:
            return None

        statement = (
            select(DocumentRecord)
            .where(DocumentRecord.knowledge_base_id == str(knowledge_base_id))
            .order_by(DocumentRecord.created_at)
        )
        return [_document_from_record(record) for record in self._session.scalars(statement)]

    def update_status(
        self,
        *,
        document_id: UUID,
        status: DocumentStatus,
        error_message: str | None = None,
    ) -> Document | None:
        record = self._session.get(DocumentRecord, str(document_id))
        if record is None:
            return None

        record.status = status.value
        record.error_message = error_message
        record.updated_at = utc_now()
        self._session.commit()
        return _document_from_record(record)


class IngestionJobRepository:
    """Persistence operations for document ingestion jobs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        document_id: UUID,
        metadata: dict[str, Any] | None = None,
    ) -> IngestionJob | None:
        if self._session.get(DocumentRecord, str(document_id)) is None:
            return None

        job = IngestionJob(document_id=document_id, metadata=metadata or {})
        self._session.add(_ingestion_job_to_record(job))
        self._session.commit()
        return job

    def get(self, job_id: UUID) -> IngestionJob | None:
        record = self._session.get(IngestionJobRecord, str(job_id))
        if record is None:
            return None
        return _ingestion_job_from_record(record)

    def list_for_document(self, document_id: UUID) -> list[IngestionJob] | None:
        if self._session.get(DocumentRecord, str(document_id)) is None:
            return None

        statement = (
            select(IngestionJobRecord)
            .where(IngestionJobRecord.document_id == str(document_id))
            .order_by(IngestionJobRecord.created_at)
        )
        return [_ingestion_job_from_record(record) for record in self._session.scalars(statement)]

    def mark_parsing(self, *, job_id: UUID, parser_name: str) -> IngestionJob | None:
        record = self._session.get(IngestionJobRecord, str(job_id))
        if record is None:
            return None
        if IngestionJobStatus(record.status) is not IngestionJobStatus.CREATED:
            raise IngestionJobStateError(
                f"Ingestion job {job_id} cannot start from status {record.status}."
            )

        record.status = IngestionJobStatus.PARSING.value
        record.parser_name = parser_name
        record.started_at = utc_now()
        document = self._session.get(DocumentRecord, record.document_id)
        if document is not None:
            document.status = DocumentStatus.PARSING.value
            document.error_message = None
            document.updated_at = utc_now()
        self._session.commit()
        return _ingestion_job_from_record(record)

    def complete_parsed(
        self,
        *,
        job_id: UUID,
        parsed_text_uri: str,
        parsed_text_checksum: str,
        parsed_text_size_bytes: int,
        content_char_count: int,
    ) -> IngestionJob | None:
        record = self._session.get(IngestionJobRecord, str(job_id))
        if record is None:
            return None
        if IngestionJobStatus(record.status) is not IngestionJobStatus.PARSING:
            raise IngestionJobStateError(
                f"Ingestion job {job_id} cannot complete from status {record.status}."
            )

        record.status = IngestionJobStatus.PARSED.value
        record.parsed_text_uri = parsed_text_uri
        record.parsed_text_checksum = parsed_text_checksum
        record.parsed_text_size_bytes = parsed_text_size_bytes
        record.content_char_count = content_char_count
        record.completed_at = utc_now()
        document = self._session.get(DocumentRecord, record.document_id)
        if document is not None:
            document.status = DocumentStatus.PARSED.value
            document.error_message = None
            document.updated_at = utc_now()
        self._session.commit()
        return _ingestion_job_from_record(record)

    def fail(
        self,
        *,
        job_id: UUID,
        error_type: str,
        error_message: str,
    ) -> IngestionJob | None:
        record = self._session.get(IngestionJobRecord, str(job_id))
        if record is None:
            return None

        record.status = IngestionJobStatus.FAILED.value
        record.error_type = error_type
        record.error_message = error_message
        record.completed_at = utc_now()
        document = self._session.get(DocumentRecord, record.document_id)
        if document is not None:
            document.status = DocumentStatus.FAILED.value
            document.error_message = error_message
            document.updated_at = utc_now()
        self._session.commit()
        return _ingestion_job_from_record(record)


class DocumentChunkRepository:
    """Persistence operations for parsed document chunks."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_for_document(
        self,
        *,
        document_id: UUID,
        chunks: list[DocumentChunk],
    ) -> list[DocumentChunk] | None:
        document = self._session.get(DocumentRecord, str(document_id))
        if document is None:
            return None
        if any(chunk.document_id != document_id for chunk in chunks):
            raise DocumentChunkingError("All chunks must belong to the target document.")

        self._session.query(DocumentChunkRecord).filter(
            DocumentChunkRecord.document_id == str(document_id)
        ).delete(synchronize_session=False)
        document.status = DocumentStatus.CHUNKING.value
        document.error_message = None
        document.updated_at = utc_now()
        self._session.flush()

        for chunk in chunks:
            self._session.add(_document_chunk_to_record(chunk))

        document.status = DocumentStatus.CHUNKED.value
        document.updated_at = utc_now()
        self._session.commit()
        return self.list_for_document(document_id) or []

    def get(self, chunk_id: UUID) -> DocumentChunk | None:
        record = self._session.get(DocumentChunkRecord, str(chunk_id))
        if record is None:
            return None
        return _document_chunk_from_record(record)

    def list_for_document(self, document_id: UUID) -> list[DocumentChunk] | None:
        if self._session.get(DocumentRecord, str(document_id)) is None:
            return None

        statement = (
            select(DocumentChunkRecord)
            .where(DocumentChunkRecord.document_id == str(document_id))
            .order_by(DocumentChunkRecord.index)
        )
        return [_document_chunk_from_record(record) for record in self._session.scalars(statement)]


class ChunkEmbeddingRepository:
    """Persistence operations for chunk embeddings."""

    def __init__(self, session: Session, *, vector_store_mode: str | None = None) -> None:
        self._session = session
        self._vector_store_mode = vector_store_mode or get_vector_store_mode()

    def replace_for_document(
        self,
        *,
        document_id: UUID,
        model: str,
        embeddings: list[ChunkEmbedding],
    ) -> list[ChunkEmbedding] | None:
        document = self._session.get(DocumentRecord, str(document_id))
        if document is None:
            return None
        if any(embedding.document_id != document_id for embedding in embeddings):
            raise DocumentChunkingError("All embeddings must belong to the target document.")
        if any(embedding.model != model for embedding in embeddings):
            raise DocumentChunkingError("All embeddings must use the selected model.")
        use_pgvector = _use_pgvector(self._session, self._vector_store_mode)

        self._session.query(ChunkEmbeddingRecord).filter(
            ChunkEmbeddingRecord.document_id == str(document_id),
            ChunkEmbeddingRecord.model == model,
        ).delete(synchronize_session=False)
        for embedding in embeddings:
            self._session.add(_chunk_embedding_to_record(embedding))
        self._session.flush()
        if use_pgvector:
            self._write_pgvector_embeddings(embeddings)

        document.status = DocumentStatus.INDEXED.value
        document.error_message = None
        document.updated_at = utc_now()
        self._session.commit()
        return self.list_for_document(document_id=document_id, model=model) or []

    def list_for_document(
        self,
        *,
        document_id: UUID,
        model: str | None = None,
    ) -> list[ChunkEmbedding] | None:
        if self._session.get(DocumentRecord, str(document_id)) is None:
            return None

        statement = select(ChunkEmbeddingRecord).where(
            ChunkEmbeddingRecord.document_id == str(document_id)
        )
        if model is not None:
            statement = statement.where(ChunkEmbeddingRecord.model == model)
        statement = statement.order_by(ChunkEmbeddingRecord.created_at)
        return [_chunk_embedding_from_record(record) for record in self._session.scalars(statement)]

    def similarity_search(
        self,
        *,
        knowledge_base_id: UUID,
        query_vector: list[float],
        model: str,
        limit: int = 5,
    ) -> list[tuple[ChunkEmbedding, float]]:
        if _use_pgvector(self._session, self._vector_store_mode):
            return self._similarity_search_pgvector(
                knowledge_base_id=knowledge_base_id,
                query_vector=query_vector,
                model=model,
                limit=limit,
            )

        statement = (
            select(ChunkEmbeddingRecord)
            .join(DocumentRecord, ChunkEmbeddingRecord.document_id == DocumentRecord.id)
            .where(DocumentRecord.knowledge_base_id == str(knowledge_base_id))
            .where(ChunkEmbeddingRecord.model == model)
        )
        scored = [
            (_chunk_embedding_from_record(record), _cosine_similarity(query_vector, record.vector))
            for record in self._session.scalars(statement)
        ]
        return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]

    def _write_pgvector_embeddings(self, embeddings: list[ChunkEmbedding]) -> None:
        for embedding in embeddings:
            self._session.execute(
                text(
                    """
                    UPDATE chunk_embeddings
                    SET vector_pg = CAST(:vector AS vector)
                    WHERE id = :embedding_id
                    """
                ),
                {
                    "embedding_id": str(embedding.id),
                    "vector": _pgvector_literal(embedding.vector),
                },
            )

    def _similarity_search_pgvector(
        self,
        *,
        knowledge_base_id: UUID,
        query_vector: list[float],
        model: str,
        limit: int,
    ) -> list[tuple[ChunkEmbedding, float]]:
        query_literal = _pgvector_literal(query_vector)
        dimensions = len(query_vector)
        rows = self._session.execute(
            text(
                f"""
                SELECT
                    ce.id AS embedding_id,
                    1 - (
                        ce.vector_pg::vector({dimensions})
                        <=> CAST(:query_vector AS vector({dimensions}))
                    ) AS score
                FROM chunk_embeddings AS ce
                JOIN documents AS d ON ce.document_id = d.id
                WHERE d.knowledge_base_id = :knowledge_base_id
                    AND ce.model = :model
                    AND ce.dimensions = :dimensions
                    AND ce.vector_pg IS NOT NULL
                ORDER BY
                    ce.vector_pg::vector({dimensions})
                    <=> CAST(:query_vector AS vector({dimensions}))
                LIMIT :limit
                """
            ),
            {
                "knowledge_base_id": str(knowledge_base_id),
                "query_vector": query_literal,
                "model": model,
                "dimensions": dimensions,
                "limit": max(1, limit),
            },
        ).mappings()

        results: list[tuple[ChunkEmbedding, float]] = []
        for row in rows:
            record = self._session.get(ChunkEmbeddingRecord, str(row["embedding_id"]))
            if record is None:
                continue
            results.append((_chunk_embedding_from_record(record), float(row["score"])))
        return results


class MemoryRepository:
    """Persistence operations for scoped memory items."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        type: MemoryType,
        scope: str,
        content: dict[str, Any],
        source_run_id: UUID | None = None,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryItem:
        memory = MemoryItem(
            type=type,
            scope=scope,
            content=content,
            source_run_id=source_run_id,
            confidence=confidence,
            metadata=metadata or {},
        )
        self._session.add(_memory_item_to_record(memory))
        self._session.commit()
        return memory

    def get(self, memory_id: UUID) -> MemoryItem | None:
        record = self._session.get(MemoryItemRecord, str(memory_id))
        if record is None:
            return None
        return _memory_item_from_record(record)

    def list(
        self,
        *,
        scope: str | None = None,
        type: MemoryType | None = None,
        limit: int = 100,
    ) -> list[MemoryItem]:
        if limit < 1:
            raise ValueError("limit must be at least 1.")

        statement = select(MemoryItemRecord)
        if scope is not None:
            statement = statement.where(MemoryItemRecord.scope == scope)
        if type is not None:
            statement = statement.where(MemoryItemRecord.type == type.value)
        statement = statement.order_by(MemoryItemRecord.created_at).limit(limit)
        return [_memory_item_from_record(record) for record in self._session.scalars(statement)]

    def delete(self, memory_id: UUID) -> bool:
        record = self._session.get(MemoryItemRecord, str(memory_id))
        if record is None:
            return False

        self._session.delete(record)
        self._session.commit()
        return True


def _agent_to_record(agent: Agent) -> AgentRecord:
    return AgentRecord(
        id=str(agent.id),
        workspace_id=str(agent.workspace_id) if agent.workspace_id is not None else None,
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
        workspace_id=UUID(record.workspace_id) if record.workspace_id is not None else None,
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
        workspace_id=str(run.workspace_id) if run.workspace_id is not None else None,
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
        workspace_id=UUID(record.workspace_id) if record.workspace_id is not None else None,
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


def _worker_lease_to_record(lease: WorkerLease) -> WorkerLeaseRecord:
    return WorkerLeaseRecord(
        id=str(lease.id),
        run_id=str(lease.run_id),
        worker_id=lease.worker_id,
        lease_token=lease.lease_token,
        acquired_at=lease.acquired_at,
        heartbeat_at=lease.heartbeat_at,
        expires_at=lease.expires_at,
        released_at=lease.released_at,
    )


def _worker_lease_from_record(record: WorkerLeaseRecord) -> WorkerLease:
    return WorkerLease(
        id=UUID(record.id),
        run_id=UUID(record.run_id),
        worker_id=record.worker_id,
        lease_token=record.lease_token,
        acquired_at=record.acquired_at,
        heartbeat_at=record.heartbeat_at,
        expires_at=record.expires_at,
        released_at=record.released_at,
    )


def _worker_lease_record_is_active(record: WorkerLeaseRecord, now: datetime) -> bool:
    if record.released_at is not None:
        return False

    expires_at = record.expires_at
    comparison_now = now
    if expires_at.tzinfo is None and comparison_now.tzinfo is not None:
        comparison_now = comparison_now.replace(tzinfo=None)
    return expires_at > comparison_now


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
        provider_name=tool_call.provider_name,
        provider_tool_call_id=tool_call.provider_tool_call_id,
        raw_provider_payload=tool_call.raw_provider_payload,
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
        provider_name=record.provider_name,
        provider_tool_call_id=record.provider_tool_call_id,
        raw_provider_payload=record.raw_provider_payload,
        trace_id=record.trace_id,
        span_id=record.span_id,
        error_type=record.error_type,
        error_message=record.error_message,
        latency_ms=record.latency_ms,
        created_at=record.created_at,
    )


def _approval_to_record(approval: Approval) -> ApprovalRecord:
    return ApprovalRecord(
        id=str(approval.id),
        run_id=str(approval.run_id),
        tool_call_id=str(approval.tool_call_id),
        status=approval.status.value,
        reason=approval.reason,
        requested_by=str(approval.requested_by) if approval.requested_by is not None else None,
        reviewed_by=str(approval.reviewed_by) if approval.reviewed_by is not None else None,
        decision_note=approval.decision_note,
        trace_id=approval.trace_id,
        requested_at=approval.requested_at,
        resolved_at=approval.resolved_at,
    )


def _approval_from_record(record: ApprovalRecord) -> Approval:
    return Approval(
        id=UUID(record.id),
        run_id=UUID(record.run_id),
        tool_call_id=UUID(record.tool_call_id),
        status=ApprovalStatus(record.status),
        reason=record.reason,
        requested_by=UUID(record.requested_by) if record.requested_by is not None else None,
        reviewed_by=UUID(record.reviewed_by) if record.reviewed_by is not None else None,
        decision_note=record.decision_note,
        trace_id=record.trace_id,
        requested_at=record.requested_at,
        resolved_at=record.resolved_at,
    )


def _knowledge_base_to_record(knowledge_base: KnowledgeBase) -> KnowledgeBaseRecord:
    return KnowledgeBaseRecord(
        id=str(knowledge_base.id),
        name=knowledge_base.name,
        description=knowledge_base.description,
        status=knowledge_base.status.value,
        extra_metadata=knowledge_base.metadata,
        created_at=knowledge_base.created_at,
        updated_at=knowledge_base.updated_at,
    )


def _knowledge_base_from_record(record: KnowledgeBaseRecord) -> KnowledgeBase:
    return KnowledgeBase(
        id=UUID(record.id),
        name=record.name,
        description=record.description,
        status=KnowledgeBaseStatus(record.status),
        metadata=record.extra_metadata,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _document_to_record(document: Document) -> DocumentRecord:
    return DocumentRecord(
        id=str(document.id),
        knowledge_base_id=str(document.knowledge_base_id),
        title=document.title,
        source_uri=document.source_uri,
        mime_type=document.mime_type,
        checksum=document.checksum,
        size_bytes=document.size_bytes,
        status=document.status.value,
        error_message=document.error_message,
        extra_metadata=document.metadata,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _document_from_record(record: DocumentRecord) -> Document:
    return Document(
        id=UUID(record.id),
        knowledge_base_id=UUID(record.knowledge_base_id),
        title=record.title,
        source_uri=record.source_uri,
        mime_type=record.mime_type,
        checksum=record.checksum,
        size_bytes=record.size_bytes,
        status=DocumentStatus(record.status),
        error_message=record.error_message,
        metadata=record.extra_metadata,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _document_chunk_to_record(chunk: DocumentChunk) -> DocumentChunkRecord:
    return DocumentChunkRecord(
        id=str(chunk.id),
        document_id=str(chunk.document_id),
        index=chunk.index,
        content=chunk.content,
        start_char=chunk.start_char,
        end_char=chunk.end_char,
        token_count_estimate=chunk.token_count_estimate,
        checksum=chunk.checksum,
        extra_metadata=chunk.metadata,
        created_at=chunk.created_at,
    )


def _document_chunk_from_record(record: DocumentChunkRecord) -> DocumentChunk:
    return DocumentChunk(
        id=UUID(record.id),
        document_id=UUID(record.document_id),
        index=record.index,
        content=record.content,
        start_char=record.start_char,
        end_char=record.end_char,
        token_count_estimate=record.token_count_estimate,
        checksum=record.checksum,
        metadata=record.extra_metadata,
        created_at=record.created_at,
    )


def _chunk_embedding_to_record(embedding: ChunkEmbedding) -> ChunkEmbeddingRecord:
    return ChunkEmbeddingRecord(
        id=str(embedding.id),
        document_id=str(embedding.document_id),
        chunk_id=str(embedding.chunk_id),
        model=embedding.model,
        dimensions=embedding.dimensions,
        vector=embedding.vector,
        checksum=embedding.checksum,
        extra_metadata=embedding.metadata,
        created_at=embedding.created_at,
    )


def _chunk_embedding_from_record(record: ChunkEmbeddingRecord) -> ChunkEmbedding:
    return ChunkEmbedding(
        id=UUID(record.id),
        document_id=UUID(record.document_id),
        chunk_id=UUID(record.chunk_id),
        model=record.model,
        dimensions=record.dimensions,
        vector=record.vector,
        checksum=record.checksum,
        metadata=record.extra_metadata,
        created_at=record.created_at,
    )


def _memory_item_to_record(memory: MemoryItem) -> MemoryItemRecord:
    return MemoryItemRecord(
        id=str(memory.id),
        type=memory.type.value,
        scope=memory.scope,
        content=memory.content,
        source_run_id=str(memory.source_run_id) if memory.source_run_id is not None else None,
        confidence=memory.confidence,
        extra_metadata=memory.metadata,
        created_at=memory.created_at,
    )


def _memory_item_from_record(record: MemoryItemRecord) -> MemoryItem:
    return MemoryItem(
        id=UUID(record.id),
        type=MemoryType(record.type),
        scope=record.scope,
        content=record.content,
        source_run_id=UUID(record.source_run_id) if record.source_run_id is not None else None,
        confidence=record.confidence,
        metadata=record.extra_metadata,
        created_at=record.created_at,
    )


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _use_pgvector(session: Session, mode: str) -> bool:
    dialect_name = session.get_bind().dialect.name
    if mode == "json":
        return False
    if mode == "auto":
        return dialect_name == "postgresql"
    if mode == "pgvector":
        if dialect_name != "postgresql":
            raise VectorStoreConfigError(
                "AGENT_KERNEL_VECTOR_STORE=pgvector requires a PostgreSQL database."
            )
        return True
    raise VectorStoreConfigError(
        "AGENT_KERNEL_VECTOR_STORE must be one of: auto, json, pgvector."
    )


def _pgvector_literal(vector: list[float]) -> str:
    if not vector:
        raise VectorStoreConfigError("pgvector requires a non-empty vector.")

    values: list[str] = []
    for value in vector:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise VectorStoreConfigError("pgvector values must be numeric.")
        if not math.isfinite(float(value)):
            raise VectorStoreConfigError("pgvector values must be finite.")
        values.append(f"{float(value):.12g}")
    return f"[{','.join(values)}]"


def _principal_to_record(principal: Principal) -> PrincipalRecord:
    return PrincipalRecord(
        id=str(principal.id),
        type=principal.type.value,
        display_name=principal.display_name,
        disabled=principal.disabled,
        created_at=principal.created_at,
    )


def _principal_from_record(record: PrincipalRecord) -> Principal:
    return Principal(
        id=UUID(record.id),
        type=PrincipalType(record.type),
        display_name=record.display_name,
        disabled=record.disabled,
        created_at=record.created_at,
    )


def _workspace_to_record(workspace: Workspace) -> WorkspaceRecord:
    return WorkspaceRecord(
        id=str(workspace.id),
        name=workspace.name,
        slug=workspace.slug,
        status=workspace.status.value,
        created_at=workspace.created_at,
    )


def _workspace_from_record(record: WorkspaceRecord) -> Workspace:
    return Workspace(
        id=UUID(record.id),
        name=record.name,
        slug=record.slug,
        status=WorkspaceStatus(record.status),
        created_at=record.created_at,
    )


def _membership_to_record(membership: WorkspaceMembership) -> WorkspaceMembershipRecord:
    return WorkspaceMembershipRecord(
        principal_id=str(membership.principal_id),
        workspace_id=str(membership.workspace_id),
        role=membership.role.value,
        created_at=membership.created_at,
    )


def _membership_from_record(record: WorkspaceMembershipRecord) -> WorkspaceMembership:
    return WorkspaceMembership(
        principal_id=UUID(record.principal_id),
        workspace_id=UUID(record.workspace_id),
        role=WorkspaceRole(record.role),
        created_at=record.created_at,
    )


def _api_key_to_record(api_key: ApiKey) -> ApiKeyRecord:
    return ApiKeyRecord(
        id=str(api_key.id),
        workspace_id=str(api_key.workspace_id),
        principal_id=str(api_key.principal_id),
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        key_hash=api_key.key_hash,
        status=api_key.status.value,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
    )


def _api_key_from_record(record: ApiKeyRecord) -> ApiKey:
    return ApiKey(
        id=UUID(record.id),
        workspace_id=UUID(record.workspace_id),
        principal_id=UUID(record.principal_id),
        name=record.name,
        key_prefix=record.key_prefix,
        key_hash=record.key_hash,
        status=ApiKeyStatus(record.status),
        created_at=record.created_at,
        expires_at=record.expires_at,
        last_used_at=record.last_used_at,
    )


def _ingestion_job_to_record(job: IngestionJob) -> IngestionJobRecord:
    return IngestionJobRecord(
        id=str(job.id),
        document_id=str(job.document_id),
        status=job.status.value,
        parser_name=job.parser_name,
        parsed_text_uri=job.parsed_text_uri,
        parsed_text_checksum=job.parsed_text_checksum,
        parsed_text_size_bytes=job.parsed_text_size_bytes,
        content_char_count=job.content_char_count,
        error_type=job.error_type,
        error_message=job.error_message,
        extra_metadata=job.metadata,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


def _ingestion_job_from_record(record: IngestionJobRecord) -> IngestionJob:
    return IngestionJob(
        id=UUID(record.id),
        document_id=UUID(record.document_id),
        status=IngestionJobStatus(record.status),
        parser_name=record.parser_name,
        parsed_text_uri=record.parsed_text_uri,
        parsed_text_checksum=record.parsed_text_checksum,
        parsed_text_size_bytes=record.parsed_text_size_bytes,
        content_char_count=record.content_char_count,
        error_type=record.error_type,
        error_message=record.error_message,
        metadata=record.extra_metadata,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
    )
