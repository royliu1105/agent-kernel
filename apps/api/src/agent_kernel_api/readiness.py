"""Dependency readiness without exposing connection strings or exception text."""

from __future__ import annotations

import asyncio
import importlib
import os
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import suppress
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

Mode = Literal["disabled", "optional", "required"]
Probe = Callable[[], object]


@dataclass(frozen=True)
class DependencyCheck:
    name: Literal["database", "redis", "s3"]
    mode: Mode
    probe: Probe | None = None


@dataclass(frozen=True)
class DependencyResult:
    name: str
    required: bool
    status: Literal["ok", "failed", "disabled"]
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"required": self.required, "status": self.status}
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass(frozen=True)
class ReadinessResult:
    dependencies: tuple[DependencyResult, ...]

    @property
    def ready(self) -> bool:
        return all(not item.required or item.status == "ok" for item in self.dependencies)

    @property
    def status_code(self) -> int:
        return 200 if self.ready else 503

    def to_dict(self) -> dict[str, object]:
        status = "ready" if self.ready else "not_ready"
        if self.ready and any(item.status == "failed" for item in self.dependencies):
            status = "degraded"
        return {
            "status": status,
            "dependencies": {item.name: item.to_dict() for item in self.dependencies},
        }


class ReadinessChecker:
    """At most one in-flight probe per dependency, shared by concurrent callers.

    HTTP deadlines do not cancel synchronous socket calls. Reusing an unfinished
    future prevents a failing dependency from building an unbounded thread queue.
    Native connect/read/pool timeouts must also be set on the supplied clients.
    """

    def __init__(
        self,
        checks: tuple[DependencyCheck, ...],
        *,
        timeout_seconds: float = 2.0,
        cache_seconds: float = 2.0,
        cleanup: tuple[Callable[[], object], ...] = (),
    ) -> None:
        if not 0 < timeout_seconds <= 10 or not 0 <= cache_seconds <= 30:
            raise ValueError("Readiness timeout/cache outside allowed range.")
        if (
            len({check.name for check in checks}) != len(checks)
            or len(checks) > 3
            or not any(c.name == "database" and c.mode == "required" for c in checks)
        ):
            raise ValueError("Readiness requires one required database and unique dependencies.")
        self._checks = checks
        self._timeout = timeout_seconds
        self._cache = cache_seconds
        self._pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="readiness")
        self._inflight: dict[str, tuple[float, Future[DependencyResult]]] = {}
        self._lock = Lock()
        self._closed = False
        self._cleanup = cleanup

    async def check(self) -> ReadinessResult:
        results = await asyncio.gather(*(self._check_one(check) for check in self._checks))
        return ReadinessResult(tuple(results))

    async def _check_one(self, check: DependencyCheck) -> DependencyResult:
        if check.mode == "disabled":
            return DependencyResult(check.name, False, "disabled")
        with self._lock:
            if self._closed:
                return DependencyResult(check.name, check.mode == "required", "failed", "closed")
            existing = self._inflight.get(check.name)
            now = monotonic()
            if existing is None or (existing[1].done() and now - existing[0] > self._cache):
                existing = (now, self._pool.submit(_run_probe, check))
                self._inflight[check.name] = existing
        started, future = existing
        if future.done():
            return future.result()
        try:
            return await asyncio.wait_for(
                asyncio.shield(asyncio.wrap_future(future)),
                timeout=max(0.001, self._timeout - (monotonic() - started)),
            )
        except TimeoutError:
            return DependencyResult(check.name, check.mode == "required", "failed", "timeout")

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            pending = [future for _, future in self._inflight.values() if not future.done()]
        self._pool.shutdown(wait=False, cancel_futures=True)
        remaining = len(pending)
        cleanup_lock = Lock()

        def finished(future: Future[DependencyResult] | None = None) -> None:
            nonlocal remaining
            with cleanup_lock:
                if future is not None:
                    remaining -= 1
                if remaining != 0:
                    return
                for close in self._cleanup:
                    close()

        if pending:
            for future in pending:
                future.add_done_callback(finished)
        else:
            finished()


