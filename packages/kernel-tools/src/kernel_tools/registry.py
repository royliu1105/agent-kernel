"""Tool registry."""

from __future__ import annotations

from collections.abc import Iterable

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

    def register_many(self, tools: Iterable[Tool]) -> None:
        """Validate the whole batch before exposing any new tools."""
        pending: dict[str, Tool] = {}
        for tool in tools:
            name = tool.metadata.name
            if name in self._tools or name in pending:
                raise DuplicateToolError(name)
            pending[name] = tool
        self._tools.update(pending)

    def unregister(self, tool: Tool) -> None:
        """Remove only the exact instance owned by a closing lifecycle."""
        name = tool.metadata.name
        if self._tools.get(name) is tool:
            del self._tools[name]
