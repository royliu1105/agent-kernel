import asyncio
from typing import Any

import pytest
from kernel_core import RiskLevel
from kernel_tools import (
    DuplicateToolError,
    EchoTool,
    ToolExecutionFailedError,
    ToolExecutor,
    ToolMetadata,
    ToolRegistry,
    ToolRequest,
    ToolResultTooLargeError,
    ToolTimeoutError,
    ToolValidationError,
    UnknownToolError,
)


def test_tool_registry_registers_and_lists_metadata() -> None:
    registry = ToolRegistry()
    tool = EchoTool()

    registry.register(tool)

    assert registry.get("echo") is tool
    assert registry.list_metadata() == (tool.metadata,)
    assert tool.metadata.risk_level is RiskLevel.READ_ONLY


def test_tool_registry_rejects_duplicate_tools() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    with pytest.raises(DuplicateToolError) as error_info:
        registry.register(EchoTool())

    assert error_info.value.error_type == "duplicate_tool"


def test_tool_registry_rejects_unknown_tools() -> None:
    registry = ToolRegistry()

    with pytest.raises(UnknownToolError) as error_info:
        registry.get("missing")

    assert error_info.value.error_type == "unknown_tool"


@pytest.mark.asyncio
async def test_tool_executor_executes_safe_echo_tool() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())
    executor = ToolExecutor(registry=registry)

    result = await executor.execute(
        ToolRequest(tool_name="echo", arguments={"message": "hello tools"})
    )

    assert result.tool_name == "echo"
    assert result.output == {"message": "hello tools"}


@pytest.mark.asyncio
async def test_tool_executor_validates_arguments_before_execution() -> None:
    tool = CountingTool()
    registry = ToolRegistry()
    registry.register(tool)
    executor = ToolExecutor(registry=registry)

    with pytest.raises(ToolValidationError) as error_info:
        await executor.execute(ToolRequest(tool_name="counting", arguments={"message": 42}))

    assert error_info.value.error_type == "invalid_tool_arguments"
    assert tool.execution_count == 0


@pytest.mark.asyncio
async def test_tool_executor_rejects_unknown_tool_execution() -> None:
    executor = ToolExecutor(registry=ToolRegistry())

    with pytest.raises(UnknownToolError) as error_info:
        await executor.execute(ToolRequest(tool_name="missing", arguments={}))

    assert error_info.value.error_type == "unknown_tool"


@pytest.mark.asyncio
async def test_tool_executor_converts_tool_errors() -> None:
    registry = ToolRegistry()
    registry.register(FailingTool())
    executor = ToolExecutor(registry=registry)

    with pytest.raises(ToolExecutionFailedError) as error_info:
        await executor.execute(ToolRequest(tool_name="failing", arguments={}))

    assert error_info.value.error_type == "tool_execution_failed"
    assert "boom" in str(error_info.value)


@pytest.mark.asyncio
async def test_tool_executor_enforces_timeout() -> None:
    registry = ToolRegistry()
    registry.register(SlowTool())
    executor = ToolExecutor(registry=registry)

    with pytest.raises(ToolTimeoutError) as error_info:
        await executor.execute(ToolRequest(tool_name="slow", arguments={}))

    assert error_info.value.error_type == "tool_timeout"


@pytest.mark.asyncio
async def test_tool_executor_enforces_result_size_limit() -> None:
    registry = ToolRegistry()
    registry.register(LargeResultTool())
    executor = ToolExecutor(registry=registry, max_result_bytes=10)

    with pytest.raises(ToolResultTooLargeError) as error_info:
        await executor.execute(ToolRequest(tool_name="large", arguments={}))

    assert error_info.value.error_type == "tool_result_too_large"


class CountingTool:
    def __init__(self) -> None:
        self.execution_count = 0

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="counting",
            description="Count executions.",
            input_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
                "additionalProperties": False,
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self.execution_count += 1
        return {"message": arguments["message"]}


class FailingTool:
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(name="failing", description="Fail deterministically.")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("boom")


class SlowTool:
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(name="slow", description="Sleep past timeout.", timeout_ms=1)

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.1)
        return {}


class LargeResultTool:
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(name="large", description="Return too much data.")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"value": "x" * 100}
