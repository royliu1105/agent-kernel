"""Real MCP SDK and guarded HTTP transport with a deterministic HTTPCore peer.

Only the network exchange is replaced: SDK framing, task groups, redirection,
session requests, and the application's transport/lifecycle remain real.
"""

import asyncio
import json
import logging
import sys
from collections.abc import AsyncIterable, Iterator
from pathlib import Path
from typing import Any, Literal

import httpcore
import pytest
from kernel_tools import ToolExecutor, ToolRegistry, ToolRequest, ToolTimeoutError
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

SENTINEL = "private-prompt-token-do-not-log-83719"


class MCPPeer:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, Any]]] = []
        self.failure: int | None = None
        self.delay = 0.0
        self.malformed_init = False
        self.malformed_notification = False
        self.changed_schema = False
        self.started = asyncio.Event()
        self.hold: asyncio.Event | None = None

    async def respond(self, request: httpcore.Request) -> httpcore.Response:
        assert isinstance(request.stream, AsyncIterable)
        message = json.loads(b"".join([part async for part in request.stream]))
        self.requests.append((request.url.target.decode(), message))
        method = message["method"]
        if "id" not in message:
            return httpcore.Response(202)
        result: dict[str, Any]
        if method == "initialize":
            result = {
                "protocolVersion": "2025-11-25",
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                "serverInfo": {"name": "fixture", "version": "1"},
            }
            if self.malformed_init:
                result["serverInfo"] = {"name": SENTINEL}
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "record",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "changed" if self.changed_schema else "value": {"type": "string"}
                            },
                        },
                    }
                ]
            }
        elif method == "resources/list":
            result = {"resources": [{"name": "state", "uri": "fixture://state"}]}
        elif method == "prompts/list":
            result = {"prompts": [{"name": "greeting"}]}
        else:
            self.started.set()
            if self.hold is not None:
                await self.hold.wait()
            if self.failure:
                status, self.failure = self.failure, None
                return httpcore.Response(
                    status,
                    headers={"Location": "/mcp/redirected"},
                    content=SENTINEL.encode(),
                )
            await asyncio.sleep(self.delay)
            if method == "tools/call":
                result = {"content": [{"type": "text", "text": "ok"}], "isError": False}
            elif method == "resources/read":
                result = {"contents": [{"uri": "fixture://state", "text": "ok"}]}
            else:
                assert method == "prompts/get"
                result = {"messages": [{"role": "user", "content": {"type": "text", "text": "ok"}}]}
        response = {"jsonrpc": "2.0", "id": message["id"], "result": result}
        if self.malformed_notification and method == "tools/call":
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/progress",
                "params": {
                    "secret": SENTINEL,
                },
            }
            body = "".join(
                f"event: message\ndata: {json.dumps(m)}\n\n"
                for m in (
                    notification,
                    response,
                )
            )
            return httpcore.Response(
                200, headers={"Content-Type": "text/event-stream"}, content=body.encode()
            )
        return httpcore.Response(
            200, headers={"Content-Type": "application/json"}, content=json.dumps(response).encode()
        )

    @property
    def operations(self) -> list[tuple[str, dict[str, Any]]]:
        return [
            (path, msg)
            for path, msg in self.requests
            if msg["method"] in {"tools/call", "resources/read", "prompts/get"}
        ]


@pytest.fixture
def peer(monkeypatch: pytest.MonkeyPatch) -> MCPPeer:
    peer = MCPPeer()

    async def respond(_pool: Any, request: httpcore.Request) -> httpcore.Response:
        return await peer.respond(request)

    monkeypatch.setattr(httpcore.AsyncConnectionPool, "handle_async_request", respond)
    return peer


@pytest.fixture
def plain_logs(caplog: pytest.LogCaptureFixture) -> Iterator[pytest.LogCaptureFixture]:
    # API bootstrap intentionally installs safe formatters process-wide. This
    # boundary test must prove SDK safety even with a plain downstream sink.
    previous = caplog.handler.formatter
    caplog.handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    try:
        yield caplog
    finally:
        caplog.handler.setFormatter(previous)


