"""Queue adapters for durable run execution coordination."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

DEFAULT_RUN_QUEUE_NAME = "agent-kernel:runs:queued"
MAX_DEQUEUE_BATCH = 1000


class QueueUnavailableError(RuntimeError):
    """A queue hint could not be delivered; persisted runs still need polling."""


class QueueFullError(QueueUnavailableError):
    """The bounded hint queue is full. Do not roll back an already committed run."""


_BOUNDED_PUSH = """
if redis.call('LLEN', KEYS[1]) >= tonumber(ARGV[2]) then return 0 end
redis.call('RPUSH', KEYS[1], ARGV[1])
return 1
"""


@runtime_checkable
class RedisScriptClient(Protocol):
    def eval(self, script: str, numkeys: int, *keys_and_args: str | int) -> object: ...


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
        max_length: int | None = None,
        on_malformed: Callable[[int], None] | None = None,
    ) -> None:
        if not queue_name.strip():
            raise ValueError("Redis queue_name must not be empty.")
        if max_length is not None and max_length < 1:
            raise ValueError("Redis queue max_length must be positive.")
        if max_length is not None and not isinstance(client, RedisScriptClient):
            raise TypeError("A bounded Redis queue requires EVAL support.")
        self._client = client
        self._queue_name = queue_name
        self._max_length = max_length
        self._on_malformed = on_malformed
        self.malformed_items = 0

    @property
    def queue_name(self) -> str:
        return self._queue_name

    def enqueue(self, run_id: UUID) -> None:
        if not isinstance(run_id, UUID):
            raise TypeError("Queue run_id must be a UUID.")
        try:
            if self._max_length is None:
                self._client.rpush(self._queue_name, str(run_id))
            else:
                assert isinstance(self._client, RedisScriptClient)
                accepted = self._client.eval(
                    _BOUNDED_PUSH, 1, self._queue_name, str(run_id), self._max_length
                )
                if accepted == 0:
                    raise QueueFullError("Run hint queue is full; use database polling.")
                if accepted != 1:
                    raise QueueUnavailableError("Invalid Redis queue response.")
        except QueueUnavailableError:
            raise
        except Exception:
            raise QueueUnavailableError("Redis enqueue failed; use database polling.") from None

    def dequeue(self, *, limit: int = 100) -> tuple[UUID, ...]:
        if limit < 1:
            raise ValueError("Queue dequeue limit must be at least 1.")
        if limit > MAX_DEQUEUE_BATCH:
            raise ValueError(f"Queue dequeue limit must not exceed {MAX_DEQUEUE_BATCH}.")

        try:
            raw = self._client.lpop(self._queue_name, limit)
        except Exception:
            raise QueueUnavailableError("Redis dequeue failed; use database polling.") from None
        if raw is None:
            return ()
        raw_items = raw if isinstance(raw, list) else [raw]
        items: list[UUID] = []
        malformed = 0
        for item in raw_items:
            try:
                items.append(UUID(_decode_redis_value(item)))
            except (ValueError, UnicodeDecodeError):
                malformed += 1
        self.malformed_items += malformed
        if malformed and self._on_malformed is not None:
            # Never expose the untrusted payload or let telemetry lose valid hints.
            with suppress(Exception):
                self._on_malformed(malformed)
        return tuple(items)

    def size(self) -> int:
        try:
            return int(self._client.llen(self._queue_name))
        except Exception:
            raise QueueUnavailableError("Redis queue size lookup failed.") from None


def _decode_redis_value(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, str):
        return value
    raise TypeError(f"Unsupported Redis queue value type: {type(value).__name__}")
