"""Queue adapters for durable run execution coordination."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

DEFAULT_RUN_QUEUE_NAME = "agent-kernel:runs:queued"


class RunQueue(Protocol):
    """Queue port for run ids waiting for worker attention."""

    def enqueue(self, run_id: UUID) -> None:
        """Add a run id to the queue."""
        ...

    def dequeue(self, *, limit: int = 100) -> tuple[UUID, ...]:
        """Remove and return up to ``limit`` run ids in FIFO order."""
        ...

    def size(self) -> int:
        """Return the approximate queue size."""
        ...


@dataclass
class InMemoryRunQueue:
    """Deterministic in-process run queue for tests and local composition."""

    _items: deque[UUID]

    def __init__(self) -> None:
        self._items = deque()

    def enqueue(self, run_id: UUID) -> None:
        self._items.append(run_id)

    def dequeue(self, *, limit: int = 100) -> tuple[UUID, ...]:
        if limit < 1:
            raise ValueError("Queue dequeue limit must be at least 1.")

        items: list[UUID] = []
        while self._items and len(items) < limit:
            items.append(self._items.popleft())
        return tuple(items)

    def size(self) -> int:
        return len(self._items)


class RedisQueueClient(Protocol):
    """Minimal Redis client protocol used by ``RedisRunQueue``.

    The protocol intentionally matches common redis-py methods without importing
    redis-py in the runtime package. Production wiring can pass a real Redis
    client; tests can pass a fake.
    """

    def rpush(self, name: str, *values: str) -> object:
        """Push values to the tail of a Redis list."""
        ...

    def lpop(self, name: str, count: int | None = None) -> object:
        """Pop one or more values from the head of a Redis list."""
        ...

    def llen(self, name: str) -> int:
        """Return the length of a Redis list."""
        ...


class RedisRunQueue:
    """Redis-backed run queue adapter.

    Redis is an acceleration and coordination layer only. Workers must still
    verify persisted run state in Postgres before executing any dequeued id.
    """

    def __init__(
        self,
        *,
        client: RedisQueueClient,
        queue_name: str = DEFAULT_RUN_QUEUE_NAME,
    ) -> None:
        if not queue_name.strip():
            raise ValueError("Redis queue_name must not be empty.")
        self._client = client
        self._queue_name = queue_name

    @property
    def queue_name(self) -> str:
        return self._queue_name

    def enqueue(self, run_id: UUID) -> None:
        self._client.rpush(self._queue_name, str(run_id))

    def dequeue(self, *, limit: int = 100) -> tuple[UUID, ...]:
        if limit < 1:
            raise ValueError("Queue dequeue limit must be at least 1.")

        raw = self._client.lpop(self._queue_name, limit)
        if raw is None:
            return ()
        raw_items = raw if isinstance(raw, list) else [raw]
        return tuple(UUID(_decode_redis_value(item)) for item in raw_items)

    def size(self) -> int:
        return int(self._client.llen(self._queue_name))


def _decode_redis_value(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, str):
        return value
    raise TypeError(f"Unsupported Redis queue value type: {type(value).__name__}")
