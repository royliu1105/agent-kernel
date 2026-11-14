"""Private checkpoint persistence on isolated PostgreSQL schemas."""

from collections.abc import Iterator
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from agent_kernel_api.schemas import RunResponse
from alembic import command
from alembic.config import Config
from kernel_core import Run, RunEventType, RunStatus, utc_now
from kernel_storage import (
    AgentRepository,
    ExecutionOwnershipError,
    RunRepository,
    WorkerLeaseRepository,
    create_session_factory,
)
from kernel_storage.models import RunRecord, WorkerLeaseRecord
from pydantic import ValidationError
from sqlalchemy import JSON, Engine, MetaData, Table, inspect, select, text, update
from sqlalchemy.orm import Session, sessionmaker

CHECKPOINT_REVISION = "0019_execution_checkpoint"
PREVIOUS_REVISION = "0018_usage_attribution"


@pytest.fixture
def checkpoint_database(
    migration_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Engine, Config]]:
    engine = migration_engine
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option(
        "script_location", str(root / "packages/kernel-storage/src/kernel_storage/migrations")
    )
    monkeypatch.setenv("DATABASE_URL", engine.url.render_as_string(hide_password=False))
    with engine.connect() as connection:
        config.attributes["version_table_schema"] = connection.scalar(
            text("SELECT current_schema()")
        )
    yield engine, config


@pytest.fixture
def checkpoint_sessions(
    checkpoint_database: tuple[Engine, Config],
) -> sessionmaker[Session]:
    engine, config = checkpoint_database
    command.upgrade(config, CHECKPOINT_REVISION)
    with engine.connect() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
    assert {"runs", "worker_leases", "alembic_version"} <= set(
        inspect(engine).get_table_names(schema=schema)
    )
    return create_session_factory(engine)


def _seed_migration_history(engine: Engine) -> str:
    metadata = MetaData()
    tables = {
        name: Table(name, metadata, autoload_with=engine)
        for name in ("agents", "runs", "run_events", "worker_leases", "model_usage")
    }
    agent_id, run_id, completed_id = (str(uuid4()) for _ in range(3))
    now = utc_now()
    with engine.begin() as connection:
        connection.execute(
            tables["agents"]
            .insert()
            .values(
                id=agent_id,
                name="checkpoint migration history",
                description="preserve this row",
                status="active",
                memory_policy={},
                tool_policy={},
                metadata={"legacy": True},
                created_at=now,
            )
        )
        for identifier, status in ((run_id, "queued"), (completed_id, "succeeded")):
            connection.execute(
                tables["runs"]
                .insert()
                .values(
                    id=identifier,
                    agent_id=agent_id,
                    status=status,
                    input={"task": "preserve nested input", "items": [1, {"ok": True}]},
                    output={"answer": "existing answer"} if status == "succeeded" else None,
                    trace_id=f"trace-{identifier}",
                    input_tokens_total=12,
                    output_tokens_total=3,
                    estimated_cost_total=0.5,
                    created_at=now,
                )
            )
        connection.execute(
            tables["run_events"]
            .insert()
            .values(
                id=str(uuid4()),
                run_id=run_id,
                sequence=1,
                type="run_created",
                payload={"status": "created"},
                created_at=now,
            )
        )
        connection.execute(
            tables["worker_leases"]
            .insert()
            .values(
                id=str(uuid4()),
                run_id=run_id,
                worker_id="migration-owner",
                lease_token=str(uuid4()),
                acquired_at=now,
                heartbeat_at=now,
                expires_at=now + timedelta(minutes=5),
            )
        )
        connection.execute(
            tables["model_usage"]
            .insert()
            .values(
                id=str(uuid4()),
                run_id=completed_id,
                provider="fixture",
                model="history",
                input_tokens=12,
                output_tokens=3,
                estimated_cost=0.5,
                created_at=now,
            )
        )
    return run_id


