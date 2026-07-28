"""Tool registry and execution primitives for Agent Kernel."""

from kernel_tools.base import Tool
from kernel_tools.builtins import EchoTool, create_default_tool_registry
from kernel_tools.errors import (
    DuplicateToolError,
    ToolDisabledError,
    ToolError,
    ToolExecutionFailedError,
    ToolResultTooLargeError,
    ToolTimeoutError,
    ToolValidationError,
    UnknownToolError,
)
from kernel_tools.executor import ToolExecutor
from kernel_tools.models import ToolMetadata, ToolRequest, ToolResult
from kernel_tools.registry import ToolRegistry

__all__ = [
    "DuplicateToolError",
    "EchoTool",
    "Tool",
    "ToolDisabledError",
    "ToolError",
    "ToolExecutionFailedError",
    "ToolExecutor",
    "ToolMetadata",
    "ToolRegistry",
    "ToolRequest",
    "ToolResult",
    "ToolResultTooLargeError",
    "ToolTimeoutError",
    "ToolValidationError",
    "UnknownToolError",
    "create_default_tool_registry",
]
