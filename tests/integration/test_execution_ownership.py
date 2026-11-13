"""Ownership contracts on independent database sessions and PostgreSQL processes."""

import asyncio
import multiprocessing
import os
from collections.abc import Callable, Iterator
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from typing import Any
from uuid import UUID, uuid4

import pytest
from kernel_core import RiskLevel, RunEventType, RunStatus, ToolCallStatus, utc_now
from kernel_providers import LLMRequest, LLMResponse, MockLLMProvider
from kernel_runtime import RunExecutionService
from kernel_storage import (
    AgentRepository,
    ApprovalDecisionError,
    ApprovalRepository,
    ExecutionOwnershipError,
    RunRepository,
    ToolCallRepository,
    WorkerLeaseRepository,
    create_session_factory,
)
from kernel_storage.base import Base
from kernel_storage.models import WorkerLeaseRecord
from kernel_tools import ToolMetadata, ToolRegistry
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(params=["sqlite", "postgres"])
def ownership_db(request: pytest.FixtureRequest, tmp_path: Any) -> Iterator[sessionmaker[Session]]:
    if request.param == "sqlite":
        engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'ownership.db'}")
        Base.metadata.create_all(engine)
        try:
            yield create_session_factory(engine)
        finally:
            engine.dispose()
        return
    url = os.getenv("AGENT_KERNEL_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set AGENT_KERNEL_TEST_POSTGRES_URL for PostgreSQL concurrency contracts.")
    schema = f"test_ownership_{uuid4().hex}"
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        make_url(url).update_query_dict({"options": f"-csearch_path={schema},public"})
    )
    try:
        Base.metadata.create_all(engine)
        yield create_session_factory(engine)
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def _queued(factory: sessionmaker[Session], payload: dict[str, Any] | None = None) -> UUID:
    with factory() as session:
        agent = AgentRepository(session).create(name="ownership")
        repo = RunRepository(session)
        run = repo.create(agent_id=agent.id, input_payload=payload or {"task": "hello"})
        repo.apply_transition(
            run_id=run.id, status=RunStatus.QUEUED, event_type=RunEventType.RUN_QUEUED, payload={}
        )
        return run.id


def _process_claim(args: tuple[str, str]) -> bool:
    url, run_id = args
    engine = create_engine(url)
    try:
        with Session(engine) as session:
            return (
                WorkerLeaseRepository(session).acquire(
                    run_id=UUID(run_id),
                    worker_id=str(os.getpid()),
                )
                is not None
            )
    finally:
        engine.dispose()