def configuration(*, discovery_ms: int = 1000, timeout_ms: int = 1000) -> ExternalToolsConfig:
    operations: tuple[tuple[Literal["tool", "resource", "prompt"], str, str], ...] = (
        ("tool", "record", "record"),
        ("resource", "fixture://state", "state"),
        ("prompt", "greeting", "greeting"),
    )
    return ExternalToolsConfig(
        mcp=(
            MCPServerConfig(
                name="fixture",
                http=HttpEndpoint(url="https://mcp.example/mcp"),
                access=ExternalAccess(allow_unscoped=True),
                discovery_timeout_ms=discovery_ms,
                bindings=tuple(
                    MCPBinding(
                        kind=kind,
                        remote_name=remote,
                        contract=ExternalToolContract(name=name, timeout_ms=timeout_ms),
                    )
                    for kind, remote, name in operations
                ),
            ),
        )
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [307, 308, 500])
@pytest.mark.parametrize("name", ["record", "state", "greeting"])
async def test_http_failure_is_one_send_owner_survives_and_later_call_recovers(
    peer: MCPPeer,
    status: int,
    name: str,
) -> None:
    registry = ToolRegistry()
    async with load_external_tools(registry, configuration()):
        assert registry.get(name).metadata.retry_safe is False
        peer.failure = status
        with pytest.raises(ExternalToolError):
            await ToolExecutor(registry=registry).execute(ToolRequest(tool_name=name))
        assert len(peer.operations) == 1
        assert peer.operations[0][0] == "/mcp"
        assert asyncio.current_task().cancelling() == 0  # type: ignore[union-attr]
        # No automatic replay, and no caller/lifespan cancellation. A *new* call
        # can establish a fresh reviewed session after a failed connection.
        result = await ToolExecutor(registry=registry).execute(ToolRequest(tool_name=name))
        assert result.output["untrusted"] is True
        assert len(peer.operations) == 2
        assert sum(message["method"] == "initialize" for _, message in peer.requests) == 2
    assert registry.list_metadata() == ()


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["record", "state", "greeting"])
async def test_discovery_deadline_does_not_cap_invocation(peer: MCPPeer, name: str) -> None:
    registry = ToolRegistry()
    async with load_external_tools(registry, configuration(discovery_ms=100, timeout_ms=1000)):
        peer.delay = 0.2
        await ToolExecutor(registry=registry).execute(ToolRequest(tool_name=name))
        assert len(peer.operations) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["record", "state", "greeting"])
async def test_timeout_is_classified_and_next_invocation_works(peer: MCPPeer, name: str) -> None:
    registry = ToolRegistry()
    async with load_external_tools(registry, configuration(timeout_ms=50)):
        peer.delay = 0.5
        with pytest.raises(ToolTimeoutError):
            await ToolExecutor(registry=registry).execute(ToolRequest(tool_name=name))
        peer.delay = 0
        await ToolExecutor(registry=registry).execute(ToolRequest(tool_name=name))
        assert len(peer.operations) == 2


@pytest.mark.asyncio
async def test_reconnect_rejects_changed_catalog_before_second_operation(peer: MCPPeer) -> None:
    registry = ToolRegistry()
    async with load_external_tools(registry, configuration()):
        peer.failure = 500
        with pytest.raises(ExternalToolError):
            await registry.get("record").execute({})
        peer.changed_schema = True
        with pytest.raises(ExternalToolError):
            await registry.get("record").execute({})
        assert len(peer.operations) == 1


@pytest.mark.asyncio
async def test_failed_connection_does_not_replay_queued_calls(peer: MCPPeer) -> None:
    registry = ToolRegistry()
    async with load_external_tools(registry, configuration()):
        peer.failure = 500
        peer.hold = asyncio.Event()
        first = asyncio.create_task(registry.get("record").execute({}))
        await asyncio.wait_for(peer.started.wait(), timeout=1)
        second = asyncio.create_task(registry.get("record").execute({}))
        await asyncio.sleep(0)
        peer.hold.set()
        results = await asyncio.wait_for(
            asyncio.gather(first, second, return_exceptions=True), timeout=2
        )
        assert all(isinstance(result, ExternalToolError) for result in results)
        assert len(peer.operations) == 1
        await registry.get("record").execute({})
        assert len(peer.operations) == 2


