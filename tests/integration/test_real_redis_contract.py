"""Opt in with a dedicated Redis 7+ service; never FLUSHDB or reuse application keys."""

import importlib.util
import os
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from kernel_runtime.queue import QueueFullError, QueueUnavailableError
from kernel_runtime.redis_support import (
    RateLimitDecision,
    RateLimitUnavailableError,
    RedisSettings,
    RedisWorkspaceRateLimiter,
    create_redis_client,
    create_run_queue,
)

SPEC = importlib.util.spec_from_file_location(
    "backend_drill", Path(__file__).parents[2] / "scripts" / "backend_drill.py"
)
assert SPEC is not None and SPEC.loader is not None
backend_drill = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = backend_drill
SPEC.loader.exec_module(backend_drill)
require_test_service = backend_drill.require_test_service
run_queue_drill = backend_drill.run_queue_drill


def settings() -> RedisSettings:
    url = os.environ.get("AGENT_KERNEL_TEST_REDIS_URL")
    if not url:
        pytest.skip("Set AGENT_KERNEL_TEST_REDIS_URL to a dedicated loopback Redis DB 15.")
    require_test_service(url, backend="redis")
    return RedisSettings(
        url=url,
        queue_backend="redis",
        queue_name=f"agent-kernel:drill:{uuid4().hex}",
        queue_max_length=10,
        rate_limit_prefix=f"agent-kernel:drill:{uuid4().hex}",
    )


def test_real_redis_queue_atomic_capacity_fifo_malformed_and_transport_errors() -> None:
    config = settings()
    client = create_redis_client(config)
    queue = create_run_queue(config, client=client)
    assert queue is not None
    try:

        def enqueue(_: int) -> bool:
            try:
                queue.enqueue(uuid4())
                return True
            except QueueFullError:
                return False

        with ThreadPoolExecutor(max_workers=16) as executor:
            accepted = list(executor.map(enqueue, range(64)))
        assert sum(accepted) == 10
        assert queue.size() == 10
        assert len(queue.dequeue(limit=10)) == 10
        first, second = uuid4(), uuid4()
        queue.enqueue(first)
        client.rpush(config.queue_name, b"bad", b"\xff")
        queue.enqueue(second)
        assert queue.dequeue() == (first, second)
        assert queue.malformed_items == 2
        assert queue.dequeue() == ()
        client.set(config.queue_name, "wrong-type")
        with pytest.raises(QueueUnavailableError):
            queue.dequeue()
        with pytest.raises(QueueUnavailableError):
            queue.enqueue(uuid4())
    finally:
        client.delete(config.queue_name)
        client.close()


def test_real_redis_workspace_limit_atomic_across_clients_and_expires() -> None:
    config = settings()
    clients = [create_redis_client(config), create_redis_client(config)]
    limiters = [
        RedisWorkspaceRateLimiter(client=c, prefix=config.rate_limit_prefix) for c in clients
    ]
    a, b = uuid4(), uuid4()
    keys = [f"{config.rate_limit_prefix}:{workspace}:7:2" for workspace in (a, b)]
    try:

        def check(index: int) -> Any:
            return limiters[index % 2].check(a, limit=7, window_seconds=2)

        with ThreadPoolExecutor(max_workers=16) as executor:
            decisions = list(executor.map(check, range(64)))
        assert sum(decision.allowed for decision in decisions) == 7
        assert all(
            1 <= decision.retry_after_seconds <= 2 for decision in decisions if not decision.allowed
        )
        assert limiters[1].check(b, limit=7, window_seconds=2).allowed
        assert 0 < clients[0].pttl(keys[0]) <= 2000
        time.sleep(2.1)
        assert limiters[1].check(a, limit=7, window_seconds=2).allowed
        clients[0].set(keys[0], "7")  # Missing TTL must fail closed, not permanently throttle.
        with pytest.raises(RateLimitUnavailableError):
            limiters[0].check(a, limit=7, window_seconds=2)
    finally:
        clients[0].delete(*keys)
        for client in clients:
            client.close()


def test_real_client_connection_failure_has_bounded_fail_closed_semantics() -> None:
    settings()  # Keep network contracts explicitly opted in alongside the real service.
    with socket.socket() as reserved_port:
        reserved_port.bind(("127.0.0.1", 0))
        port = reserved_port.getsockname()[1]
        config = RedisSettings(
            url=f"redis://127.0.0.1:{port}/15",
            queue_backend="redis",
            socket_timeout_seconds=0.05,
            connect_timeout_seconds=0.05,
        )
        client = create_redis_client(config)
        queue = create_run_queue(config, client=client)
        assert queue is not None
        started = time.monotonic()
        try:
            with pytest.raises(QueueUnavailableError):
                queue.enqueue(uuid4())
            with pytest.raises(QueueUnavailableError):
                queue.dequeue()
            with pytest.raises(RateLimitUnavailableError):
                RedisWorkspaceRateLimiter(client=client).check(uuid4(), limit=1, window_seconds=1)
            assert time.monotonic() - started < 5
        finally:
            client.close()