def test_only_one_process_can_claim(ownership_db: sessionmaker[Session]) -> None:
    run_id = _queued(ownership_db)
    with ownership_db() as session:
        url = session.get_bind().engine.url.render_as_string(hide_password=False)
    with ProcessPoolExecutor(
        max_workers=3, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        results = list(pool.map(_process_claim, [(url, str(run_id))] * 3))
    assert results.count(True) == 1


def test_stale_owner_cannot_write_results_or_events(ownership_db: sessionmaker[Session]) -> None:
    run_id = _queued(ownership_db)
    with ownership_db() as session:
        lease = WorkerLeaseRepository(session).acquire(run_id=run_id, worker_id="old")
        assert lease is not None
        old = RunRepository(session, lease_token=lease.lease_token)
        call = ToolCallRepository(session, lease_token=lease.lease_token).create_requested(
            run_id=run_id,
            tool_name="echo",
            arguments={},
            risk_level=RiskLevel.READ_ONLY,
        )
        assert call is not None
        row = session.scalar(select(WorkerLeaseRecord).where(WorkerLeaseRecord.id == str(lease.id)))
        assert row is not None
        row.expires_at = utc_now() - timedelta(seconds=1)
        session.commit()
        replacement = WorkerLeaseRepository(session).acquire(run_id=run_id, worker_id="new")
        assert replacement is not None
        before = len(old.list_events(run_id))
        writes: list[Callable[[], object]] = [
            lambda: old.update_status(run_id=run_id, status=RunStatus.SUCCEEDED),
            lambda: old.append_event(run_id=run_id, event_type=RunEventType.RUN_COMPLETED),
            lambda: old.complete(
                run_id=run_id,
                output_payload={},
                input_tokens_total=0,
                output_tokens_total=0,
                estimated_cost_total=0,
                event_payload={},
            ),
            lambda: ToolCallRepository(session, lease_token=lease.lease_token).complete(
                tool_call_id=call.id,
                result={},
                latency_ms=1,
            ),
        ]
        for write in writes:
            with pytest.raises(ExecutionOwnershipError):
                write()
            session.rollback()
        assert len(old.list_events(run_id)) == before
        assert ToolCallRepository(session).get(call.id).status is ToolCallStatus.REQUESTED  # type: ignore[union-attr]


def test_recovery_rechecks_expiry_after_heartbeat(ownership_db: sessionmaker[Session]) -> None:
    run_id = _queued(ownership_db)
    with ownership_db() as session:
        leases = WorkerLeaseRepository(session)
        lease = leases.acquire(run_id=run_id, worker_id="healthy")
        assert lease is not None
        RunRepository(session, lease_token=lease.lease_token).update_status(
            run_id=run_id,
            status=RunStatus.RUNNING,
        )
        assert leases.heartbeat(lease_token=lease.lease_token) is not None
        # A stale scanner snapshot cannot authorize recovery of a renewed lease.
        assert leases.recover_expired(lease_token=lease.lease_token) == (
            False,
            RunStatus.RUNNING,
            "lease_no_longer_expired",
        )


class SlowProvider(MockLLMProvider):
    async def complete(self, request: LLMRequest) -> LLMResponse:
        await asyncio.sleep(1.3)
        return await super().complete(request)


@pytest.mark.asyncio
async def test_runtime_renews_and_releases_lease(ownership_db: sessionmaker[Session]) -> None:
    run_id = _queued(ownership_db)
    with ownership_db() as session:
        result = await RunExecutionService(provider=SlowProvider(), lease_ttl_seconds=1).execute(
            run_id=run_id,
            repository=RunRepository(session),
        )
        assert result.status is RunStatus.SUCCEEDED
        lease = session.scalar(
            select(WorkerLeaseRecord).where(WorkerLeaseRecord.run_id == str(run_id))
        )
        assert lease is not None and lease.released_at is not None
        assert lease.heartbeat_at > lease.acquired_at


class CountedWrite:
    def __init__(self) -> None:
        self.calls = 0

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="counted_write",
            description="Test write",
            risk_level=RiskLevel.EXTERNAL_WRITE,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        await asyncio.sleep(0.1)
        return {"ok": True}


@pytest.mark.asyncio
async def test_approval_and_concurrent_resume_are_idempotent(
    ownership_db: sessionmaker[Session],
) -> None:
    tool = CountedWrite()
    registry = ToolRegistry()
    registry.register(tool)
    service = RunExecutionService(tool_registry=registry)
    run_id = _queued(ownership_db, {"tool": {"name": "counted_write", "arguments": {}}})
    with ownership_db() as session:
        waiting = await service.execute(run_id=run_id, repository=RunRepository(session))
        assert waiting.status is RunStatus.WAITING_APPROVAL
        approval = ApprovalRepository(session).list_for_run(run_id)[0]
    barrier = Barrier(2)

    def decide() -> None:
        with ownership_db() as session:
            barrier.wait(timeout=10)
            ApprovalRepository(session).approve(approval_id=approval.id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(decide) for _ in range(2)]
        for future in futures:
            future.result(timeout=15)
    with ownership_db() as session, pytest.raises(ApprovalDecisionError):
        ApprovalRepository(session).reject(approval_id=approval.id, decision_note="conflict")

    async def resume() -> Any:
        with ownership_db() as session:
            return await service.resume(
                run_id=run_id,
                repository=RunRepository(session),
                approval_repository=ApprovalRepository(session),
                tool_call_repository=ToolCallRepository(session),
            )

    results = await asyncio.gather(resume(), resume(), return_exceptions=True)
    assert sum(not isinstance(result, BaseException) for result in results) == 1
    assert tool.calls == 1
    with ownership_db() as session:
        events = RunRepository(session).list_events(run_id)
        assert [e.type for e in events].count(RunEventType.APPROVAL_APPROVED) == 1
        assert [e.type for e in events].count(RunEventType.RUN_COMPLETED) == 1
        assert [e.sequence for e in events] == list(range(1, len(events) + 1))
