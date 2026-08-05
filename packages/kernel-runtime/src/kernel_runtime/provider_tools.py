"""Adapters from Agent Kernel tool metadata to provider tool contracts."""

from __future__ import annotations

from copy import deepcopy

from kernel_providers import LLMToolDefinition
from kernel_tools import ToolMetadata, ToolRegistry


def tool_metadata_to_llm_tool_definition(metadata: ToolMetadata) -> LLMToolDefinition:
    """Convert internal tool metadata into the provider-facing tool definition."""

    return LLMToolDefinition(
        name=metadata.name,
        description=metadata.description,
        input_schema=deepcopy(metadata.input_schema),
    )


def tool_registry_to_llm_tool_definitions(registry: ToolRegistry) -> tuple[LLMToolDefinition, ...]:
    """Return enabled registry tools as provider-facing tool definitions."""

    return tuple(
        tool_metadata_to_llm_tool_definition(metadata)
        for metadata in registry.list_metadata()
        if metadata.enabled
    )
