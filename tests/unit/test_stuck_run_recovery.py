from datetime import timedelta
from uuid import UUID

import pytest
from kernel_core import RunEventType, RunStatus, utc_now
from kernel_runtime import StuckRunRecoveryService
from kernel_storage import AgentRepository, RunRepository, WorkerLeaseRepository
from kernel_storage.models import WorkerLeaseRecord
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker


def test_recovery_fails_running_run_with_expired_lease(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    run_id, lease_token = _create_leased_run(
        sqlite_session_factory,
        status=RunStatus.RUNNING,
    )
    _expire_lease(sqlite_session_factory, lease_token=lease_token)

    result = StuckRunRecoveryService(session_factory=sqlite_session_factory).recover_once(limit=10)

    with sqlite_session_factory() as session:
        run = RunRepository(session).get(run_id)
        events = RunRepository(session).list_events(run_id)
        active_lease = WorkerLeaseRepository(session).get_active(run_id=run_id)

    assert result.inspected_count == 1
    assert result.recovered_count == 1
    assert result.skipped_count == 0
    assert result.results[0].reason == "worker_lease_expired"
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert run.error_type == "worker_lease_expired"
    assert "expired before release" in (run.error_message or "")
    assert events[-1].type is RunEventType.RUN_FAILED
    assert events[-1].payload["reason"] == "worker_lease_expired"
    assert active_lease is None


def test_recovery_fails_resuming_run_with_expired_lease(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    run_id, lease_token = _create_leased_run(
        sqlite_session_factory,
        status=RunStatus.RESUMING,
    )
    _expire_lease(sqlite_session_factory, lease_token=lease_token)

    result = StuckRunRecoveryService(session_factory=sqlite_session_factory).recover_once(limit=10)

    with sqlite_session_factory() as session:
        run = RunRepository(session).get(run_id)

    assert result.recovered_count == 1
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert run.error_type == "worker_lease_expired"


def test_recovery_releases_expired_queued_lease_without_failing_run(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    run_id, lease_token = _create_leased_run(
        sqlite_session_factory,
        status=RunStatus.QUEUED,
    )
    _expire_lease(sqlite_session_factory, lease_token=lease_token)

    result = StuckRunRecoveryService(session_factory=sqlite_session_factory).recover_once(limit=10)

    with sqlite_session_factory() as session:
        run = RunRepository(session).get(run_id)
        active_lease = WorkerLeaseRepository(session).get_active(run_id=run_id)

    assert result.inspected_count == 1
    assert result.recovered_count == 0
    assert result.skipped_count == 1
    assert result.results[0].reason == "status_queued_not_recoverable"
    assert run is not None
    assert run.status is RunStatus.QUEUED
    assert run.error_type is None
    assert active_lease is None


def test_recovery_ignores_non_expired_leases(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    run_id, _lease_token = _create_leased_run(
        sqlite_session_factory,
        status=RunStatus.RUNNING,
    )

    result = StuckRunRecoveryService(session_factory=sqlite_session_factory).recover_once(limit=10)

    with sqlite_session_factory() as session:
        run = RunRepository(session).get(run_id)
        active_lease = WorkerLeaseRepository(session).get_active(run_id=run_id)

    assert result.inspected_count == 0
    assert run is not None
    assert run.status is RunStatus.RUNNING
    assert active_lease is not None


def test_recovery_rejects_invalid_limit(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    service = StuckRunRecoveryService(session_factory=sqlite_session_factory)

    with pytest.raises(ValueError, match="Recovery limit must be at least 1"):
        service.recover_once(limit=0)


def _create_leased_run(
    session_factory: sessionmaker[Session],
    *,
    status: RunStatus,
) -> tuple[UUID, str]:
    with session_factory() as session:
        agent = AgentRepository(session).create(name="recovery-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(agent_id=agent.id, input_payload={"task": "recover"})
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        lease = WorkerLeaseRepository(session).acquire(
            run_id=run.id,
            worker_id="worker-a",
            ttl_seconds=60,
        )
        assert lease is not None
        if status is not RunStatus.QUEUED:
            event_type = (
                RunEventType.RUN_STARTED
                if status is RunStatus.RUNNING
                else RunEventType.RUN_RESUMING
            )
            run_repository.apply_transition(
                run_id=run.id,
                status=status,
                event_type=event_type,
                payload={"from_status": "queued", "to_status": status.value},
            )
        return run.id, lease.lease_token


def _expire_lease(session_factory: sessionmaker[Session], *, lease_token: str) -> None:
    with session_factory() as session:
        record = session.scalar(
            select(WorkerLeaseRecord).where(WorkerLeaseRecord.lease_token == lease_token)
        )
        assert record is not None
        record.expires_at = utc_now() - timedelta(seconds=1)
        session.commit()