@pytest.mark.asyncio
async def test_cancelled_queued_call_is_not_dispatched(peer: MCPPeer) -> None:
    registry = ToolRegistry()
    async with load_external_tools(registry, configuration()):
        peer.hold = asyncio.Event()
        first = asyncio.create_task(registry.get("record").execute({}))
        await asyncio.wait_for(peer.started.wait(), timeout=1)
        second = asyncio.create_task(registry.get("record").execute({}))
        await asyncio.sleep(0)
        second.cancel()
        with pytest.raises(asyncio.CancelledError):
            await second
        peer.hold.set()
        await first
        await registry.get("record").execute({})
        assert len(peer.operations) == 2


@pytest.mark.asyncio
async def test_shutdown_fails_pending_call_without_cancelling_caller(peer: MCPPeer) -> None:
    registry = ToolRegistry()
    async with load_external_tools(registry, configuration()):
        peer.hold = asyncio.Event()
        pending = asyncio.create_task(registry.get("record").execute({}))
        await asyncio.wait_for(peer.started.wait(), timeout=1)
    with pytest.raises(ExternalToolError):
        await pending
    assert len(peer.operations) == 1
    assert not any(task.get_name() == "mcp-session-owner" for task in asyncio.all_tasks())


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", ["initialize", "notification"])
async def test_sdk_raw_diagnostics_do_not_reach_plain_log_handlers(
    peer: MCPPeer,
    plain_logs: pytest.LogCaptureFixture,
    scenario: Literal["initialize", "notification"],
) -> None:
    caplog = plain_logs
    caplog.set_level(logging.DEBUG)
    registry = ToolRegistry()
    if scenario == "initialize":
        peer.malformed_init = True
        with pytest.raises(ExternalConfigurationError):
            async with load_external_tools(registry, configuration()):
                pytest.fail("Malformed initialization must fail")
    else:
        async with load_external_tools(registry, configuration()):
            peer.malformed_notification = True
            await registry.get("record").execute({})
    assert caplog.records
    assert "External SDK diagnostic omitted" in caplog.text
    assert SENTINEL not in caplog.text
    assert all(SENTINEL not in repr(record.__dict__) for record in caplog.records)
    logging.warning("Application diagnostic remains visible")
    assert "Application diagnostic remains visible" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", ["initialize", "notification"])
async def test_stdio_sdk_diagnostics_are_safe(
    plain_logs: pytest.LogCaptureFixture,
    scenario: str,
) -> None:
    caplog = plain_logs
    caplog.set_level(logging.DEBUG)
    fixture = Path(__file__).parents[1] / "fixtures" / "external_mcp_untrusted_server.py"
    config = ExternalToolsConfig(
        mcp=(
            MCPServerConfig(
                name="untrusted",
                stdio=StdioEndpoint(command=sys.executable, args=(str(fixture), scenario)),
                access=ExternalAccess(allow_unscoped=True),
                bindings=(
                    MCPBinding(
                        remote_name="trigger", contract=ExternalToolContract(name="trigger")
                    ),
                ),
            ),
        )
    )
    registry = ToolRegistry()
    if scenario == "initialize":
        with pytest.raises(ExternalConfigurationError):
            async with load_external_tools(registry, config):
                pytest.fail("Malformed initialization must fail")
    else:
        async with load_external_tools(registry, config):
            await registry.get("trigger").execute({})
        assert "External SDK diagnostic omitted" in caplog.text
    assert SENTINEL not in caplog.text
    assert all(SENTINEL not in repr(record.__dict__) for record in caplog.records)


@pytest.mark.asyncio
async def test_stdio_invocation_can_outlast_discovery_deadline() -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "external_mcp_untrusted_server.py"
    config = ExternalToolsConfig(
        mcp=(
            MCPServerConfig(
                name="slow",
                stdio=StdioEndpoint(command=sys.executable, args=(str(fixture), "slow")),
                access=ExternalAccess(allow_unscoped=True),
                discovery_timeout_ms=1000,
                bindings=(
                    MCPBinding(
                        remote_name="trigger",
                        contract=ExternalToolContract(
                            name="trigger",
                            timeout_ms=3000,
                        ),
                    ),
                ),
            ),
        )
    )
    registry = ToolRegistry()
    async with load_external_tools(registry, config):
        result = await ToolExecutor(registry=registry).execute(ToolRequest(tool_name="trigger"))
        assert result.output["data"]["content"][0]["text"] == "ok"
