"""Tool protocol."""

from __future__ import annotations

from typing import Any, Protocol

from kernel_tools.models import ToolMetadata


class Tool(Protocol):
    """Async interface implemented by all Agent Kernel tools."""

    @property
    def metadata(self) -> ToolMetadata:
        """Return stable metadata used for validation and policy decisions."""

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool after arguments have been validated."""
