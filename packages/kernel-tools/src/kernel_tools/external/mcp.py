"""Official MCP SDK sessions adapted into the normal tool execution contract."""

from __future__ import annotations

import asyncio
import os
from contextlib import AsyncExitStack
from datetime import timedelta
from typing import Any

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from pydantic import AnyUrl, BaseModel

from kernel_tools.errors import ToolTimeoutError
from kernel_tools.external.config import MCPBinding, MCPServerConfig
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
        session: ClientSession,
        config: MCPServerConfig,
        binding: MCPBinding,
        schema: dict[str, Any],
    ) -> None:
        self._session = session
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
                if self._binding.kind == "tool":
                    tool_result = await self._session.call_tool(
                        self._binding.remote_name, arguments
                    )
                    if tool_result.isError:
                        raise ExternalToolError("MCP operation reported failure.")
                    result = tool_result
                elif self._binding.kind == "resource":
                    result = await self._session.read_resource(AnyUrl(self._binding.remote_name))
                else:
                    result = await self._session.get_prompt(self._binding.remote_name, arguments)
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


async def connect_mcp(stack: AsyncExitStack, config: MCPServerConfig) -> list[MCPTool]:
    """Enter and exit in the same lifespan task (SDK uses AnyIO cancel scopes)."""
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
    session = await stack.enter_async_context(
        ClientSession(
            read,
            write,
            read_timeout_seconds=timedelta(milliseconds=config.discovery_timeout_ms),
        )
    )
    async with asyncio.timeout(config.discovery_timeout_ms / 1_000):
        await session.initialize()
        return await _discover(session, config)


async def _discover(session: ClientSession, config: MCPServerConfig) -> list[MCPTool]:
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

    tools: list[MCPTool] = []
    for binding in config.bindings:
        item = catalogs[binding.kind].get(binding.remote_name)
        if item is None:
            raise ExternalConfigurationError("Configured MCP operation is not advertised.")
        schema: dict[str, Any]
        if binding.kind == "tool":
            schema = sanitize_schema(item.inputSchema)
            # The SDK validates structured results using this original schema.
            # Reject unsafe references/complexity before any tool can be invoked.
            if item.outputSchema is not None:
                sanitize_schema(item.outputSchema)
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
        tools.append(MCPTool(session, config, binding, schema))
    return tools
