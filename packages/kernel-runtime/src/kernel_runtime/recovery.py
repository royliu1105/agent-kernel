"""Stuck-run recovery for durable worker execution."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from kernel_core import RunStatus, WorkerLease
from kernel_storage import RunRepository, WorkerLeaseRepository
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class StuckRunRecoveryResult:
    """Recovery outcome for one expired worker lease."""

    run_id: UUID
    lease_id: UUID
    worker_id: str
    recovered: bool
    status: RunStatus | None
    reason: str


@dataclass(frozen=True)
class StuckRunRecoveryBatchResult:
    """Summary for one stuck-run recovery pass."""

    results: tuple[StuckRunRecoveryResult, ...]

    @property
    def inspected_count(self) -> int:
        return len(self.results)

    @property
    def recovered_count(self) -> int:
        return sum(1 for result in self.results if result.recovered)

    @property
    def skipped_count(self) -> int:
        return sum(1 for result in self.results if not result.recovered)


class StuckRunRecoveryService:
    """Recover runs associated with expired worker leases."""

    _recoverable_statuses = frozenset({RunStatus.RUNNING, RunStatus.RESUMING})

    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def recover_once(self, *, limit: int = 100) -> StuckRunRecoveryBatchResult:
        """Recover up to ``limit`` expired leases in expiration order."""

        if limit < 1:
            raise ValueError("Recovery limit must be at least 1.")

        with self._session_factory() as session:
            lease_repository = WorkerLeaseRepository(session)
            leases = lease_repository.list_expired(limit=limit)
            results = tuple(self._recover_lease(session=session, lease=lease) for lease in leases)
            return StuckRunRecoveryBatchResult(results=results)

    def _recover_lease(
        self,
        *,
        session: Session,
        lease: WorkerLease,
    ) -> StuckRunRecoveryResult:
        run_repository = RunRepository(session)
        lease_repository = WorkerLeaseRepository(session)
        run = run_repository.get(lease.run_id)
        if run is None:
            lease_repository.release(lease_token=lease.lease_token)
            return StuckRunRecoveryResult(
                run_id=lease.run_id,
                lease_id=lease.id,
                worker_id=lease.worker_id,
                recovered=False,
                status=None,
                reason="run_not_found",
            )

        if run.status not in self._recoverable_statuses:
            lease_repository.release(lease_token=lease.lease_token)
            return StuckRunRecoveryResult(
                run_id=run.id,
                lease_id=lease.id,
                worker_id=lease.worker_id,
                recovered=False,
                status=run.status,
                reason=f"status_{run.status.value}_not_recoverable",
            )

        failed = run_repository.fail(
            run_id=run.id,
            error_type="worker_lease_expired",
            error_message=(
                f"Worker lease {lease.id} from worker {lease.worker_id!r} expired before release."
            ),
            event_payload={
                "from_status": run.status.value,
                "to_status": RunStatus.FAILED.value,
                "reason": "worker_lease_expired",
                "lease_id": str(lease.id),
                "worker_id": lease.worker_id,
            },
        )
        lease_repository.release(lease_token=lease.lease_token)
        return StuckRunRecoveryResult(
            run_id=run.id,
            lease_id=lease.id,
            worker_id=lease.worker_id,
            recovered=failed is not None,
            status=failed.status if failed is not None else run.status,
            reason="worker_lease_expired",
        )
