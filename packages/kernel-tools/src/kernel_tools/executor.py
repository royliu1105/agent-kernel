"""Tool executor with schema validation and bounded results."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from jsonschema import ValidationError
from jsonschema.validators import validate

from kernel_tools.errors import (
    ToolDisabledError,
    ToolError,
    ToolExecutionFailedError,
    ToolResultTooLargeError,
    ToolTimeoutError,
    ToolValidationError,
)
from kernel_tools.models import ToolRequest, ToolResult
from kernel_tools.registry import ToolRegistry


class ToolExecutor:
    """Validate and execute registered tools."""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        max_result_bytes: int = 65_536,
    ) -> None:
        if max_result_bytes < 1:
            raise ValueError("max_result_bytes must be at least 1.")
        self._registry = registry
        self._max_result_bytes = max_result_bytes

    async def execute(self, request: ToolRequest) -> ToolResult:
        tool = self._registry.get(request.tool_name)
        metadata = tool.metadata
        if not metadata.enabled:
            raise ToolDisabledError(metadata.name)

        _validate_arguments(
            tool_name=metadata.name,
            schema=metadata.input_schema,
            arguments=request.arguments,
        )

        try:
            output = await asyncio.wait_for(
                tool.execute(request.arguments),
                timeout=metadata.timeout_ms / 1_000,
            )
        except TimeoutError as error:
            raise ToolTimeoutError(metadata.name, metadata.timeout_ms) from error
        except ToolError:
            raise
        except Exception as error:
            raise ToolExecutionFailedError(metadata.name, str(error)) from error

        _validate_output_shape(tool_name=metadata.name, output=output)
        _enforce_result_size(
            tool_name=metadata.name,
            output=output,
            max_result_bytes=self._max_result_bytes,
        )
        return ToolResult(tool_name=metadata.name, output=output)


def _validate_arguments(
    *,
    tool_name: str,
    schema: dict[str, Any],
    arguments: dict[str, Any],
) -> None:
    try:
        validate(instance=arguments, schema=schema)
    except ValidationError as error:
        raise ToolValidationError(tool_name, error.message) from error


def _validate_output_shape(*, tool_name: str, output: object) -> None:
    if not isinstance(output, dict):
        raise ToolExecutionFailedError(tool_name, "Tool output must be a JSON object.")


def _enforce_result_size(
    *,
    tool_name: str,
    output: dict[str, Any],
    max_result_bytes: int,
) -> None:
    try:
        serialized = json.dumps(output, sort_keys=True)
    except TypeError as error:
        raise ToolExecutionFailedError(
            tool_name,
            "Tool output must be JSON serializable.",
        ) from error
    if len(serialized.encode("utf-8")) > max_result_bytes:
        raise ToolResultTooLargeError(tool_name, max_result_bytes)
