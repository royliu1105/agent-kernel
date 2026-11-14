from pathlib import Path

import pytest
from kernel_core import MemoryType, RunEventType, RunStatus
from kernel_rag import LocalObjectStore
from kernel_runtime import RunExecutionService
from kernel_storage import AgentRepository, EvalRunRepository, MemoryRepository, RunRepository
from sqlalchemy.orm import Session, sessionmaker
from test_bounded_native_execution import ScriptedProvider, reply
from test_knowledge_workspace_isolation import _client


def test_memory_and_evals_do_not_cross_workspaces(
    postgres_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    store = LocalObjectStore(root_path=tmp_path)
    a, workspace_a = _client(postgres_session_factory, store)
    b, workspace_b = _client(postgres_session_factory, store)
    with postgres_session_factory() as session:
        legacy = MemoryRepository(session).create(
            type=MemoryType.LONG_TERM, scope="same", content={}
        )
        legacy_eval = EvalRunRepository(session).create_from_report(
            name="legacy",
            suite_type="x",
            report={"case_count": 0, "passed_count": 0, "failed_count": 0},
        )
        agent_b = AgentRepository(session).create(name="b", workspace_id=workspace_b)
        run_b = RunRepository(session).create(
            agent_id=agent_b.id, workspace_id=workspace_b, input_payload={}
        )
    memory = a.post(
        "/v1/memory", json={"type": "long_term", "scope": "same", "content": {"secret": "a"}}
    )
    assert memory.status_code == 201
    record = memory.json()
    assert record["workspace_id"] == str(workspace_a)
    assert a.get(f"/v1/memory/{legacy.id}").status_code == 404
    assert b.get("/v1/memory?scope=same").json() == []
    assert b.get(f"/v1/memory/{record['id']}").status_code == 404
    assert b.delete(f"/v1/memory/{record['id']}").status_code == 404
    assert a.get(f"/v1/memory/{record['id']}").status_code == 200
    forged = a.post(
        "/v1/memory",
        json={
            "type": "task_context",
            "scope": "same",
            "content": {},
            "source_run_id": str(run_b.id),
        },
    )
    assert forged.status_code == 404
    evaluation = a.post(
        "/v1/evals/runs",
        json={
            "name": "a",
            "report": {
                "passed": True,
                "case_count": 0,
                "passed_count": 0,
                "failed_count": 0,
            },
        },
    )
    assert evaluation.status_code == 201
    assert evaluation.json()["workspace_id"] == str(workspace_a)
    assert b.get(f"/v1/evals/runs/{evaluation.json()['id']}").status_code == 404
    assert a.get(f"/v1/evals/runs/{legacy_eval.id}").status_code == 404
    assert b.get("/v1/evals/runs").json() == []
    assert len(a.get("/v1/evals/runs").json()) == 1
    assert a.delete(f"/v1/memory/{record['id']}").status_code == 200


@pytest.mark.asyncio
async def test_runtime_memory_scope_is_not_an_authorization_override(
    postgres_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    store = LocalObjectStore(root_path=tmp_path)
    _, a = _client(postgres_session_factory, store)
    _, b = _client(postgres_session_factory, store)
    provider = ScriptedProvider([reply(text="done")])
    with postgres_session_factory() as session:
        MemoryRepository(session, workspace_id=b).create(
            type=MemoryType.USER_PREFERENCE, scope="shared-label", content={"value": "SECRET-B"}
        )
        agent = AgentRepository(session).create(name="a", workspace_id=a)
        repo = RunRepository(session)
        run = repo.create(
            agent_id=agent.id,
            workspace_id=a,
            input_payload={
                "task": "hello",
                "model": "scripted:small",
                "memory": {"scopes": ["shared-label"]},
                "workspace_id": str(b),
            },
        )
        repo.apply_transition(
            run_id=run.id, status=RunStatus.QUEUED, event_type=RunEventType.RUN_QUEUED, payload={}
        )
        done = await RunExecutionService(provider=provider).execute(run_id=run.id, repository=repo)
        assert done.status is RunStatus.SUCCEEDED
        events = repo.list_events(run.id)
        memory_event = next(
            event for event in events if event.type is RunEventType.MEMORY_RETRIEVED
        )
        assert memory_event.payload["item_count"] == 0
        assert "SECRET-B" not in str(done.output)
        assert "SECRET-B" not in provider.requests[0].model_dump_json()
