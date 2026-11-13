"""Real Redis admission shared by independent API instances, with isolated keys."""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import pytest
from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from kernel_rag import LocalObjectStore
from kernel_runtime.redis_support import RedisSettings, create_redis_client
from kernel_storage.models import AgentRecord
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from test_knowledge_workspace_isolation import _client


@dataclass(frozen=True)
class SharedAdmission:
    first: TestClient
    second: TestClient
    redis: Any
    headers_a: dict[str, str]
    headers_b: dict[str, str]
    workspace_a: UUID
    workspace_b: UUID
    key_a: str
    key_b: str
    window_seconds: int


@pytest.fixture
def shared_admission(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[SharedAdmission]:
    url = os.environ.get("AGENT_KERNEL_TEST_REDIS_URL")
    if not url:
        pytest.skip("Set AGENT_KERNEL_TEST_REDIS_URL to a dedicated loopback Redis DB 15.")
    parsed = urlsplit(url)
    assert parsed.hostname in {"127.0.0.1", "localhost", "::1"} and parsed.path == "/15", (
        "API admission contracts require a dedicated loopback Redis DB 15."
    )
    prefix = f"agent-kernel:drill:shared-admission:{uuid4().hex}"
    window = 60
    monkeypatch.setenv("REDIS_URL", url)
    monkeypatch.setenv("AGENT_KERNEL_RUN_QUEUE_BACKEND", "database")
    monkeypatch.setenv("AGENT_KERNEL_RATE_LIMIT_REQUESTS", "0")
    store = LocalObjectStore(root_path=tmp_path)
    issued_a, workspace_a = _client(sqlite_session_factory, store)
    issued_b, workspace_b = _client(sqlite_session_factory, store)
    headers_a, headers_b = dict(issued_a.headers), dict(issued_b.headers)
    issued_a.close()
    issued_b.close()

    # Configure real composition only after identity setup; no limiter is injected.
    monkeypatch.setenv("AGENT_KERNEL_RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("AGENT_KERNEL_RATE_LIMIT_WINDOW_SECONDS", str(window))
    monkeypatch.setenv("AGENT_KERNEL_RATE_LIMIT_PREFIX", prefix)
    admin = create_redis_client(RedisSettings(url=url))
    key_a, key_b = (f"{prefix}:{workspace}:2:{window}" for workspace in (workspace_a, workspace_b))
    try:
        with (
            TestClient(
                create_app(
                    session_factory=sqlite_session_factory,
                    object_store=store,
                    api_key_auth_enabled=True,
                )
            ) as first,
            TestClient(
                create_app(
                    session_factory=sqlite_session_factory,
                    object_store=store,
                    api_key_auth_enabled=True,
                )
            ) as second,
        ):
            assert first.app is not second.app
            yield SharedAdmission(
                first=first,
                second=second,
                redis=admin,
                headers_a=headers_a,
                headers_b=headers_b,
                workspace_a=workspace_a,
                workspace_b=workspace_b,
                key_a=key_a,
                key_b=key_b,
                window_seconds=window,
            )
    finally:
        try:
            admin.delete(key_a, key_b)
        finally:
            admin.close()


def test_two_api_instances_share_workspace_quota_but_not_other_workspace(
    shared_admission: SharedAdmission,
) -> None:
    cluster = shared_admission
    assert cluster.first.get("/healthz").status_code == 200
    assert cluster.second.get("/healthz").status_code == 200
    assert cluster.redis.exists(cluster.key_a, cluster.key_b) == 0

    assert cluster.first.get("/v1/usage", headers=cluster.headers_a).status_code == 200
    assert cluster.second.get("/v1/usage", headers=cluster.headers_a).status_code == 200
    assert cluster.redis.get(cluster.key_a) == b"2"
    for client in (cluster.first, cluster.second):
        denied = client.get(
            f"/v1/usage?workspace_id={cluster.workspace_b}", headers=cluster.headers_a
        )
        assert denied.status_code == 429, denied.text
        assert 1 <= int(denied.headers["Retry-After"]) <= cluster.window_seconds
        assert denied.json() == {"detail": "Workspace request limit exceeded."}
    assert cluster.redis.get(cluster.key_a) == b"2"
    assert cluster.redis.exists(cluster.key_b) == 0

    # A's exhausted quota cannot block B; B also shares one quota across replicas.
    assert cluster.second.get("/v1/usage", headers=cluster.headers_b).status_code == 200
    assert cluster.first.get("/v1/usage", headers=cluster.headers_b).status_code == 200
    assert cluster.redis.get(cluster.key_b) == b"2"
    assert cluster.second.get("/v1/usage", headers=cluster.headers_b).status_code == 429
    unauthenticated = cluster.first.get("/v1/usage", headers={"Authorization": "Bearer invalid"})
    assert unauthenticated.status_code == 401
    assert cluster.redis.get(cluster.key_a) == cluster.redis.get(cluster.key_b) == b"2"


def test_wrongtype_limiter_key_fails_closed_without_write_or_cross_workspace_outage(
    shared_admission: SharedAdmission,
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    cluster = shared_admission
    cluster.redis.rpush(cluster.key_a, "test-only-wrongtype")
    try:
        for client in (cluster.first, cluster.second):
            unavailable = client.post(
                "/v1/agents", headers=cluster.headers_a, json={"name": "must-not-be-created"}
            )
            assert unavailable.status_code == 503, unavailable.text
            assert unavailable.json() == {"detail": "Admission unavailable."}
            assert "WRONGTYPE" not in unavailable.text
            assert cluster.key_a not in unavailable.text
            assert client.get("/healthz").status_code == 200
        with sqlite_session_factory() as session:
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(AgentRecord)
                    .where(AgentRecord.workspace_id == str(cluster.workspace_a))
                )
                == 0
            )
        assert cluster.second.get("/v1/usage", headers=cluster.headers_b).status_code == 200
        assert cluster.redis.get(cluster.key_b) == b"1"
        assert cluster.redis.type(cluster.key_a) == b"list"
    finally:
        # Only the randomly generated test key is repaired; never flush or stop Redis.
        cluster.redis.delete(cluster.key_a)

    assert cluster.first.get("/v1/usage", headers=cluster.headers_a).status_code == 200
    assert cluster.redis.get(cluster.key_a) == b"1"
