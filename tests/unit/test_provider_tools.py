from typing import Any

from kernel_core import RiskLevel
from kernel_runtime import (
    tool_metadata_to_llm_tool_definition,
    tool_registry_to_llm_tool_definitions,
)
from kernel_tools import ToolMetadata, ToolRegistry


def test_tool_metadata_to_llm_tool_definition_copies_provider_visible_schema() -> None:
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
        "additionalProperties": False,
    }
    metadata = ToolMetadata(
        name="kb_search",
        description="Search the knowledge base.",
        input_schema=input_schema,
        output_schema={"type": "object"},
        risk_level=RiskLevel.READ_ONLY,
    )

    definition = tool_metadata_to_llm_tool_definition(metadata)
    input_schema["properties"]["query"]["description"] = "mutated later"

    assert definition.name == "kb_search"
    assert definition.description == "Search the knowledge base."
    assert definition.input_schema == {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
        "additionalProperties": False,
    }


def test_tool_registry_to_llm_tool_definitions_filters_disabled_tools() -> None:
    registry = ToolRegistry()
    registry.register(_StaticTool(name="enabled_tool", enabled=True))
    registry.register(_StaticTool(name="disabled_tool", enabled=False))

    definitions = tool_registry_to_llm_tool_definitions(registry)

    assert [definition.name for definition in definitions] == ["enabled_tool"]


class _StaticTool:
    def __init__(self, *, name: str, enabled: bool) -> None:
        self._metadata = ToolMetadata(
            name=name,
            description=f"{name} description.",
            input_schema={"type": "object"},
            enabled=enabled,
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return arguments