def _history_snapshot(engine: Engine) -> dict[str, list[dict[str, Any]]]:
    snapshot = {}
    with engine.connect() as connection:
        for name in ("agents", "runs", "run_events", "worker_leases", "model_usage"):
            table = Table(name, MetaData(), autoload_with=connection)
            columns = [column for column in table.c if column.name != "execution_checkpoint"]
            snapshot[name] = [
                dict(row)
                for row in connection.execute(select(*columns).order_by(table.c.id)).mappings()
            ]
    return snapshot


@pytest.mark.parametrize("legacy", [False, True], ids=["fresh", "legacy-upgrade"])
def test_checkpoint_migration_preserves_rows_through_upgrade_and_downgrade(
    checkpoint_database: tuple[Engine, Config], legacy: bool
) -> None:
    engine, config = checkpoint_database
    command.upgrade(config, PREVIOUS_REVISION if legacy else CHECKPOINT_REVISION)
    run_id = _seed_migration_history(engine)
    before = _history_snapshot(engine)
    if legacy:
        assert "execution_checkpoint" not in {
            column["name"] for column in inspect(engine).get_columns("runs")
        }
        command.upgrade(config, CHECKPOINT_REVISION)

    column = next(
        column
        for column in inspect(engine).get_columns("runs")
        if column["name"] == "execution_checkpoint"
    )
    assert column["nullable"] is True
    assert isinstance(column["type"], JSON)
    runs = Table("runs", MetaData(), autoload_with=engine)
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            CHECKPOINT_REVISION
        )
        assert list(connection.scalars(select(runs.c.execution_checkpoint))) == [None, None]
        connection.execute(
            runs.update()
            .where(runs.c.id == run_id)
            .values(execution_checkpoint={"version": 1, "private": ["continuation"]})
        )
    assert _history_snapshot(engine) == before

    command.downgrade(config, PREVIOUS_REVISION)
    assert "execution_checkpoint" not in {
        column["name"] for column in inspect(engine).get_columns("runs")
    }
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            PREVIOUS_REVISION
        )
    assert _history_snapshot(engine) == before

    command.upgrade(config, CHECKPOINT_REVISION)
    with engine.connect() as connection:
        assert list(connection.scalars(select(runs.c.execution_checkpoint))) == [None, None]
    assert _history_snapshot(engine) == before


def _queued_run(factory: sessionmaker[Session]) -> UUID:
    with factory() as session:
        agent = AgentRepository(session).create(name="checkpoint-owner")
        repository = RunRepository(session)
        run = repository.create(agent_id=agent.id, input_payload={"task": "public task"})
        repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={},
        )
        return run.id


def test_checkpoint_round_trip_has_deep_copy_semantics(
    checkpoint_sessions: sessionmaker[Session],
) -> None:
    run_id = _queued_run(checkpoint_sessions)
    payload: dict[str, Any] = {
        "version": 1,
        "history": [{"content": {"parts": ["private continuation"]}}],
    }
    expected = deepcopy(payload)
    with checkpoint_sessions() as session:
        lease = WorkerLeaseRepository(session).acquire(run_id=run_id, worker_id="owner")
        assert lease is not None
        repository = RunRepository(session, lease_token=lease.lease_token)
        assert repository.load_execution_checkpoint(run_id) is None
        record = session.get(RunRecord, str(run_id))
        assert record is not None
        repository.save_execution_checkpoint(run_id, payload)
        assert record.execution_checkpoint == expected
        assert record.execution_checkpoint is not payload
        payload["history"][0]["content"]["parts"].append("caller mutation")
        assert record.execution_checkpoint == expected

        loaded = repository.load_execution_checkpoint(run_id)
        assert loaded is not None
        assert loaded == expected
        assert loaded is not record.execution_checkpoint
        loaded["history"][0]["content"]["parts"].append("reader mutation")
        assert record.execution_checkpoint == expected
        session.commit()

    with checkpoint_sessions() as session:
        repository = RunRepository(session, lease_token=lease.lease_token)
        assert repository.load_execution_checkpoint(run_id) == expected
        repository.save_execution_checkpoint(run_id, {"version": 1, "next_turn": 2})
    with checkpoint_sessions() as session:
        repository = RunRepository(session, lease_token=lease.lease_token)
        assert repository.load_execution_checkpoint(run_id) == {"version": 1, "next_turn": 2}


