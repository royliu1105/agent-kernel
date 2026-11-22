"""Credential-free MCP log lookup for the local troubleshooting showcase.

Returns fixture spans for known TraceIds. Not a real log platform and not used
by default ``make docker-up``.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

server = FastMCP("showcase-troubleshooting")

# Known demos: TRACE-OK has enough evidence; TRACE-THIN is sparse; others missing.
_FIXTURES: dict[str, dict[str, Any]] = {
    "TRACE-OK": {
        "trace_id": "TRACE-OK",
        "evidence_sufficient": True,
        "service": "checkout-api",
        "error_fingerprint": "redis_timeout_checkout_cart",
        "summary": "checkout-api timed out calling Redis cart cache during checkout.",
        "spans": [
            {
                "service": "edge-gateway",
                "operation": "HTTP POST /checkout",
                "duration_ms": 3200,
                "status": "ok",
            },
            {
                "service": "checkout-api",
                "operation": "CartService.load",
                "duration_ms": 3010,
                "status": "error",
                "error": "TimeoutError: Redis GET cart:{user} exceeded 3000ms",
            },
            {
                "service": "redis-cart",
                "operation": "GET",
                "duration_ms": 3005,
                "status": "error",
                "error": "connection pool exhausted",
            },
        ],
        "denoised_notes": [
            "Dropped 14 health-check spans",
            "Kept error subtree rooted at checkout-api → redis-cart",
        ],
    },
    "TRACE-THIN": {
        "trace_id": "TRACE-THIN",
        "evidence_sufficient": False,
        "service": "unknown",
        "error_fingerprint": None,
        "summary": "Only a gateway accept span; no downstream error body.",
        "spans": [
            {
                "service": "edge-gateway",
                "operation": "HTTP POST /checkout",
                "duration_ms": 12,
                "status": "ok",
            }
        ],
        "denoised_notes": ["Insufficient spans for root-cause claims"],
        "refusal_hint": "Do not invent a root cause; say evidence is insufficient.",
    },
}


@server.tool()
def trace_logs_lookup(trace_id: str) -> dict[str, Any]:
    """Fetch denoised mock link logs for a TraceId (fixture only)."""

    key = (trace_id or "").strip()
    if key in _FIXTURES:
        return dict(_FIXTURES[key])
    return {
        "trace_id": key or None,
        "evidence_sufficient": False,
        "service": None,
        "error_fingerprint": None,
        "summary": "No spans found for this TraceId in the mock log store.",
        "spans": [],
        "denoised_notes": ["Trace not present in fixture catalog"],
        "refusal_hint": "Do not invent a root cause; say the TraceId was not found.",
    }


if __name__ == "__main__":
    server.run(transport="stdio")