def _run_probe(check: DependencyCheck) -> DependencyResult:
    error: str | None = None
    try:
        if check.probe is None:
            error = "not_configured"
        elif check.probe() is False:
            error = "unavailable"
    except ImportError:
        error = "missing_client"
    except Exception:
        # Dependency exceptions often contain credentials, SQL, URLs or bucket names.
        error = "unavailable"
    return DependencyResult(
        check.name, check.mode == "required", "failed" if error else "ok", error
    )


def _mode(env: Mapping[str, str], name: str, default: Mode) -> Mode:
    value = env.get(f"AGENT_KERNEL_READINESS_{name}", default).strip().lower()
    if value not in {"disabled", "optional", "required"}:
        raise ValueError(f"AGENT_KERNEL_READINESS_{name} must be disabled, optional or required.")
    if value == "disabled":
        return "disabled"
    return "required" if value == "required" else "optional"


def create_readiness_checker(
    session_factory: sessionmaker[Session],
    *,
    env: Mapping[str, str] | None = None,
    redis_probe: Probe | None = None,
    s3_probe: Probe | None = None,
    timeout_seconds: float = 2.0,
    cache_seconds: float = 2.0,
) -> ReadinessChecker:
    """Create once per API/worker process; call ``close`` during lifespan shutdown.

    Redis defaults optional unless the shared rate limiter requires it.
    S3 is required when selected as the object store. No external
    calls or optional imports occur until the first probe.
    """
    values = dict(os.environ if env is None else env)
    redis_url = values.get("REDIS_URL", "").strip()
    uses_s3 = values.get("AGENT_KERNEL_OBJECT_STORE_BACKEND", "local").strip().lower() == "s3"
    bucket = values.get("AGENT_KERNEL_S3_BUCKET", "").strip()
    limiter_enabled = int(values.get("AGENT_KERNEL_RATE_LIMIT_REQUESTS", "0")) > 0
    redis_mode = _mode(
        values, "REDIS", "required" if limiter_enabled else "optional" if redis_url else "disabled"
    )
    s3_mode = _mode(values, "S3", "required" if uses_s3 else "disabled")
    if limiter_enabled and redis_mode != "required":
        raise ValueError("Redis readiness must be required when the rate limiter is enabled.")
    if uses_s3 and s3_mode != "required":
        raise ValueError("S3 readiness must be required when the S3 backend is selected.")
    clients: dict[str, Any] = {}

    def database_check() -> None:
        with session_factory() as session:
            session.execute(text("SELECT 1"))
            session.execute(text("SELECT id FROM runs LIMIT 0"))

    def redis_check() -> object:
        if "redis" not in clients:
            redis = importlib.import_module("redis")
            retry = importlib.import_module("redis.retry")
            backoff = importlib.import_module("redis.backoff")
            clients["redis"] = redis.Redis.from_url(
                redis_url,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
                retry_on_timeout=False,
                retry=retry.Retry(backoff.NoBackoff(), 0),
                max_connections=1,
            )
        return clients["redis"].ping()

    def s3_check() -> None:
        if "s3" not in clients:
            boto3 = importlib.import_module("boto3")
            config_module = importlib.import_module("botocore.config")
            config = config_module.Config(
                connect_timeout=0.5,
                read_timeout=0.5,
                max_pool_connections=1,
                retries={"total_max_attempts": 1, "mode": "standard"},
            )
            clients["s3"] = boto3.session.Session().client(
                "s3",
                endpoint_url=values.get("AGENT_KERNEL_S3_ENDPOINT_URL") or None,
                region_name=values.get("AGENT_KERNEL_S3_REGION") or None,
                config=config,
            )
        clients["s3"].head_bucket(Bucket=bucket)

    def close_clients() -> None:
        for client in tuple(clients.values()):
            # Shutdown is best effort; never emit client exception text.
            with suppress(Exception):
                client.close()

    return ReadinessChecker(
        (
            DependencyCheck("database", "required", database_check),
            DependencyCheck(
                "redis",
                redis_mode,
                redis_probe or (redis_check if redis_url else None),
            ),
            DependencyCheck(
                "s3",
                s3_mode,
                s3_probe or (s3_check if bucket else None),
            ),
        ),
        timeout_seconds=timeout_seconds,
        cache_seconds=cache_seconds,
        cleanup=(close_clients,),
    )
