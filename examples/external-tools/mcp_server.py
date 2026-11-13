"""Local, credential-free MCP inventory service for integration exercises."""

import argparse

from mcp.server.fastmcp import FastMCP

parser = argparse.ArgumentParser()
parser.add_argument("--http", action="store_true")
parser.add_argument("--port", type=int, default=8051)
args = parser.parse_args()
server = FastMCP("inventory", host="127.0.0.1", port=args.port, json_response=True)


@server.tool()
def inventory_lookup(item_id: str) -> dict[str, str]:
    """Look up an item in the example inventory."""
    return {"item_id": item_id, "availability": "unknown"}


@server.resource("inventory://terms")
def terms() -> str:
    return "Inventory entries in this example are fixtures, not purchasing advice."


@server.prompt()
def inventory_question(item_id: str) -> str:
    return f"Check the availability of inventory item {item_id}."


if __name__ == "__main__":
    server.run(transport="streamable-http" if args.http else "stdio")
