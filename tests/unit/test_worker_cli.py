from datetime import timedelta

import pytest
from agent_kernel_worker import main as worker_main
from kernel_core import RunEventType, RunStatus, utc_now
from kernel_storage import AgentRepository, RunRepository, WorkerLeaseRepository
from kernel_storage.models import WorkerLeaseRecord
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker
from typer.testing import CliRunner


def test_worker_cli_prints_ready_without_mode() -> None:
    result = CliRunner().invoke(worker_main.app, [])

    assert result.exit_code == 0
    assert "agent-kernel-worker ready" in result.output


def test_worker_cli_rejects_multiple_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    engine_created = False

    def fake_create_engine_for_url() -> None:
        nonlocal engine_created
        engine_created = True

    monkeypatch.setattr(worker_main, "create_engine_for_url", fake_create_engine_for_url)

    result = CliRunner().invoke(worker_main.app, ["--once", "--recover-stuck"])

    assert result.exit_code != 0
    assert engine_created is False


def test_worker_cli_once_executes_persisted_queued_run(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_engine: Engine,
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    monkeypatch.setattr(worker_main, "create_engine_for_url", lambda: sqlite_engine)

    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="worker-cli-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "process through cli", "model": "mock:mock-cli"},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

    result = CliRunner().invoke(worker_main.app, ["--once", "--limit", "10"])

    with sqlite_session_factory() as session:
        completed = RunRepository(session).get(run.id)

    assert result.exit_code == 0
    assert "processed=1 succeeded=1 failed=0" in result.output
    assert completed is not None
    assert completed.status is RunStatus.SUCCEEDED
    assert completed.output is not None
    assert completed.output["text"] == "Mock response: process through cli"


def test_worker_cli_recover_stuck_fails_expired_running_run(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_engine: Engine,
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    monkeypatch.setattr(worker_main, "create_engine_for_url", lambda: sqlite_engine)

    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="worker-cli-recovery-agent")
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
            worker_id="worker-cli",
            ttl_seconds=60,
        )
        assert lease is not None
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.RUNNING,
            event_type=RunEventType.RUN_STARTED,
            payload={"from_status": "queued", "to_status": "running"},
        )
        record = session.scalar(
            select(WorkerLeaseRecord).where(
                WorkerLeaseRecord.lease_token == lease.lease_token
            )
        )
        assert record is not None
        record.expires_at = utc_now() - timedelta(seconds=1)
        session.commit()

    result = CliRunner().invoke(worker_main.app, ["--recover-stuck", "--limit", "10"])

    with sqlite_session_factory() as session:
        failed = RunRepository(session).get(run.id)
        active_lease = WorkerLeaseRepository(session).get_active(run_id=run.id)

    assert result.exit_code == 0
    assert "inspected=1 recovered=1 skipped=0" in result.output
    assert failed is not None
    assert failed.status is RunStatus.FAILED
    assert failed.error_type == "worker_lease_expired"
    assert active_lease is None
