"""Persistence helpers for provider-native tool call responses."""

from __future__ import annotations

from kernel_core import RiskLevel, Run, ToolCall
from kernel_providers import LLMResponse, LLMToolCall
from kernel_storage import ToolCallRepository
from kernel_tools import ToolError, ToolRegistry


def persist_provider_tool_calls(
    *,
    running: Run,
    response: LLMResponse,
    tool_call_repository: ToolCallRepository,
    tool_registry: ToolRegistry,
) -> tuple[ToolCall, ...]:
    """Persist normalized provider-native tool calls without executing them."""

    return tuple(
        _persist_one_provider_tool_call(
            running=running,
            provider_name=response.provider,
            tool_call=tool_call,
            tool_call_repository=tool_call_repository,
            tool_registry=tool_registry,
        )
        for tool_call in response.tool_calls
    )


def _persist_one_provider_tool_call(
    *,
    running: Run,
    provider_name: str,
    tool_call: LLMToolCall,
    tool_call_repository: ToolCallRepository,
    tool_registry: ToolRegistry,
) -> ToolCall:
    persisted = tool_call_repository.create_provider_requested(
        run_id=running.id,
        provider_name=provider_name,
        provider_tool_call_id=tool_call.id,
        tool_name=tool_call.name,
        arguments=tool_call.arguments,
        risk_level=_risk_level_for_tool(tool_registry=tool_registry, tool_name=tool_call.name),
        raw_provider_payload=tool_call.raw,
        trace_id=running.trace_id,
    )
    if persisted is None:
        raise ValueError(f"Run {running.id} was not found.")
    return persisted


def _risk_level_for_tool(*, tool_registry: ToolRegistry, tool_name: str) -> RiskLevel:
    try:
        return tool_registry.get(tool_name).metadata.risk_level
    except ToolError:
        return RiskLevel.DANGEROUS
