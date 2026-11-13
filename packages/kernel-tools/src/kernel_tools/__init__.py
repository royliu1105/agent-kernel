"""Tool registry and execution primitives for Agent Kernel."""

from kernel_tools.base import ContextualTool, Tool
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
from kernel_tools.models import ToolExecutionContext, ToolMetadata, ToolRequest, ToolResult
from kernel_tools.registry import ToolRegistry

__all__ = [
    "ContextualTool",
    "DuplicateToolError",
    "EchoTool",
    "Tool",
    "ToolDisabledError",
    "ToolError",
    "ToolExecutionContext",
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
