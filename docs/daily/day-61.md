# Day 61: Redis Queue Adapter Foundation

## Goal

Add the queue adapter foundation for Redis-backed worker coordination while
keeping Postgres as the durable source of truth and preserving the existing
worker polling behavior.

## Scope

- Add a `RunQueue` port for queued run ids.
- Add deterministic `InMemoryRunQueue` for tests and local composition.
- Add `RedisRunQueue` adapter using a minimal redis-py-compatible client
  protocol.
- Define the default Redis list key for queued run notifications.
- Add tests for FIFO behavior, size, limit validation, bytes/string decoding,
  empty queue behavior, and invalid Redis payloads.
- Update durable execution docs and milestone progress.

## Tasks

- [x] Add `RunQueue` protocol.
- [x] Add `InMemoryRunQueue`.
- [x] Add `RedisQueueClient` protocol.
- [x] Add `RedisRunQueue`.
- [x] Export queue APIs from `kernel_runtime`.
- [x] Add queue adapter tests.
- [x] Update docs and milestones.

## Acceptance

- [x] Queue adapters enqueue and dequeue run ids in FIFO order.
- [x] Queue adapters reject invalid dequeue limits.
- [x] Redis adapter can decode string and byte values.
- [x] Redis adapter exposes queue size.
- [x] Redis adapter does not require a real Redis server in unit tests.
- [x] Existing worker behavior remains unchanged.

## Verification

- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_run_queue.py`
- [x] `uv run pytest tests/unit/test_runtime_worker.py tests/integration/test_runtime_e2e.py`

## Notes

- Redis remains a coordination and wakeup layer, not the source of truth.
- Postgres run state and worker leases remain authoritative.
- Day 61 does not wire Redis queueing into API queue or worker polling paths.
- Day 61 does not add a redis-py dependency; the adapter accepts any compatible
  client object.
- Day 62 should add durable retry visibility and worker restart tests before
  changing default queue behavior.
