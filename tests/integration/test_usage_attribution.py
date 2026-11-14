"""Cost attribution uses trusted identities and persisted provider responses."""

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from kernel_rag import LocalObjectStore
from kernel_storage import RunRepository
from sqlalchemy.orm import Session, sessionmaker
from test_knowledge_workspace_isolation import _client


def test_api_cost_dimensions_are_scoped_and_principal_cannot_be_spoofed(
    postgres_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    store = LocalObjectStore(root_path=tmp_path)
    client, workspace = _client(postgres_session_factory, store)
    other, _ = _client(postgres_session_factory, store)
    with client, other:
        agent = client.post("/v1/agents", json={"name": "attribution"}).json()
        forged = str(uuid4())
        response = client.post(
            f"/v1/agents/{agent['id']}/runs",
            json={
                "input": {"task": "x", "principal_id": forged, "workspace_id": forged},
            },
        )
        assert response.status_code == 201, response.text
        run_id = UUID(response.json()["id"])
        with postgres_session_factory() as session:
            repo = RunRepository(session)
            run = repo.get(run_id)
            assert run is not None and run.principal_id is not None
            assert str(run.principal_id) != forged
            assert run.workspace_id == workspace
            for model, cost in (("first", 0.1), ("second", 0.2)):
                repo.record_usage(
                    run_id,
                    input_tokens=10,
                    output_tokens=2,
                    estimated_cost=cost,
                    provider="fixture",
                    model=model,
                )
        for group_by in ("workspace", "principal", "run", "model"):
            path = f"/v1/usage/breakdown?group_by={group_by}"
            own = client.get(path)
            assert own.status_code == 200, own.text
            items = own.json()["items"]
            assert sum(item["estimated_cost"] for item in items) == pytest.approx(0.3)
            assert own.json()["estimated"] is True
            assert other.get(path).json()["items"] == []
            assert (
                other.get(f"{path}&run_id={run_id}&workspace_id={workspace}").json()["items"] == []
            )
        models = client.get("/v1/usage/breakdown?group_by=model").json()["items"]
        assert {item["model"] for item in models} == {"first", "second"}
        assert {item["provider"] for item in models} == {"fixture"}
        assert client.get("/v1/usage/breakdown?group_by=raw_input").status_code == 422
        assert client.get("/v1/usage/breakdown?limit=1001").status_code == 422


def test_unknown_local_initiator_is_not_inferred_from_input(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    from kernel_storage import AgentRepository

    with postgres_session_factory() as session:
        agent = AgentRepository(session).create(name="local")
        repo = RunRepository(session)
        run = repo.create(agent_id=agent.id, input_payload={"principal_id": str(uuid4())})
        repo.record_usage(run.id, input_tokens=1, output_tokens=2, estimated_cost=0.01)
        assert repo.usage_breakdown(group_by="principal")[0]["principal"] is None
        assert repo.usage_breakdown(group_by="model")[0]["model"] == "unknown"
