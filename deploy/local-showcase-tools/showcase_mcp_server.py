"""Credential-free MCP inventory tool for the local mock showcase profile.

Counts invocations so the happy-path script can prove approval gates the first
side effect. Not a product feature and not used by default ``make docker-up``.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

server = FastMCP("showcase-inventory")
calls = 0


@server.tool()
def inventory_lookup(item_id: str) -> dict[str, str | int]:
    """Look up a fixture inventory item. Side effects are counted."""

    global calls
    calls += 1
    return {
        "item_id": item_id,
        "availability": "in_stock",
        "calls": calls,
        "pid": os.getpid(),
    }


if __name__ == "__main__":
    server.run(transport="stdio")
