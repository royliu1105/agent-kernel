"""Framework-independent HTTP metrics without URL, query or tenant labels."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from contextlib import suppress
from time import monotonic
from typing import Any

from kernel_observability.metrics import MetricsRecorder

ASGIApp = Callable[..., Awaitable[None]]
_GROUPS = frozenset(
    {
        "health",
        "runs",
        "agents",
        "approvals",
        "memory",
        "knowledge-bases",
        "documents",
        "evals",
        "ingestion",
        "other",
        "unmatched",
    }
)
_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})


class HttpMetricsMiddleware:
    def __init__(self, app: ASGIApp, *, metrics: MetricsRecorder) -> None:
        self.app = app
        self.metrics = metrics

    async def __call__(
        self, scope: MutableMapping[str, Any], receive: ASGIApp, send: ASGIApp
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = monotonic()
        status_code = 500

        async def capture(message: MutableMapping[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, capture)
        finally:
            route = scope.get("route")
            tags = getattr(route, "tags", ())
            group = str(tags[0]) if tags else "other" if route else "unmatched"
            method = scope.get("method", "OTHER")
            labels = {
                "route_group": group if group in _GROUPS else "other",
                "method": method if method in _METHODS else "OTHER",
                "status_class": f"{status_code // 100}xx" if 100 <= status_code <= 599 else "other",
            }
            with suppress(Exception):
                self.metrics.increment("api_requests_total", labels=labels)
                self.metrics.observe(
                    "api_request_latency_ms", (monotonic() - started) * 1000, labels=labels
                )
