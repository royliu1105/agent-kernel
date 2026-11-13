import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from kernel_core import RiskLevel
from kernel_policy import (
    PolicyAwareToolExecutor,
    PolicyDecisionType,
    ToolApprovalRequiredError,
    ToolDeniedError,
    ToolPolicy,
    ToolPolicyEvaluator,
)
from kernel_tools import (
    EchoTool,
    ToolExecutionContext,
    ToolExecutor,
    ToolRegistry,
    ToolRequest,
    ToolTimeoutError,
    ToolValidationError,
)
from kernel_tools.external import (
    ExternalAccess,
    ExternalConfigurationError,
    ExternalToolContract,
    ExternalToolError,
    ExternalToolsConfig,
    HttpEndpoint,
    MCPBinding,
    MCPServerConfig,
    StdioEndpoint,
    load_external_tools,
)

SERVER = Path(__file__).parents[1] / "fixtures" / "external_mcp_server.py"


@pytest.fixture
def mcp_http_url() -> Iterator[str]:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, str(SERVER), "http", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(200):
            if process.poll() is not None:
                pytest.fail("MCP HTTP fixture exited during startup")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.025)
        else:
            pytest.fail("MCP HTTP fixture did not start")
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def config(*, http_url: str | None = None) -> ExternalToolsConfig:
    return ExternalToolsConfig(
        mcp=(
            MCPServerConfig(
                name="fixture",
                stdio=StdioEndpoint(command=sys.executable, args=(str(SERVER),))
                if not http_url
                else None,
                http=HttpEndpoint(url=http_url, allow_private_network=True) if http_url else None,
                access=ExternalAccess(allow_unscoped=True),
                bindings=(
                    MCPBinding(
                        remote_name="record", contract=ExternalToolContract(name="remote_record")
                    ),
                    MCPBinding(
                        kind="resource",
                        remote_name="fixture://state",
                        contract=ExternalToolContract(name="remote_state"),
                    ),
                    MCPBinding(
                        kind="prompt",
                        remote_name="greeting",
                        contract=ExternalToolContract(name="remote_greeting"),
                    ),
                    MCPBinding(
                        remote_name="slow",
                        contract=ExternalToolContract(name="remote_slow", timeout_ms=25),
                    ),
                ),
            ),
        )
    )


async def exercise(config_value: ExternalToolsConfig) -> int:
    registry = ToolRegistry()
    registry.register(EchoTool())
    async with load_external_tools(registry, config_value) as loaded:
        assert len(loaded.tool_names) == 4
        policy_executor = PolicyAwareToolExecutor(registry=registry)
        direct_executor = ToolExecutor(registry=registry)
        for name in ("remote_record", "remote_state", "remote_greeting"):
            assert registry.get(name).metadata.risk_level is RiskLevel.NETWORK
            with pytest.raises(ToolApprovalRequiredError):
                await policy_executor.execute(ToolRequest(tool_name=name))
        deny = PolicyAwareToolExecutor(
            registry=registry,
            evaluator=ToolPolicyEvaluator(
                ToolPolicy(
                    tool_decisions={
                        "remote_record": PolicyDecisionType.DENY,
                        "remote_state": PolicyDecisionType.DENY,
                        "remote_greeting": PolicyDecisionType.DENY,
                    }
                )
            ),
        )
        for name in ("remote_record", "remote_state", "remote_greeting"):
            with pytest.raises(ToolDeniedError):
                await deny.execute(ToolRequest(tool_name=name))
        state = await direct_executor.execute(ToolRequest(tool_name="remote_state"))
        assert json.loads(state.output["data"]["contents"][0]["text"])["calls"] == 0
        with pytest.raises(ToolValidationError):
            await direct_executor.execute(
                ToolRequest(
                    tool_name="remote_state",
                    arguments={"uri": "file:///secret"},
                )
            )
        with pytest.raises(ToolValidationError):
            await direct_executor.execute(
                ToolRequest(
                    tool_name="remote_record",
                    arguments={"message": 12},
                )
            )
        result = await direct_executor.execute(
            ToolRequest(
                tool_name="remote_record",
                arguments={"message": "hello"},
            )
        )
        record = result.output["data"]["structuredContent"]
        assert record["message"] == "hello"
        assert record["calls"] == 1
        assert record["secret_inherited"] is False
        assert result.output["untrusted"] is True
        assert "Ignore" not in registry.get("remote_record").metadata.description
        prompt = await direct_executor.execute(
            ToolRequest(
                tool_name="remote_greeting",
                arguments={"name": "Ada"},
            )
        )
        assert "Ada" in prompt.output["data"]["messages"][0]["content"]["text"]
        assert prompt.output["untrusted"] is True
        with pytest.raises(ToolTimeoutError):
            await direct_executor.execute(ToolRequest(tool_name="remote_slow"))
        retained_tool = registry.get("remote_record")
    assert [m.name for m in registry.list_metadata()] == ["echo"]
    with pytest.raises(ExternalToolError, match="closed"):
        await retained_tool.execute({"message": "cannot restart"})
    return int(record["pid"])


@pytest.mark.asyncio
async def test_mcp_stdio_policy_schemas_resources_prompts_and_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXTERNAL_TEST_SECRET", "not-for-subprocesses")
    pid = await exercise(config())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


@pytest.mark.asyncio
async def test_mcp_real_streamable_http_lifecycle(mcp_http_url: str) -> None:
    await exercise(config(http_url=mcp_http_url))


@pytest.mark.asyncio
async def test_mcp_workspace_denial_before_rpc() -> None:
    registry = ToolRegistry()
    value = config()
    server = value.mcp[0].model_copy(update={"access": ExternalAccess(workspace_ids=(uuid4(),))})
    async with load_external_tools(registry, ExternalToolsConfig(mcp=(server,))):
        with pytest.raises(ExternalToolError, match="access denied"):
            await ToolExecutor(registry=registry).execute(
                ToolRequest(
                    tool_name="remote_record",
                    arguments={"message": "denied"},
                    context=ToolExecutionContext(workspace_id=uuid4()),
                )
            )


@pytest.mark.asyncio
async def test_mcp_bad_metadata_load_is_atomic() -> None:
    value = config()
    server = value.mcp[0].model_copy(
        update={
            "bindings": (
                *value.mcp[0].bindings,
                MCPBinding(remote_name="invalid", contract=ExternalToolContract(name="bad")),
            )
        }
    )
    registry = ToolRegistry()
    registry.register(EchoTool())
    with pytest.raises(ExternalConfigurationError):
        async with load_external_tools(registry, ExternalToolsConfig(mcp=(server,))):
            pytest.fail("Bad metadata must prevent startup")
    assert [m.name for m in registry.list_metadata()] == ["echo"]


@pytest.mark.asyncio
async def test_mcp_empty_configuration_preserves_registry() -> None:
    registry = ToolRegistry()
    async with load_external_tools(registry, ExternalToolsConfig()) as loaded:
        assert loaded.tool_names == ()
        await asyncio.sleep(0)
