from collections import defaultdict, deque
from uuid import uuid4

import pytest
from kernel_runtime import DEFAULT_RUN_QUEUE_NAME, InMemoryRunQueue, RedisRunQueue


def test_in_memory_run_queue_enqueues_and_dequeues_fifo() -> None:
    first = uuid4()
    second = uuid4()
    queue = InMemoryRunQueue()

    queue.enqueue(first)
    queue.enqueue(second)
    dequeued = queue.dequeue(limit=1)

    assert dequeued == (first,)
    assert queue.size() == 1
    assert queue.dequeue(limit=10) == (second,)
    assert queue.size() == 0


def test_in_memory_run_queue_rejects_invalid_limit() -> None:
    queue = InMemoryRunQueue()

    with pytest.raises(ValueError, match="Queue dequeue limit must be at least 1"):
        queue.dequeue(limit=0)


def test_redis_run_queue_enqueues_and_dequeues_fifo_with_default_name() -> None:
    client = FakeRedisClient()
    queue = RedisRunQueue(client=client)
    first = uuid4()
    second = uuid4()

    queue.enqueue(first)
    queue.enqueue(second)

    assert queue.queue_name == DEFAULT_RUN_QUEUE_NAME
    assert client.rpush_calls == [
        (DEFAULT_RUN_QUEUE_NAME, str(first)),
        (DEFAULT_RUN_QUEUE_NAME, str(second)),
    ]
    assert queue.size() == 2
    assert queue.dequeue(limit=2) == (first, second)
    assert queue.size() == 0


def test_redis_run_queue_decodes_bytes_values() -> None:
    client = FakeRedisClient(return_bytes=True)
    queue = RedisRunQueue(client=client, queue_name="custom")
    run_id = uuid4()

    queue.enqueue(run_id)

    assert queue.dequeue(limit=10) == (run_id,)


def test_redis_run_queue_returns_empty_tuple_for_empty_queue() -> None:
    queue = RedisRunQueue(client=FakeRedisClient())

    assert queue.dequeue(limit=10) == ()


def test_redis_run_queue_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="Redis queue_name must not be empty"):
        RedisRunQueue(client=FakeRedisClient(), queue_name=" ")

    queue = RedisRunQueue(client=FakeRedisClient())
    with pytest.raises(ValueError, match="Queue dequeue limit must be at least 1"):
        queue.dequeue(limit=0)


def test_redis_run_queue_rejects_unsupported_value_type() -> None:
    queue = RedisRunQueue(client=FakeRedisClient(raw_items=[123]))

    with pytest.raises(TypeError, match="Unsupported Redis queue value type"):
        queue.dequeue(limit=1)


class FakeRedisClient:
    def __init__(
        self,
        *,
        return_bytes: bool = False,
        raw_items: list[object] | None = None,
    ) -> None:
        self._return_bytes = return_bytes
        self._lists: defaultdict[str, deque[object]] = defaultdict(deque)
        self.rpush_calls: list[tuple[str, str]] = []
        if raw_items is not None:
            self._lists[DEFAULT_RUN_QUEUE_NAME].extend(raw_items)

    def rpush(self, name: str, *values: str) -> int:
        for value in values:
            self.rpush_calls.append((name, value))
            stored: object = value.encode("utf-8") if self._return_bytes else value
            self._lists[name].append(stored)
        return len(self._lists[name])

    def lpop(self, name: str, count: int | None = None) -> object:
        if not self._lists[name]:
            return None
        if count is None:
            return self._lists[name].popleft()

        values: list[object] = []
        while self._lists[name] and len(values) < count:
            values.append(self._lists[name].popleft())
        return values

    def llen(self, name: str) -> int:
        return len(self._lists[name])
