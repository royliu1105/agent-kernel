"""Optional Redis wiring and atomic, fail-closed workspace admission limits.

These synchronous adapters must run in a thread when used from an async API.
Redis is not the durable run store or an exactly-once execution mechanism.
"""

from __future__ import annotations

import importlib
import math
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from kernel_runtime.queue import DEFAULT_RUN_QUEUE_NAME, RedisRunQueue, RedisScriptClient


@dataclass(frozen=True)
class RedisSettings:
    url: str = field(default="redis://127.0.0.1:6379/0", repr=False)
    queue_backend: str = "database"
    queue_name: str = DEFAULT_RUN_QUEUE_NAME
    queue_max_length: int = 10_000
    socket_timeout_seconds: float = 1.0
    connect_timeout_seconds: float = 1.0
    max_connections: int = 20
    rate_limit_prefix: str = "agent-kernel:rate-limit"

    def __post_init__(self) -> None:
        try:
            parsed = urlsplit(self.url)
            valid_url = (
                parsed.scheme in {"redis", "rediss"}
                and bool(parsed.hostname)
                and not parsed.query
                and not parsed.fragment
                and (not parsed.path.strip("/") or parsed.path[1:].isdigit())
                and (parsed.port is None or 0 < parsed.port <= 65535)
            )
        except ValueError:
            valid_url = False
        if not valid_url:
            raise ValueError("Redis URL must use redis/rediss with a host and numeric database.")
        if self.queue_backend not in {"database", "redis"}:
            raise ValueError("Run queue backend must be database or redis.")
        if not self.queue_name.strip() or not self.rate_limit_prefix.strip():
            raise ValueError("Redis key prefixes must not be empty.")
        if not 1 <= self.queue_max_length <= 1_000_000:
            raise ValueError("Redis queue max length must be between 1 and 1000000.")
        if not 1 <= self.max_connections <= 1000:
            raise ValueError("Redis max connections must be between 1 and 1000.")
        for value in (self.socket_timeout_seconds, self.connect_timeout_seconds):
            if not math.isfinite(value) or not 0 < value <= 30:
                raise ValueError("Redis timeouts must be greater than zero and at most 30 seconds.")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> RedisSettings:
        source = os.environ if env is None else env
        try:
            return cls(
                url=source.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
                queue_backend=source.get("AGENT_KERNEL_RUN_QUEUE_BACKEND", "database"),
                queue_name=source.get("AGENT_KERNEL_RUN_QUEUE_NAME", DEFAULT_RUN_QUEUE_NAME),
                queue_max_length=int(source.get("AGENT_KERNEL_RUN_QUEUE_MAX_LENGTH", "10000")),
                socket_timeout_seconds=float(source.get("AGENT_KERNEL_REDIS_TIMEOUT_SECONDS", "1")),
                connect_timeout_seconds=float(
                    source.get("AGENT_KERNEL_REDIS_CONNECT_TIMEOUT_SECONDS", "1")
                ),
                max_connections=int(source.get("AGENT_KERNEL_REDIS_MAX_CONNECTIONS", "20")),
                rate_limit_prefix=source.get(
                    "AGENT_KERNEL_RATE_LIMIT_PREFIX", "agent-kernel:rate-limit"
                ),
            )
        except ValueError:
            raise ValueError(
                "Invalid Redis configuration; check URL, bounds and backend."
            ) from None


def create_redis_client(settings: RedisSettings) -> Any:
    """Create a caller-owned client without I/O; call close() on application shutdown.

    Import is lazy so database-only installs do not require redis-py. URL query
    overrides are rejected; they must not disable timeouts or TLS verification.
    Command retries are disabled because a lost reply can follow a successful write.
    """
    try:
        redis = importlib.import_module("redis")
        retry = importlib.import_module("redis.retry")
        backoff = importlib.import_module("redis.backoff")
    except ImportError:
        raise RuntimeError("Redis support requires the redis-py dependency.") from None
    options: dict[str, object] = {
        "decode_responses": False,
        "socket_timeout": settings.socket_timeout_seconds,
        "socket_connect_timeout": settings.connect_timeout_seconds,
        "max_connections": settings.max_connections,
        "health_check_interval": 30,
        "retry": retry.Retry(backoff.NoBackoff(), 0),
        "retry_on_timeout": False,
    }
    if settings.url.startswith("rediss:"):
        options.update(ssl_cert_reqs="required", ssl_check_hostname=True)
    return redis.Redis.from_url(settings.url, **options)


def create_run_queue(
    settings: RedisSettings,
    *,
    client: Any | None = None,
    on_malformed: Callable[[int], None] | None = None,
) -> RedisRunQueue | None:
    """Database mode has no hint queue; Redis mode always has a bounded queue.

    Prefer passing an application-owned client so its lifecycle can be closed.
    """
    if settings.queue_backend == "database":
        return None
    return RedisRunQueue(
        client=client if client is not None else create_redis_client(settings),
        queue_name=settings.queue_name,
        max_length=settings.queue_max_length,
        on_malformed=on_malformed,
    )


class RateLimitUnavailableError(RuntimeError):
    """Admission cannot be decided. The API must return 503, not silently allow."""


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


