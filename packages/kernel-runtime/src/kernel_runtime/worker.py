"""Worker orchestration for queued run execution."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID

from kernel_core import RunStatus
from kernel_observability import MetricsRecorder, NoOpMetricsRecorder
from kernel_storage import RunRepository
from sqlalchemy.orm import Session, sessionmaker

from kernel_runtime.execution import RunAlreadyClaimedError, RunExecutionService
from kernel_runtime.queue import QueueUnavailableError, RunQueue


@dataclass(frozen=True)
class WorkerRunResult:
    """Execution result for one queued run picked by a worker."""

    run_id: UUID
    status: RunStatus | None
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class WorkerBatchResult:
    """Summary for one worker polling pass."""

    runs: tuple[WorkerRunResult, ...]

    @property
    def processed_count(self) -> int:
        return len(self.runs)

    @property
    def succeeded_count(self) -> int:
        return sum(1 for run in self.runs if run.status is RunStatus.SUCCEEDED)

    @property
    def failed_count(self) -> int:
        return sum(
            1 for run in self.runs if run.status is RunStatus.FAILED or run.error_type is not None
        )


class QueuedRunWorker:
    """Poll persisted queued runs and execute them one at a time."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        execution_service: RunExecutionService,
        run_queue: RunQueue | None = None,
        metrics_recorder: MetricsRecorder | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._execution_service = execution_service
        self._run_queue = run_queue
        self._metrics = metrics_recorder or NoOpMetricsRecorder()

    async def run_once(self, *, limit: int = 100) -> WorkerBatchResult:
        """Execute up to ``limit`` queued runs in created-at order."""

        if limit < 1:
            raise ValueError("Worker limit must be at least 1.")

        hinted: tuple[UUID, ...] = ()
        if self._run_queue is not None:
            try:
                hinted = await asyncio.to_thread(self._run_queue.dequeue, limit=min(limit, 1000))
            except QueueUnavailableError:
                self._metrics.increment("run_queue_errors_total", labels={"operation": "dequeue"})
        # Poll on every pass even when hints exist. Lost/duplicate hints are harmless;
        # persisted queue state and atomic leases remain the source of truth.
        run_ids = tuple(dict.fromkeys((*self._list_queued_run_ids(limit=limit), *hinted)))[:limit]
        results: list[WorkerRunResult] = []
        for run_id in run_ids:
            result = await self._execute_one(run_id)
            if result is not None:
                results.append(result)
        return WorkerBatchResult(runs=tuple(results))

    def _list_queued_run_ids(self, *, limit: int) -> tuple[UUID, ...]:
        with self._session_factory() as session:
            repository = RunRepository(session)
            return tuple(run.id for run in repository.list_queued(limit=limit))

    async def _execute_one(self, run_id: UUID) -> WorkerRunResult | None:
        with self._session_factory() as session:
            repository = RunRepository(session)
            current = repository.get(run_id)
            if current is None or current.status is not RunStatus.QUEUED:
                return None
            try:
                run = await self._execution_service.execute(run_id=run_id, repository=repository)
            except RunAlreadyClaimedError:
                session.rollback()
                return None
            except Exception as error:
                session.rollback()
                return WorkerRunResult(
                    run_id=run_id,
                    status=None,
                    error_type=type(error).__name__,
                    error_message=str(error),
                )
            return WorkerRunResult(
                run_id=run.id,
                status=run.status,
                error_type=run.error_type,
                error_message=run.error_message,
            )
