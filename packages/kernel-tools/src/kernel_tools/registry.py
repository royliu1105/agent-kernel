"""Tool registry."""

from __future__ import annotations

from kernel_tools.base import Tool
from kernel_tools.errors import DuplicateToolError, UnknownToolError
from kernel_tools.models import ToolMetadata


class ToolRegistry:
    """In-memory registry for enabled tool implementations."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        tool_name = tool.metadata.name
        if tool_name in self._tools:
            raise DuplicateToolError(tool_name)
        self._tools[tool_name] = tool

    def get(self, tool_name: str) -> Tool:
        tool = self._tools.get(tool_name)
        if tool is None:
            raise UnknownToolError(tool_name)
        return tool

    def list_metadata(self) -> tuple[ToolMetadata, ...]:
        return tuple(tool.metadata for tool in self._tools.values())
