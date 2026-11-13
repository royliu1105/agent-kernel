"""Atomic registry loading with process-local async transport ownership."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass

from kernel_tools.external.config import ExternalToolsConfig
from kernel_tools.external.http import create_http_client
from kernel_tools.external.mcp import MCPTool, connect_mcp
from kernel_tools.external.openapi import OpenAPITool, load_openapi_tools
from kernel_tools.external.security import ExternalConfigurationError
from kernel_tools.registry import ToolRegistry


@dataclass(frozen=True)
class LoadedExternalTools:
    tool_names: tuple[str, ...]


@asynccontextmanager
async def load_external_tools(
    registry: ToolRegistry,
    config: ExternalToolsConfig | None = None,
) -> AsyncIterator[LoadedExternalTools]:
    """Hold this context in the API lifespan or worker main task until shutdown.

    The registry is unchanged on discovery/validation failure. Transport sessions
    must not be reused across processes/event loops. Stop accepting executions and
    drain or cancel active runs before leaving this context.
    """
    config = (config or ExternalToolsConfig()).model_copy(deep=True)
    loaded: list[MCPTool | OpenAPITool] = []
    started = False
    try:
        async with AsyncExitStack() as stack:
            for server in config.mcp:
                loaded.extend(await connect_mcp(stack, server))
            for api in config.openapi:
                client = await stack.enter_async_context(create_http_client(api.endpoint))
                loaded.extend(load_openapi_tools(client, api))
            registry.register_many(loaded)
            started = True
            try:
                yield LoadedExternalTools(tuple(tool.metadata.name for tool in loaded))
            finally:
                for tool in loaded:
                    tool.deactivate()
                    registry.unregister(tool)
    except Exception:
        if started:
            raise
        # SDK task groups can wrap discovery failures during cleanup. Normalize
        # outside the exit stack, without exposing remote errors or credentials.
        raise ExternalConfigurationError(
            "External tool startup failed; check configuration."
        ) from None


register_external_tools = load_external_tools
