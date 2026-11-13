"""Deterministic contracts complement (not replace) the real Redis suite."""

from collections.abc import Callable
from uuid import uuid4

import pytest
from kernel_runtime.queue import QueueFullError, QueueUnavailableError, RedisRunQueue
from kernel_runtime.redis_support import (
    RateLimitUnavailableError,
    RedisSettings,
    RedisWorkspaceRateLimiter,
    create_run_queue,
)


class ScriptClient:
    def __init__(self, result: object = 1, *, fail: bool = False):
        self.result = result
        self.fail = fail
        self.calls: list[tuple[object, ...]] = []

    def eval(self, script: str, numkeys: int, *args: str | int) -> object:
        self.calls.append((numkeys, *args))
        if self.fail:
            raise OSError("redis://user:secret@host/0")
        return self.result

    def rpush(self, name: str, *values: str) -> object:
        raise AssertionError("Bounded queue must use atomic EVAL")

    def lpop(self, name: str, count: int | None = None) -> object:
        if self.fail:
            raise OSError("private backend details")
        return self.result

    def llen(self, name: str) -> int:
        if self.fail:
            raise OSError("private backend details")
        return 0


def test_factory_is_disabled_without_importing_redis_and_bounds_production_queue() -> None:
    assert create_run_queue(RedisSettings.from_env({})) is None
    client = ScriptClient()
    queue = create_run_queue(
        RedisSettings(queue_backend="redis", queue_max_length=12), client=client
    )
    assert queue is not None
    run_id = uuid4()
    queue.enqueue(run_id)
    assert client.calls[0][-2:] == (str(run_id), 12)


@pytest.mark.parametrize(
    "url",
    ["http://localhost", "redis://", "redis://host/x", "redis://host/0?socket_timeout=0"],
)
def test_rejects_unsafe_or_invalid_redis_urls(url: str) -> None:
    with pytest.raises(ValueError):
        RedisSettings(url=url)


def test_redis_settings_do_not_expose_credentials() -> None:
    settings = RedisSettings(url="rediss://user:private-password@localhost:6379/1")
    assert "private-password" not in repr(settings)
    with pytest.raises(ValueError, match="Invalid Redis configuration") as caught:
        RedisSettings.from_env({"REDIS_URL": "rediss://private-password@host/invalid"})
    assert "private-password" not in str(caught.value)
    with pytest.raises(ValueError):
        RedisSettings(socket_timeout_seconds=float("nan"))


def test_full_queue_and_transport_failure_are_distinct_but_both_fallback_eligible() -> None:
    with pytest.raises(QueueFullError):
        RedisRunQueue(client=ScriptClient(0), max_length=1).enqueue(uuid4())
    queue = RedisRunQueue(client=ScriptClient(fail=True), max_length=1)
    operations: list[Callable[[], object]] = [
        lambda: queue.enqueue(uuid4()),
        queue.dequeue,
        queue.size,
    ]
    for operation in operations:
        with pytest.raises(QueueUnavailableError) as caught:
            operation()
        assert "secret" not in str(caught.value)
        assert "private" not in str(caught.value)


def test_malformed_items_do_not_discard_valid_siblings_or_loop_unboundedly() -> None:
    valid = uuid4()
    client = ScriptClient([b"garbage", b"\xff", str(valid).encode()])
    counts: list[int] = []
    queue = RedisRunQueue(client=client, on_malformed=counts.append)
    assert queue.dequeue(limit=3) == (valid,)
    assert queue.malformed_items == 2
    assert counts == [2]
    with pytest.raises(ValueError, match="must not exceed"):
        queue.dequeue(limit=1001)


def test_limiter_one_atomic_operation_scopes_by_workspace_and_policy() -> None:
    client = ScriptClient([1, 4, 1000])
    limiter = RedisWorkspaceRateLimiter(client=client)
    a, b = uuid4(), uuid4()
    decision = limiter.check(a, limit=5, window_seconds=1)
    assert decision.allowed and decision.remaining == 4 and decision.retry_after_seconds == 0
    limiter.check(b, limit=5, window_seconds=1)
    assert client.calls[0][1] != client.calls[1][1]
    assert client.calls[0][-2:] == (5, 1000)
    client.result = [0, 0, 1201]
    assert limiter.check(a, limit=5, window_seconds=1).retry_after_seconds == 2


@pytest.mark.parametrize("result", [None, [], [1, -1, 100], [1, 4, -1], [2, 4, 100]])
def test_limiter_fails_closed_on_invalid_backend_response(result: object) -> None:
    with pytest.raises(RateLimitUnavailableError):
        RedisWorkspaceRateLimiter(client=ScriptClient(result)).check(
            uuid4(), limit=5, window_seconds=1
        )


def test_limiter_does_not_reveal_transport_credentials() -> None:
    with pytest.raises(RateLimitUnavailableError) as caught:
        RedisWorkspaceRateLimiter(client=ScriptClient(fail=True)).check(
            uuid4(), limit=5, window_seconds=1
        )
    assert "secret" not in str(caught.value)
