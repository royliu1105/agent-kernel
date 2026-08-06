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
    TOOL_CALL_RETRYING = "tool_call_retrying"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    MEMORY_RETRIEVED = "memory_retrieved"
    MODEL_CALL_RETRYING = "model_call_retrying"
    MODEL_FALLBACK_SELECTED = "model_fallback_selected"


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


class KnowledgeBaseStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class DocumentStatus(StrEnum):
    REGISTERED = "registered"
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    CHUNKING = "chunking"
    CHUNKED = "chunked"
    EMBEDDING = "embedding"
    INDEXED = "indexed"
    FAILED = "failed"


class IngestionJobStatus(StrEnum):
    CREATED = "created"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class EvalRunStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class MemoryType(StrEnum):
    SHORT_TERM = "short_term"
    TASK_CONTEXT = "task_context"
    USER_PREFERENCE = "user_preference"
    LONG_TERM = "long_term"


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
    workspace_id: UUID | None = None
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
    workspace_id: UUID | None = None
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


class WorkerLease(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    worker_id: str = Field(min_length=1, max_length=255)
    lease_token: str = Field(min_length=1, max_length=255)
    acquired_at: datetime = Field(default_factory=utc_now)
    heartbeat_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime
    released_at: datetime | None = None


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
    provider_name: str | None = None
    provider_tool_call_id: str | None = None
    raw_provider_payload: dict[str, Any] | None = None
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


class KnowledgeBase(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = ""
    status: KnowledgeBaseStatus = KnowledgeBaseStatus.ACTIVE
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Document(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    knowledge_base_id: UUID
    title: str
    source_uri: str
    mime_type: str | None = None
    checksum: str | None = None
    size_bytes: int | None = None
    status: DocumentStatus = DocumentStatus.REGISTERED
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DocumentChunk(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    index: int
    content: str
    start_char: int
    end_char: int
    token_count_estimate: int
    checksum: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ChunkEmbedding(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    chunk_id: UUID
    model: str
    dimensions: int
    vector: list[float]
    checksum: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class IngestionJob(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    status: IngestionJobStatus = IngestionJobStatus.CREATED
    parser_name: str | None = None
    parsed_text_uri: str | None = None
    parsed_text_checksum: str | None = None
    parsed_text_size_bytes: int | None = None
    content_char_count: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class EvalRun(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=255)
    suite_type: str = Field(min_length=1, max_length=255)
    status: EvalRunStatus
    passed: bool
    case_count: int = Field(ge=0)
    passed_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    report: dict[str, Any]
    error_type: str | None = None
    error_message: str | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class MemoryItem(KernelModel):
    id: UUID = Field(default_factory=uuid4)
    type: MemoryType
    scope: str = Field(min_length=1, max_length=255)
    content: dict[str, Any]
    source_run_id: UUID | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
