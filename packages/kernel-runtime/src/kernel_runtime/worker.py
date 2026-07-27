"""Worker orchestration for queued run execution."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from kernel_core import RunStatus
from kernel_storage import RunRepository
from sqlalchemy.orm import Session, sessionmaker

from kernel_runtime.execution import RunExecutionService


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
    ) -> None:
        self._session_factory = session_factory
        self._execution_service = execution_service

    async def run_once(self, *, limit: int = 100) -> WorkerBatchResult:
        """Execute up to ``limit`` queued runs in created-at order."""

        if limit < 1:
            raise ValueError("Worker limit must be at least 1.")

        run_ids = self._list_queued_run_ids(limit=limit)
        results: list[WorkerRunResult] = []
        for run_id in run_ids:
            results.append(await self._execute_one(run_id))
        return WorkerBatchResult(runs=tuple(results))

    def _list_queued_run_ids(self, *, limit: int) -> tuple[UUID, ...]:
        with self._session_factory() as session:
            repository = RunRepository(session)
            return tuple(run.id for run in repository.list_queued(limit=limit))

    async def _execute_one(self, run_id: UUID) -> WorkerRunResult:
        with self._session_factory() as session:
            repository = RunRepository(session)
            try:
                run = await self._execution_service.execute(run_id=run_id, repository=repository)
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
