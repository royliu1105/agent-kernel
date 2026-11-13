"""Tool protocol."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from kernel_tools.models import ToolExecutionContext, ToolMetadata


class Tool(Protocol):
    """Async interface implemented by all Agent Kernel tools."""

    @property
    def metadata(self) -> ToolMetadata:
        """Return stable metadata used for validation and policy decisions."""

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool after arguments have been validated."""


@runtime_checkable
class ContextualTool(Protocol):
    """Optional execution interface for tools accessing scoped resources."""

    async def execute_with_context(
        self, arguments: dict[str, Any], *, context: ToolExecutionContext
    ) -> dict[str, Any]:
        """Use trusted run context independently of validated tool arguments."""
