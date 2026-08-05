# Day 60: Stuck-Run Detection and Recovery

## Goal

Add the first durable recovery path for runs whose worker lease expires before
the worker releases it.

## Scope

- Add expired worker lease listing to storage.
- Add a `StuckRunRecoveryService` in runtime.
- Recover expired leases for `running` and `resuming` runs by marking the run
  failed with `worker_lease_expired`.
- Release expired leases after recovery or safe skip.
- Add an explicit worker CLI mode for manual recovery.
- Add regression tests for recoverable, skipped, ignored, and invalid recovery
  cases.
- Update durable execution docs and milestone progress.

## Tasks

- [x] Add `WorkerLeaseRepository.list_expired`.
- [x] Add stuck-run recovery result models.
- [x] Add `StuckRunRecoveryService`.
- [x] Export recovery service from `kernel_runtime`.
- [x] Add `agent-kernel-worker --recover-stuck`.
- [x] Add recovery tests.
- [x] Update docs and milestones.

## Acceptance

- [x] Expired leases can be detected in expiration order.
- [x] Expired leases for `running` runs fail the run and release the lease.
- [x] Expired leases for `resuming` runs fail the run and release the lease.
- [x] Expired leases for queued runs are released without failing the run.
- [x] Non-expired leases are ignored.
- [x] Recovery is explicit and does not change normal worker polling behavior.

## Verification

- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_stuck_run_recovery.py tests/unit/test_storage_repositories.py`
- [x] `uv run pytest tests/unit/test_runtime_worker.py tests/integration/test_runtime_e2e.py`

## Notes

- Day 60 intentionally fails expired `running` and `resuming` runs instead of
  automatically requeueing them. This avoids blindly repeating side effects.
- Day 60 does not add Redis-backed scheduling.
- Day 60 does not add automatic recovery inside the normal worker loop.
- Day 62 should add durable retry visibility and worker restart tests on top of
  this recovery foundation.
