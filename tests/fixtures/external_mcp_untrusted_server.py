"""Intentionally malformed wire peer for the actual MCP stdio client tests."""

import json
import sys
import time
from typing import Any

SENTINEL = "private-prompt-token-do-not-log-83719"

for line in sys.stdin:
    message = json.loads(line)
    if "id" not in message:
        continue
    result: dict[str, Any]
    if message["method"] == "initialize":
        result = {
            "protocolVersion": "2025-11-25",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "fixture", "version": "1"},
        }
        if sys.argv[-1] == "initialize":
            result["serverInfo"] = {"name": SENTINEL}
    elif message["method"] == "tools/list":
        result = {"tools": [{"name": "trigger", "inputSchema": {"type": "object"}}]}
    else:
        if sys.argv[-1] == "slow":
            time.sleep(1.2)
        print(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/progress",
                    "params": {"secret": SENTINEL},
                }
            ),
            flush=True,
        )
        result = {"content": [{"type": "text", "text": "ok"}]}
    print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
