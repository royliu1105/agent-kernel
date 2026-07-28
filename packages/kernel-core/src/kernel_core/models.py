"""Initial Agent Kernel domain models.

These models are intentionally infrastructure-free. They must not import API,
storage, provider, or framework implementation code.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


class AgentStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class RunStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    RESUMING = "resuming"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class RunStepType(StrEnum):
    MODEL_CALL = "model_call"
    TOOL_CALL = "tool_call"
    RETRIEVAL = "retrieval"
    APPROVAL = "approval"
    MEMORY = "memory"
    FINAL = "final"


class RunStepStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunEventType(StrEnum):
    RUN_CREATED = "run_created"
    RUN_QUEUED = "run_queued"
    RUN_STARTED = "run_started"
    RUN_WAITING_APPROVAL = "run_waiting_approval"
    RUN_RESUMING = "run_resuming"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_CANCELED = "run_canceled"
    STEP_CREATED = "step_created"
    STEP_UPDATED = "step_updated"
    TOOL_CALL_REQUESTED = "tool_call_requested"
    POLICY_EVALUATED = "policy_evaluated"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"


class ToolCallStatus(StrEnum):
    REQUESTED = "requested"
    POLICY_CHECKED = "policy_checked"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DENIED = "denied"
    TIMED_OUT = "timed_out"


class ApprovalStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELED = "canceled"


class RiskLevel(StrEnum):
    READ_ONLY = "read_only"
    EXTERNAL_WRITE = "external_write"
    FILESYSTEM_WRITE = "filesystem_write"
    NETWORK = "network"
    DANGEROUS = "dangerous"


class KernelModel(BaseModel):
    """Base model for domain objects."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Agent(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = ""
    status: AgentStatus = AgentStatus.ACTIVE
    prompt_id: UUID | None = None
    default_model_policy_id: UUID | None = None
    memory_policy: dict[str, Any] = Field(default_factory=dict)
    tool_policy: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class Run(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    status: RunStatus = RunStatus.CREATED
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    trace_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    input_tokens_total: int = 0
    output_tokens_total: int = 0
    estimated_cost_total: float = 0.0
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)


class RunStep(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    index: int
    type: RunStepType
    status: RunStepStatus = RunStepStatus.CREATED
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    trace_id: str | None = None
    span_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    latency_ms: int | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)


class RunEvent(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    sequence: int
    type: RunEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ToolCall(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    step_id: UUID | None = None
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    status: ToolCallStatus = ToolCallStatus.REQUESTED
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    requires_approval: bool = False
    approval_id: UUID | None = None
    trace_id: str | None = None
    span_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Approval(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    tool_call_id: UUID
    status: ApprovalStatus = ApprovalStatus.REQUESTED
    reason: str
    requested_by: UUID | None = None
    reviewed_by: UUID | None = None
    decision_note: str | None = None
    trace_id: str | None = None
    requested_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None
