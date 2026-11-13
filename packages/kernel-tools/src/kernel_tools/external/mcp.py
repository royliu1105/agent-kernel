"""Official MCP SDK sessions adapted into the normal tool execution contract."""

from __future__ import annotations

import asyncio
import os
from contextlib import AsyncExitStack, suppress
from dataclasses import dataclass
from functools import partial
from typing import Any

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from pydantic import AnyUrl, BaseModel

from kernel_tools.errors import ToolTimeoutError
from kernel_tools.external.config import MCPBinding, MCPServerConfig
from kernel_tools.external.diagnostics import sdk_diagnostics_scope
from kernel_tools.external.http import create_http_client
from kernel_tools.external.security import (
    ExternalConfigurationError,
    ExternalToolError,
    bounded_result,
    metadata_for,
    require_access,
    sanitize_schema,
)
from kernel_tools.models import ToolExecutionContext, ToolMetadata


class MCPTool:
    """Tools, exact resources and prompts share policy/approval/timeout handling."""

    def __init__(
        self,
        connection: _MCPConnection,
        config: MCPServerConfig,
        binding: MCPBinding,
        schema: dict[str, Any],
    ) -> None:
        self._connection = connection
        self._config = config
        self._binding = binding
        self._metadata = metadata_for(binding.contract, schema)
        self._active = True

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata.model_copy(deep=True)

    def deactivate(self) -> None:
        self._active = False

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.execute_with_context(arguments, context=ToolExecutionContext())

    async def execute_with_context(
        self, arguments: dict[str, Any], *, context: ToolExecutionContext
    ) -> dict[str, Any]:
        require_access(self._config.access, context)
        if not self._active:
            raise ExternalToolError("External tool lifecycle is closed.")
        result: BaseModel
        try:
            async with asyncio.timeout(self._metadata.timeout_ms / 1_000):
                result = await self._connection.call(self._binding, arguments)
        except TimeoutError as error:
            raise ToolTimeoutError(self._metadata.name, self._metadata.timeout_ms) from error
        except ExternalToolError:
            raise
        except Exception:
            # Remote errors can contain credentials, URIs or arbitrary server prose.
            raise ExternalToolError("MCP operation failed.") from None
        return bounded_result(
            {
                "source": self._config.name,
                "untrusted": True,
                "data": result.model_dump(mode="json", exclude_none=True),
            }
        )


@dataclass(frozen=True)
class _CatalogEntry:
    binding: MCPBinding
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None


@dataclass(frozen=True)
class _Call:
    binding: MCPBinding
    arguments: dict[str, Any]
    result: asyncio.Future[BaseModel]


def _cancel_abandoned_call(
    task: asyncio.Task[BaseModel], result: asyncio.Future[BaseModel]
) -> None:
    if result.cancelled():
        task.cancel()


class _MCPConnection:
    """A dedicated task owns SDK cancel scopes, never the application lifespan.

    Calls on one connection are serialized. Failed/queued calls are not replayed;
    a later explicit call can reconnect after the original owner has exited.
    """

    def __init__(self, config: MCPServerConfig) -> None:
        self._config = config
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._queue: asyncio.Queue[_Call] = asyncio.Queue(maxsize=64)
        self._catalog: list[_CatalogEntry] | None = None
        self._closed = False

    async def start(self) -> list[_CatalogEntry]:
        async with self._lock:
            if self._closed:
                raise ExternalToolError("External tool lifecycle is closed.")
            if self._task is None or self._task.done():
                ready: asyncio.Future[list[_CatalogEntry]] = (
                    asyncio.get_running_loop().create_future()
                )
                self._task = asyncio.create_task(self._serve(ready), name="mcp-session-owner")
                try:
                    self._catalog = await asyncio.shield(ready)
                except BaseException:
                    # Retrieve/cancel startup futures and reap the owner even if
                    # the caller's discovery/deadline cancellation wins the race.
                    ready.cancel()
                    self._task.cancel()
                    await self._task
                    raise
            assert self._catalog is not None
            return self._catalog

    async def call(self, binding: MCPBinding, arguments: dict[str, Any]) -> BaseModel:
        await self.start()
        result: asyncio.Future[BaseModel] = asyncio.get_running_loop().create_future()
        try:
            self._queue.put_nowait(_Call(binding, arguments, result))
        except asyncio.QueueFull:
            raise ExternalToolError("MCP connection is busy.") from None
        return await result

    async def close(self) -> None:
        self._closed = True
        if self._task is not None:
            self._task.cancel()
            await self._task

    async def _serve(self, ready: asyncio.Future[list[_CatalogEntry]]) -> None:
        current: _Call | None = None
        operation: asyncio.Task[BaseModel] | None = None
        try:
            with sdk_diagnostics_scope():
                async with AsyncExitStack() as stack:
                    async with asyncio.timeout(self._config.discovery_timeout_ms / 1_000):
                        session = await _open_session(stack, self._config)
                        await session.initialize()
                        catalog = await _discover(session, self._config)
                        if self._catalog is not None and catalog != self._catalog:
                            raise ExternalConfigurationError(
                                "MCP catalog changed; restart required."
                            )
                    ready.set_result(catalog)
                    while True:
                        current = await self._queue.get()
                        if current.result.cancelled():
                            current = None
                            continue
                        operation = asyncio.create_task(
                            _invoke(session, current.binding, current.arguments)
                        )
                        # Caller cancellation stops this RPC, not the shared owner.
                        current.result.add_done_callback(partial(_cancel_abandoned_call, operation))
                        try:
                            response = await asyncio.shield(operation)
                        except asyncio.CancelledError:
                            owner = asyncio.current_task()
                            if owner is not None and owner.cancelling():
                                raise
                        except Exception:
                            if not current.result.done():
                                current.result.set_exception(
                                    ExternalToolError("MCP operation failed.")
                                )
                        else:
                            if not current.result.done():
                                current.result.set_result(response)
                        finally:
                            if operation is not None:
                                operation.cancel()
                            # Keep current on owner failure so final cleanup fails it.
                            owner = asyncio.current_task()
                            if owner is None or not owner.cancelling():
                                current = None
        except (Exception, asyncio.CancelledError):
            # SDK child failures may be ExceptionGroups. Do not leak their raw
            # messages or cancel the API/worker task that loaded this connection.
            pass
        finally:
            if operation is not None:
                operation.cancel()
                with suppress(Exception, asyncio.CancelledError):
                    await operation
            if not ready.done():
                ready.set_exception(ExternalToolError("MCP connection failed."))
            if current is not None and not current.result.done():
                current.result.set_exception(ExternalToolError("MCP connection failed."))
            while not self._queue.empty():
                pending = self._queue.get_nowait()
                if not pending.result.done():
                    pending.result.set_exception(ExternalToolError("MCP connection failed."))