def test_multi_scope_quotas_are_atomic_independent_and_do_not_charge_denials() -> None:
    config = settings()
    clients = [create_redis_client(config), create_redis_client(config)]
    limiters = [
        RedisWorkspaceRateLimiter(client=c, prefix=config.rate_limit_prefix) for c in clients
    ]
    workspace, other, principal, second_principal, key, key2, key3 = (uuid4() for _ in range(7))

    def check(
        index: int, *, ws: UUID = workspace, user: UUID = principal, token: UUID = key
    ) -> RateLimitDecision:
        return limiters[index % 2].check_scopes(
            ws,
            principal_id=user,
            api_key_id=token,
            workspace_limit=5,
            principal_limit=3,
            api_key_limit=2,
            window_seconds=60,
        )

    try:
        with ThreadPoolExecutor(max_workers=12) as pool:
            decisions = list(pool.map(check, range(32)))
        assert sum(d.allowed for d in decisions) == 2
        workspace_key = f"{config.rate_limit_prefix}:{workspace}:5:60"
        principal_key = f"{config.rate_limit_prefix}:{workspace}:principal:{principal}:3:60"
        assert clients[0].get(workspace_key) == clients[0].get(principal_key) == b"2"
        assert check(0, token=key2).allowed  # Another key, same principal has one remaining.
        assert not check(1, token=key2).allowed
        assert check(0, user=second_principal, token=key3).allowed
        assert check(1, user=second_principal, token=key3).allowed
        assert not check(0, user=uuid4(), token=uuid4()).allowed  # Workspace exhausted.
        assert check(1, ws=other).allowed  # Quotas never cross the workspace boundary.
        assert all(1 <= d.retry_after_seconds <= 60 for d in decisions if not d.allowed)
    finally:
        keys = list(clients[0].scan_iter(match=f"{config.rate_limit_prefix}:*"))
        if keys:
            clients[0].delete(*keys)
        for client in clients:
            client.close()


def test_invalid_secondary_bucket_does_not_partially_charge_workspace() -> None:
    config = settings()
    client = create_redis_client(config)
    workspace, principal, key = uuid4(), uuid4(), uuid4()
    workspace_key = f"{config.rate_limit_prefix}:{workspace}:10:60"
    key_bucket = f"{config.rate_limit_prefix}:{workspace}:api-key:{key}:2:60"
    try:
        client.rpush(key_bucket, "wrongtype")
        with pytest.raises(RateLimitUnavailableError):
            RedisWorkspaceRateLimiter(client=client, prefix=config.rate_limit_prefix).check_scopes(
                workspace,
                principal_id=principal,
                api_key_id=key,
                workspace_limit=10,
                api_key_limit=2,
                window_seconds=60,
            )
        assert client.exists(workspace_key) == 0
    finally:
        client.delete(workspace_key, key_bucket)
        client.close()


@pytest.mark.parametrize("malformed", ["1e0", "01", "1.0", "+1", "-0", "99999999999999999999"])
def test_noncanonical_counter_does_not_charge_any_other_bucket(malformed: str) -> None:
    config = settings()
    client = create_redis_client(config)
    workspace, principal, token = uuid4(), uuid4(), uuid4()
    workspace_key = f"{config.rate_limit_prefix}:{workspace}:10:60"
    principal_key = f"{config.rate_limit_prefix}:{workspace}:principal:{principal}:10:60"
    token_key = f"{config.rate_limit_prefix}:{workspace}:api-key:{token}:2:60"
    try:
        client.set(token_key, malformed, ex=60)
        with pytest.raises(RateLimitUnavailableError):
            RedisWorkspaceRateLimiter(client=client, prefix=config.rate_limit_prefix).check_scopes(
                workspace,
                principal_id=principal,
                api_key_id=token,
                workspace_limit=10,
                principal_limit=10,
                api_key_limit=2,
                window_seconds=60,
            )
        assert client.exists(workspace_key, principal_key) == 0
        assert client.get(token_key) == malformed.encode()
    finally:
        client.delete(workspace_key, principal_key, token_key)
        client.close()


@pytest.mark.asyncio
async def test_real_queue_drill_recovers_rejected_and_lost_hints() -> None:
    report = await run_queue_drill(settings().url)
    assert report["passed"] and report["runs_recovered"] == 3
    assert report["worker_queue_fallbacks"] == 1