@pytest.mark.parametrize("operation", ["load", "save"])
@pytest.mark.parametrize(
    "ownership",
    [
        "no-active-lease",
        "missing-token",
        "unknown-token",
        "other-run-token",
        "expired",
        "released",
        "replaced",
        "invalidated",
        "locally-revoked",
    ],
)
def test_checkpoint_access_rejects_unowned_tokens_without_mutating_state(
    checkpoint_sessions: sessionmaker[Session], operation: str, ownership: str
) -> None:
    run_id = _queued_run(checkpoint_sessions)
    payload = {"version": 1, "history": [{"content": "private checkpoint"}]}
    with checkpoint_sessions() as owner_session:
        lease = WorkerLeaseRepository(owner_session).acquire(run_id=run_id, worker_id="old")
        assert lease is not None
        owner = RunRepository(owner_session, lease_token=lease.lease_token)
        owner.save_execution_checkpoint(run_id, payload)
        token: str | None = lease.lease_token
        with checkpoint_sessions() as control_session:
            leases = WorkerLeaseRepository(control_session)
            if ownership in {"no-active-lease", "released"}:
                assert leases.release(lease_token=lease.lease_token) is not None
                if ownership == "no-active-lease":
                    token = None
            elif ownership == "missing-token":
                token = None
            elif ownership == "unknown-token":
                token = str(uuid4())
            elif ownership == "other-run-token":
                other_run_id = _queued_run(checkpoint_sessions)
                other_lease = leases.acquire(run_id=other_run_id, worker_id="other-run")
                assert other_lease is not None
                token = other_lease.lease_token
            elif ownership in {"expired", "replaced"}:
                control_session.execute(
                    update(WorkerLeaseRecord)
                    .where(WorkerLeaseRecord.lease_token == token)
                    .values(expires_at=utc_now() - timedelta(seconds=1))
                )
                control_session.commit()
                if ownership == "replaced":
                    replacement = leases.acquire(run_id=run_id, worker_id="replacement")
                    assert replacement is not None
                    assert replacement.lease_token != token
                    new_owner = RunRepository(control_session, lease_token=replacement.lease_token)
                    assert new_owner.load_execution_checkpoint(run_id) == payload
                    new_owner.save_execution_checkpoint(run_id, payload)
            elif ownership == "invalidated":
                assert leases.invalidate(lease_token=lease.lease_token) is not None
            elif ownership == "locally-revoked":
                owner.revoke_local_ownership()

        denied = RunRepository(owner_session, lease_token=token)
        with pytest.raises(ExecutionOwnershipError):
            if operation == "load":
                denied.load_execution_checkpoint(run_id)
            else:
                denied.save_execution_checkpoint(run_id, {"tampered": True})
        owner_session.rollback()

    with checkpoint_sessions() as session:
        assert (
            session.scalar(
                select(RunRecord.execution_checkpoint).where(RunRecord.id == str(run_id))
            )
            == payload
        )


def test_checkpoint_is_absent_from_public_run_models(
    checkpoint_sessions: sessionmaker[Session],
) -> None:
    run_id = _queued_run(checkpoint_sessions)
    sentinel = "private-provider-history-must-not-leak"
    with checkpoint_sessions() as session:
        lease = WorkerLeaseRepository(session).acquire(run_id=run_id, worker_id="owner")
        assert lease is not None
        RunRepository(session, lease_token=lease.lease_token).save_execution_checkpoint(
            run_id, {"version": 1, "history": [sentinel]}
        )
    with checkpoint_sessions() as session:
        run = RunRepository(session).get(run_id)
        assert run is not None
        response = RunResponse.model_validate(run.model_dump())
        for model, instance in ((Run, run), (RunResponse, response)):
            assert "execution_checkpoint" not in model.model_fields
            assert "execution_checkpoint" not in model.model_json_schema()["properties"]
            assert "execution_checkpoint" not in instance.model_dump()
            assert sentinel not in instance.model_dump_json()
            with pytest.raises(ValidationError, match="execution_checkpoint"):
                model.model_validate({**instance.model_dump(), "execution_checkpoint": {}})
