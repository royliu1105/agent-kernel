"""Tool contract models."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from kernel_core import RiskLevel
from pydantic import BaseModel, ConfigDict, Field

JsonSchema = dict[str, Any]


class ToolModel(BaseModel):
    """Base model for tool package value objects."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ToolMetadata(ToolModel):
    """Metadata used by registry, policy, and future provider tool schemas."""

    name: str
    description: str
    input_schema: JsonSchema = Field(default_factory=lambda: {"type": "object"})
    output_schema: JsonSchema | None = None
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    timeout_ms: int = Field(default=1_000, ge=1)
    enabled: bool = True
    retry_safe: bool | None = None


class ToolExecutionContext(ToolModel):
    """Trusted runtime context, never populated from model tool arguments."""

    run_id: UUID | None = None
    workspace_id: UUID | None = None
    tool_call_id: UUID | None = None


class ToolRequest(ToolModel):
    """Request to execute a registered tool."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    context: ToolExecutionContext = Field(default_factory=ToolExecutionContext)


class ToolResult(ToolModel):
    """Result returned by a successful tool execution."""

    tool_name: str
    output: dict[str, Any]