async def _invoke(
    session: ClientSession, binding: MCPBinding, arguments: dict[str, Any]
) -> BaseModel:
    if binding.kind == "tool":
        result = await session.call_tool(binding.remote_name, arguments)
        if result.isError:
            raise ExternalToolError("MCP operation reported failure.")
        return result
    if binding.kind == "resource":
        return await session.read_resource(AnyUrl(binding.remote_name))
    return await session.get_prompt(binding.remote_name, arguments)


async def connect_mcp(stack: AsyncExitStack, config: MCPServerConfig) -> list[MCPTool]:
    connection = _MCPConnection(config)
    stack.push_async_callback(connection.close)
    catalog = await connection.start()
    return [MCPTool(connection, config, item.binding, item.input_schema) for item in catalog]


async def _open_session(stack: AsyncExitStack, config: MCPServerConfig) -> ClientSession:
    if config.stdio is not None:
        endpoint = config.stdio
        params = StdioServerParameters(
            command=endpoint.command,
            args=list(endpoint.args),
            env={name: value.get_secret_value() for name, value in endpoint.env.items()},
            cwd=endpoint.cwd,
        )
        # Do not route untrusted child stderr into the application's structured logs.
        stderr = stack.enter_context(open(os.devnull, "w"))  # noqa: SIM115
        read, write = await stack.enter_async_context(stdio_client(params, errlog=stderr))
    else:
        assert config.http is not None
        client = await stack.enter_async_context(create_http_client(config.http))
        read, write, _ = await stack.enter_async_context(
            streamable_http_client(config.http.url, http_client=client)
        )
    # Discovery and each invocation have separate outer deadlines. A session-wide
    # discovery timeout would silently truncate longer tool/resource/prompt calls.
    return await stack.enter_async_context(ClientSession(read, write))


async def _discover(session: ClientSession, config: MCPServerConfig) -> list[_CatalogEntry]:
    catalogs: dict[str, dict[str, Any]] = {}
    for kind in {binding.kind for binding in config.bindings}:
        catalog: dict[str, Any] = {}
        cursor: str | None = None
        cursors: set[str] = set()
        # Bound empty pages as well as item counts from an untrusted server.
        for _ in range(config.max_catalog_entries + 1):
            params = types.PaginatedRequestParams(cursor=cursor) if cursor else None
            entries: list[tuple[str, Any]]
            if kind == "tool":
                tool_page = await session.list_tools(params=params)
                entries = [(item.name, item) for item in tool_page.tools]
                cursor = tool_page.nextCursor
            elif kind == "resource":
                resource_page = await session.list_resources(params=params)
                entries = [(str(item.uri), item) for item in resource_page.resources]
                cursor = resource_page.nextCursor
            else:
                prompt_page = await session.list_prompts(params=params)
                entries = [(item.name, item) for item in prompt_page.prompts]
                cursor = prompt_page.nextCursor
            for name, entry in entries:
                if name in catalog:
                    raise ExternalConfigurationError("Duplicate MCP catalog entry.")
                catalog[name] = entry
            if len(catalog) > config.max_catalog_entries:
                raise ExternalConfigurationError("MCP catalog exceeds the configured limit.")
            if cursor is None:
                break
            if cursor in cursors:
                raise ExternalConfigurationError("MCP pagination cursor repeated.")
            cursors.add(cursor)
        else:
            raise ExternalConfigurationError("MCP catalog has too many pages.")
        catalogs[kind] = catalog

    tools: list[_CatalogEntry] = []
    for binding in config.bindings:
        item = catalogs[binding.kind].get(binding.remote_name)
        if item is None:
            raise ExternalConfigurationError("Configured MCP operation is not advertised.")
        schema: dict[str, Any]
        output_schema: dict[str, Any] | None = None
        if binding.kind == "tool":
            schema = sanitize_schema(item.inputSchema)
            # The SDK validates structured results using this original schema.
            # Reject unsafe references/complexity before any tool can be invoked.
            if item.outputSchema is not None:
                output_schema = sanitize_schema(item.outputSchema)
        elif binding.kind == "resource":
            schema = {"type": "object", "properties": {}, "additionalProperties": False}
        else:
            args = item.arguments or []
            if len({arg.name for arg in args}) != len(args):
                raise ExternalConfigurationError("Duplicate MCP prompt argument.")
            schema = sanitize_schema(
                {
                    "type": "object",
                    "properties": {arg.name: {"type": "string"} for arg in args},
                    "required": [arg.name for arg in args if arg.required],
                    "additionalProperties": False,
                }
            )
        tools.append(_CatalogEntry(binding, schema, output_schema))
    return tools
