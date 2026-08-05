"""Provider-facing LLM contract types."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LLMToolChoice(StrEnum):
    AUTO = "auto"
    NONE = "none"
    REQUIRED = "required"


class LLMFinishReason(StrEnum):
    STOP = "stop"
    TOOL_CALLS = "tool_calls"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"
    UNKNOWN = "unknown"


class ProviderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LLMMessage(ProviderModel):
    role: MessageRole
    content: str
    name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMToolDefinition(ProviderModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object"})


class LLMToolCall(ProviderModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class LLMRequest(ProviderModel):
    model: str
    messages: tuple[LLMMessage, ...]
    temperature: float = 0.0
    max_output_tokens: int | None = None
    tools: tuple[LLMToolDefinition, ...] = ()
    tool_choice: LLMToolChoice | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMUsage(ProviderModel):
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0


class LLMResponse(ProviderModel):
    provider: str
    model: str
    text: str
    usage: LLMUsage = Field(default_factory=LLMUsage)
    finish_reason: LLMFinishReason = LLMFinishReason.STOP
    tool_calls: tuple[LLMToolCall, ...] = ()
    raw: dict[str, Any] = Field(default_factory=dict)


class LLMProviderError(RuntimeError):
    """Base error raised by provider implementations."""

    def __init__(self, message: str, *, error_type: str = "provider_error") -> None:
        self.error_type = error_type
        super().__init__(message)


class LLMProvider(Protocol):
    """Async interface implemented by all LLM providers."""

    @property
    def name(self) -> str:
        """Stable provider name used in traces, events, and eval output."""

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a single non-streaming completion."""
