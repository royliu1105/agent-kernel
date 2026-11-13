from pathlib import Path
from uuid import UUID, uuid4

import pytest
from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from kernel_core import RiskLevel
from kernel_rag import LocalObjectStore
from kernel_runtime import RunExecutionService
from kernel_runtime.queue import InMemoryRunQueue, QueueUnavailableError
from kernel_runtime.redis_support import (
    RateLimitDecision,
    RateLimitUnavailableError,
    RedisWorkspaceRateLimiter,
)
from kernel_storage import AgentRepository, RunRepository, ToolCallRepository
from sqlalchemy.orm import Session, sessionmaker
from test_knowledge_workspace_isolation import _client


def test_usage_audit_and_tool_records_are_workspace_scoped(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    store = LocalObjectStore(root_path=tmp_path)
    a, wa = _client(sqlite_session_factory, store)
    b, wb = _client(sqlite_session_factory, store)
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="a", workspace_id=wa)
        repo = RunRepository(session)
        run = repo.create(agent_id=agent.id, workspace_id=wa, input_payload={})
        repo.record_usage(run.id, input_tokens=15, output_tokens=2, estimated_cost=0.4)
        call = ToolCallRepository(session, workspace_id=wa).create_requested(
            run_id=run.id,
            tool_name="echo",
            arguments={"secret": "only-a"},
            risk_level=RiskLevel.READ_ONLY,
        )
        assert call is not None
        denied = ToolCallRepository(session, workspace_id=wb)
        assert denied.get(call.id) is None
        assert denied.list_for_run(run.id) == []
        assert denied.complete(tool_call_id=call.id, result={}) is None
        assert repo.list_events(run.id, workspace_id=wb) == []
    assert a.get("/v1/usage").json() == {
        "run_count": 1,
        "input_tokens": 15,
        "output_tokens": 2,
        "estimated_cost": 0.4,
    }
    assert b.get("/v1/usage").json()["run_count"] == 0
    assert b.get(f"/v1/runs/{run.id}/events").status_code == 404
    assert a.get("/metrics").status_code == 401


class StubLimiter(RedisWorkspaceRateLimiter):
    def __init__(self) -> None:
        self.seen: list[UUID] = []
        self.outage = False

    def check(self, workspace_id: UUID, *, limit: int, window_seconds: int) -> RateLimitDecision:
        if self.outage:
            raise RateLimitUnavailableError("unavailable")
        self.seen.append(workspace_id)
        return RateLimitDecision(len(self.seen) <= 1, 0, 60)


def test_admission_uses_authenticated_workspace_and_fails_closed(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_KERNEL_RATE_LIMIT_REQUESTS", "1")
    # Issue credentials before enabling the test middleware.
    monkeypatch.setenv("AGENT_KERNEL_RATE_LIMIT_REQUESTS", "0")
    issued, workspace = _client(sqlite_session_factory, LocalObjectStore(root_path=tmp_path))
    monkeypatch.setenv("AGENT_KERNEL_RATE_LIMIT_REQUESTS", "1")
    limiter = StubLimiter()
    with TestClient(
        create_app(
            session_factory=sqlite_session_factory,
            api_key_auth_enabled=True,
            rate_limiter=limiter,
        ),
        headers=dict(issued.headers),
    ) as client:
        assert client.post("/v1/agents", json={"name": "a"}).status_code == 201
        denied = client.get(f"/v1/usage?workspace_id={uuid4()}")
        assert denied.status_code == 429 and denied.headers["retry-after"] == "60"
        assert limiter.seen == [workspace, workspace]
        limiter.outage = True
        assert client.get("/v1/usage").status_code == 503
        assert client.get("/healthz").status_code == 200


class BrokenQueue(InMemoryRunQueue):
    def enqueue(self, run_id: UUID) -> None:
        raise QueueUnavailableError("unavailable")

    def dequeue(self, *, limit: int = 100) -> tuple[UUID, ...]:
        raise QueueUnavailableError("unavailable")


@pytest.mark.asyncio
async def test_committed_run_survives_redis_outage_and_lost_hints(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    from kernel_providers import MockLLMProvider
    from kernel_runtime import QueuedRunWorker

    queue = BrokenQueue()
    with TestClient(create_app(session_factory=sqlite_session_factory, run_queue=queue)) as client:
        agent = client.post("/v1/agents", json={"name": "a"}).json()
        run = client.post(
            f"/v1/agents/{agent['id']}/runs", json={"input": {"task": "hello"}}
        ).json()
        assert client.post(f"/v1/runs/{run['id']}/queue").status_code == 200
        worker = QueuedRunWorker(
            session_factory=sqlite_session_factory,
            run_queue=queue,
            execution_service=RunExecutionService(provider=MockLLMProvider()),
        )
        result = await worker.run_once()
        assert result.succeeded_count == 1
        assert (await worker.run_once()).processed_count == 0
