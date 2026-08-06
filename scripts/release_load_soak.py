"""Deterministic release load/soak scenarios for Agent Kernel."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from time import perf_counter
from uuid import UUID

from kernel_core import RunEventType, RunStatus
from kernel_providers import MockLLMProvider
from kernel_runtime import ModelRouter, QueuedRunWorker, RunExecutionService
from kernel_storage import AgentRepository, Base, RunRepository, create_session_factory
from kernel_storage import models as storage_models
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

_ = storage_models


@dataclass(frozen=True)
class LoadSoakProfile:
    name: str
    runs: int
    batch_size: int
    max_elapsed_ms: int


@dataclass(frozen=True)
class LoadSoakReport:
    profile: str
    scenario: str
    runs_requested: int
    processed_count: int
    succeeded_count: int
    failed_count: int
    remaining_queued_count: int
    elapsed_ms: int
    batch_p95_ms: int
    passed: bool


PROFILES = {
    "quick": LoadSoakProfile(name="quick", runs=25, batch_size=10, max_elapsed_ms=5_000),
    "local": LoadSoakProfile(name="local", runs=100, batch_size=25, max_elapsed_ms=20_000),
}


async def run_worker_burst(profile: LoadSoakProfile) -> LoadSoakReport:
    """Run a deterministic queued-run worker burst against in-memory SQLite."""

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    run_ids = _create_queued_runs(session_factory=session_factory, runs=profile.runs)

    worker = QueuedRunWorker(
        session_factory=session_factory,
        execution_service=RunExecutionService(
            router=ModelRouter({"mock": MockLLMProvider(response_prefix="Load")})
        ),
    )

    processed_count = 0
    succeeded_count = 0
    failed_count = 0
    batch_elapsed_ms: list[int] = []
    started = perf_counter()

    while True:
        batch_started = perf_counter()
        batch = await worker.run_once(limit=profile.batch_size)
        batch_elapsed_ms.append(_elapsed_ms(batch_started))
        if batch.processed_count == 0:
            break
        processed_count += batch.processed_count
        succeeded_count += batch.succeeded_count
        failed_count += batch.failed_count

    elapsed_ms = _elapsed_ms(started)
    remaining_queued_count = _remaining_queued_count(session_factory)
    persisted_success_count = _persisted_success_count(
        session_factory=session_factory,
        run_ids=run_ids,
    )
    passed = (
        processed_count == profile.runs
        and succeeded_count == profile.runs
        and persisted_success_count == profile.runs
        and failed_count == 0
        and remaining_queued_count == 0
        and elapsed_ms <= profile.max_elapsed_ms
    )

    Base.metadata.drop_all(engine)
    engine.dispose()

    return LoadSoakReport(
        profile=profile.name,
        scenario="queued-worker-burst",
        runs_requested=profile.runs,
        processed_count=processed_count,
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        remaining_queued_count=remaining_queued_count,
        elapsed_ms=elapsed_ms,
        batch_p95_ms=_p95(batch_elapsed_ms),
        passed=passed,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default="quick",
        help="Load/soak profile to run.",
    )
    args = parser.parse_args()

    report = asyncio.run(run_worker_burst(PROFILES[args.profile]))
    print(json.dumps(asdict(report), indent=2, sort_keys=True))
    return 0 if report.passed else 1


def _create_queued_runs(
    *,
    session_factory: sessionmaker[Session],
    runs: int,
) -> tuple[UUID, ...]:
    with session_factory() as session:
        agent = AgentRepository(session).create(name="release-load-soak-agent")
        run_repository = RunRepository(session)
        run_ids: list[UUID] = []
        for index in range(runs):
            run = run_repository.create(
                agent_id=agent.id,
                input_payload={
                    "task": f"process load scenario {index}",
                    "model": "mock:load-soak",
                },
            )
            run_repository.apply_transition(
                run_id=run.id,
                status=RunStatus.QUEUED,
                event_type=RunEventType.RUN_QUEUED,
                payload={"from_status": "created", "to_status": "queued"},
            )
            run_ids.append(run.id)
        return tuple(run_ids)


def _remaining_queued_count(session_factory: sessionmaker[Session]) -> int:
    with session_factory() as session:
        return len(RunRepository(session).list_queued(limit=10_000))


def _persisted_success_count(
    *,
    session_factory: sessionmaker[Session],
    run_ids: tuple[UUID, ...],
) -> int:
    with session_factory() as session:
        repository = RunRepository(session)
        count = 0
        for run_id in run_ids:
            run = repository.get(run_id)
            if run is not None and run.status is RunStatus.SUCCEEDED:
                count += 1
        return count


def _elapsed_ms(started: float) -> int:
    return int((perf_counter() - started) * 1_000)


def _p95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * 0.95))
    return ordered[index]


if __name__ == "__main__":
    raise SystemExit(main())