_RATE_LIMIT = """
local count = tonumber(redis.call('GET', KEYS[1]) or '0')
local ttl = redis.call('PTTL', KEYS[1])
if count < 0 or (count > 0 and ttl < 0) then
    return redis.error_reply('invalid limiter state')
end
if count >= tonumber(ARGV[1]) then return {0, 0, ttl} end
count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('PEXPIRE', KEYS[1], ARGV[2])
    ttl = tonumber(ARGV[2])
end
return {1, tonumber(ARGV[1]) - count, ttl}
"""

_MULTI_RATE_LIMIT = """
local retry = 0
local remaining = 1000000
local ttl = tonumber(ARGV[#KEYS + 1])
for i, key in ipairs(KEYS) do
    local raw = redis.call('GET', key)
    if raw and raw ~= '0' and not string.match(raw, '^[1-9][0-9]*$') then
        return redis.error_reply('invalid limiter state')
    end
    local count = tonumber(raw or '0')
    local expires = redis.call('PTTL', key)
    if not count or count < 0 or count > 1000000 or (count > 0 and expires < 0) then
        return redis.error_reply('invalid limiter state')
    end
    if count >= tonumber(ARGV[i]) then retry = math.max(retry, math.max(1, expires)) end
end
if retry > 0 then return {0, 0, retry} end
for i, key in ipairs(KEYS) do
    local count = redis.call('INCR', key)
    if count == 1 then redis.call('PEXPIRE', key, ttl) end
    remaining = math.min(remaining, tonumber(ARGV[i]) - count)
end
return {1, remaining, ttl}
"""


class RedisWorkspaceRateLimiter:
    """Fixed window beginning at the first admitted request, shared by all replicas.

    One Lua operation checks, increments and sets expiry. Denied requests do not
    extend the window. This does not promise HA durability across Redis failover.
    """

    def __init__(self, *, client: RedisScriptClient, prefix: str = "agent-kernel:rate-limit"):
        if not prefix.strip():
            raise ValueError("Rate limit prefix must not be empty.")
        self._client = client
        self._prefix = prefix

    def check(self, workspace_id: UUID, *, limit: int, window_seconds: int) -> RateLimitDecision:
        if not isinstance(workspace_id, UUID):
            raise TypeError("Rate limit workspace_id must be a trusted UUID.")
        if not 1 <= limit <= 1_000_000 or not 1 <= window_seconds <= 86_400:
            raise ValueError("Rate limit/window must be positive and within configured bounds.")
        # Include the policy so a policy change cannot inherit an incompatible TTL.
        key = f"{self._prefix}:{workspace_id}:{limit}:{window_seconds}"
        try:
            raw = self._client.eval(_RATE_LIMIT, 1, key, limit, window_seconds * 1000)
            if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                raise ValueError("Invalid limiter response")
            admitted, remaining, ttl = (int(value) for value in raw)
            if admitted not in (0, 1) or not 0 <= remaining < limit or ttl < 0:
                raise ValueError("Invalid limiter response")
        except Exception:
            raise RateLimitUnavailableError("Workspace rate limit backend unavailable.") from None
        return RateLimitDecision(
            allowed=bool(admitted),
            remaining=remaining,
            retry_after_seconds=0 if admitted else max(1, math.ceil(ttl / 1000)),
        )

    def check_scopes(
        self,
        workspace_id: UUID,
        *,
        principal_id: UUID,
        api_key_id: UUID,
        workspace_limit: int = 0,
        principal_limit: int = 0,
        api_key_limit: int = 0,
        window_seconds: int = 60,
    ) -> RateLimitDecision:
        """Atomically admit all enabled quotas; principal/key quotas are workspace-local.

        No bucket is charged on denial or invalid state. Uses standalone Redis;
        the existing deployment contract does not support Redis Cluster sharding.
        """
        if not all(isinstance(item, UUID) for item in (workspace_id, principal_id, api_key_id)):
            raise TypeError("Admission identities must be trusted UUIDs.")
        limits = (workspace_limit, principal_limit, api_key_limit)
        if (
            not any(limits)
            or any(not 0 <= value <= 1_000_000 for value in limits)
            or not 1 <= window_seconds <= 86_400
        ):
            raise ValueError("Admission quotas/window are outside configured bounds.")
        scopes = (
            str(workspace_id),
            f"{workspace_id}:principal:{principal_id}",
            f"{workspace_id}:api-key:{api_key_id}",
        )
        enabled = [
            (f"{self._prefix}:{scope}:{limit}:{window_seconds}", limit)
            for scope, limit in zip(scopes, limits, strict=True)
            if limit
        ]
        try:
            raw = self._client.eval(
                _MULTI_RATE_LIMIT,
                len(enabled),
                *(key for key, _ in enabled),
                *(limit for _, limit in enabled),
                window_seconds * 1000,
            )
            if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                raise ValueError("Invalid limiter response")
            admitted, remaining, ttl = (int(value) for value in raw)
            if admitted not in (0, 1) or not 0 <= remaining < min(v for _, v in enabled) or ttl < 0:
                raise ValueError("Invalid limiter response")
        except Exception:
            raise RateLimitUnavailableError("Request admission backend unavailable.") from None
        return RateLimitDecision(
            allowed=bool(admitted),
            remaining=remaining,
            retry_after_seconds=0 if admitted else max(1, math.ceil(ttl / 1000)),
        )
