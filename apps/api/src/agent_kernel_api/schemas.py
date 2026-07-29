"""HTTP schemas for the Agent Kernel API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from kernel_core import (
    AgentStatus,
    ApprovalStatus,
    DocumentStatus,
    IngestionJobStatus,
    KnowledgeBaseStatus,
    MemoryType,
    RunEventType,
    RunStatus,
)
from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentCreateRequest(ApiModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)


class AgentResponse(ApiModel):
    id: UUID
    name: str
    description: str
    status: AgentStatus
    prompt_id: UUID | None
    default_model_policy_id: UUID | None
    memory_policy: dict[str, Any]
    tool_policy: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime


class RunCreateRequest(ApiModel):
    input: dict[str, Any] = Field(default_factory=dict)


class RunResumeRequest(ApiModel):
    approval_id: UUID | None = None


class RunResponse(ApiModel):
    id: UUID
    agent_id: UUID
    status: RunStatus
    input: dict[str, Any]
    output: dict[str, Any] | None
    trace_id: str | None
    error_type: str | None
    error_message: str | None
    input_tokens_total: int
    output_tokens_total: int
    estimated_cost_total: float
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class RunEventResponse(ApiModel):
    id: UUID
    run_id: UUID
    sequence: int
    type: RunEventType
    payload: dict[str, Any]
    trace_id: str | None
    created_at: datetime


class ApprovalResponse(ApiModel):
    id: UUID
    run_id: UUID
    tool_call_id: UUID
    status: ApprovalStatus
    reason: str
    requested_by: UUID | None
    reviewed_by: UUID | None
    decision_note: str | None
    trace_id: str | None
    requested_at: datetime
    resolved_at: datetime | None


class ApprovalApproveRequest(ApiModel):
    decision_note: str | None = Field(default=None, max_length=4000)


class ApprovalRejectRequest(ApiModel):
    reason: str = Field(min_length=1, max_length=4000)


class KnowledgeBaseCreateRequest(ApiModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeBaseResponse(ApiModel):
    id: UUID
    name: str
    description: str
    status: KnowledgeBaseStatus
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DocumentCreateRequest(ApiModel):
    title: str = Field(min_length=1, max_length=500)
    source_uri: str = Field(min_length=1, max_length=2000)
    mime_type: str | None = Field(default=None, max_length=255)
    checksum: str | None = Field(default=None, max_length=255)
    size_bytes: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentResponse(ApiModel):
    id: UUID
    knowledge_base_id: UUID
    title: str
    source_uri: str
    mime_type: str | None
    checksum: str | None
    size_bytes: int | None
    status: DocumentStatus
    error_message: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DocumentChunkResponse(ApiModel):
    id: UUID
    document_id: UUID
    index: int
    content: str
    start_char: int
    end_char: int
    token_count_estimate: int
    checksum: str
    metadata: dict[str, Any]
    created_at: datetime


class ChunkEmbeddingResponse(ApiModel):
    id: UUID
    document_id: UUID
    chunk_id: UUID
    model: str
    dimensions: int
    vector: list[float]
    checksum: str
    metadata: dict[str, Any]
    created_at: datetime


class DocumentIndexResponse(ApiModel):
    document_id: UUID
    model: str
    dimensions: int
    embedding_count: int


class RetrievalRequest(ApiModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=50)


class CitationResponse(ApiModel):
    knowledge_base_id: UUID
    document_id: UUID
    document_title: str
    document_source_uri: str
    chunk_id: UUID
    chunk_index: int
    start_char: int
    end_char: int


class RetrievalResultResponse(ApiModel):
    content: str
    score: float
    citation: CitationResponse
    metadata: dict[str, Any]


class RetrievalResponseModel(ApiModel):
    knowledge_base_id: UUID
    query: str
    model: str
    results: list[RetrievalResultResponse]


class MemoryCreateRequest(ApiModel):
    type: MemoryType
    scope: str = Field(min_length=1, max_length=255)
    content: dict[str, Any]
    source_run_id: UUID | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryResponse(ApiModel):
    id: UUID
    type: MemoryType
    scope: str
    content: dict[str, Any]
    source_run_id: UUID | None
    confidence: float
    metadata: dict[str, Any]
    created_at: datetime


class MemoryDeleteResponse(ApiModel):
    id: UUID
    deleted: bool


class IngestionJobResponse(ApiModel):
    id: UUID
    document_id: UUID
    status: IngestionJobStatus
    parser_name: str | None
    parsed_text_uri: str | None
    parsed_text_checksum: str | None
    parsed_text_size_bytes: int | None
    content_char_count: int | None
    error_type: str | None
    error_message: str | None
    metadata: dict[str, Any]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
