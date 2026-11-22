# Day 59: Worker Lease Model and Storage Foundation

## Goal

Start the durable execution track by adding the storage foundation for worker
leases, without changing worker execution behavior yet.

## Scope

- Add a `WorkerLease` domain model.
- Add `worker_leases` storage table and Alembic migration.
- Add `WorkerLeaseRepository` acquire, get-active, heartbeat, and release
  operations.
- Enforce one active lease per queued run at the repository level.
- Allow a queued run to be reacquired after an expired lease.
- Add unit tests for lease acquisition, duplicate denial, heartbeat, release,
  queued-only acquisition, expiration, and invalid inputs.
- Update durable execution docs and milestone progress.

## Tasks

- [x] Add `WorkerLease` core model.
- [x] Add `WorkerLeaseRecord` SQLAlchemy model.
- [x] Add `0011_worker_leases` migration.
- [x] Add `WorkerLeaseRepository`.
- [x] Export the repository from `kernel_storage`.
- [x] Add storage repository tests.
- [x] Update docs and milestones.

## Acceptance

- [x] A queued run can acquire a worker lease.
- [x] A created/non-queued run cannot acquire a worker lease.
- [x] A second worker cannot acquire an already active lease.
- [x] A lease can be heartbeated to extend its expiration.
- [x] A lease can be released.
- [x] An expired lease can be superseded by a new lease.
- [x] Migration revision id fits Alembic's version column.

## Verification

- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_storage_repositories.py tests/unit/test_migrations.py`
- [x] `uv run pytest tests/unit/test_runtime_worker.py tests/integration/test_runtime_e2e.py`

## Notes

- Day 59 does not switch `QueuedRunWorker` to lease-backed claiming.
- Day 59 does not implement stuck-run recovery.
- Day 59 does not add Redis-backed scheduling.
- Day 60 should wire worker recovery semantics on top of this lease foundation.
