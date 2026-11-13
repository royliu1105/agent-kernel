"""Stuck-run recovery for durable worker execution."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from kernel_core import RunStatus, WorkerLease
from kernel_storage import WorkerLeaseRepository
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
        recovered, status, reason = WorkerLeaseRepository(session).recover_expired(
            lease_token=lease.lease_token,
        )
        return StuckRunRecoveryResult(
            run_id=lease.run_id,
            lease_id=lease.id,
            worker_id=lease.worker_id,
            recovered=recovered,
            status=status,
            reason=reason,
        )
