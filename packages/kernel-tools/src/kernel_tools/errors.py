"""Typed errors for tool registration and execution."""

from __future__ import annotations


class ToolError(RuntimeError):
    """Base error for tool package failures."""

    def __init__(self, message: str, *, error_type: str) -> None:
        self.error_type = error_type
        super().__init__(message)


class DuplicateToolError(ToolError):
    """Raised when a tool name is registered more than once."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            f"Tool {tool_name!r} is already registered.",
            error_type="duplicate_tool",
        )


class UnknownToolError(ToolError):
    """Raised when a tool is requested but not registered."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            f"Tool {tool_name!r} is not registered.",
            error_type="unknown_tool",
        )


class ToolDisabledError(ToolError):
    """Raised when a registered tool is disabled."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            f"Tool {tool_name!r} is disabled.",
            error_type="tool_disabled",
        )


class ToolValidationError(ToolError):
    """Raised when tool arguments fail schema validation."""

    def __init__(self, tool_name: str, message: str) -> None:
        super().__init__(
            f"Invalid arguments for tool {tool_name!r}: {message}",
            error_type="invalid_tool_arguments",
        )


class ToolExecutionFailedError(ToolError):
    """Raised when a tool raises an unexpected execution error."""

    def __init__(self, tool_name: str, message: str) -> None:
        super().__init__(
            f"Tool {tool_name!r} failed: {message}",
            error_type="tool_execution_failed",
        )


class ToolTimeoutError(ToolError):
    """Raised when a tool exceeds its timeout."""

    def __init__(self, tool_name: str, timeout_ms: int) -> None:
        super().__init__(
            f"Tool {tool_name!r} timed out after {timeout_ms} ms.",
            error_type="tool_timeout",
        )


class ToolResultTooLargeError(ToolError):
    """Raised when a tool result exceeds the configured serialized size limit."""

    def __init__(self, tool_name: str, max_result_bytes: int) -> None:
        super().__init__(
            f"Tool {tool_name!r} result exceeds {max_result_bytes} bytes.",
            error_type="tool_result_too_large",
        )
