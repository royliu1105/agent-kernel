"""HTTP schemas for the Agent Kernel API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from kernel_core import AgentStatus, ApprovalStatus, RunEventType, RunStatus
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
