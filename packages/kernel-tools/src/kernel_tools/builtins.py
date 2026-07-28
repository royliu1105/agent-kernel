"""Built-in safe tools."""

from __future__ import annotations

from typing import Any

from kernel_core import RiskLevel

from kernel_tools.models import ToolMetadata
from kernel_tools.registry import ToolRegistry


class EchoTool:
    """Deterministic read-only tool for testing and local development."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="echo",
            description="Return the provided message without side effects.",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                },
                "required": ["message"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                },
                "required": ["message"],
                "additionalProperties": False,
            },
            risk_level=RiskLevel.READ_ONLY,
            timeout_ms=1_000,
            enabled=True,
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        message = arguments["message"]
        return {"message": message}


def create_default_tool_registry() -> ToolRegistry:
    """Return the default safe built-in tools for local runtime execution."""

    registry = ToolRegistry()
    registry.register(EchoTool())
    return registry
