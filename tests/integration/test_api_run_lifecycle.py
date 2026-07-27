from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker


def test_create_agent_run_and_inspect_timeline(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))

    agent_response = client.post(
        "/v1/agents",
        json={"name": "research-agent", "description": "Research assistant"},
    )
    assert agent_response.status_code == 201
    agent = agent_response.json()
    assert agent["name"] == "research-agent"

    run_response = client.post(
        f"/v1/agents/{agent['id']}/runs",
        json={"input": {"task": "summarize latest notes"}},
    )
    assert run_response.status_code == 201
    run = run_response.json()
    assert run["agent_id"] == agent["id"]
    assert run["status"] == "created"
    assert run["input"] == {"task": "summarize latest notes"}

    get_run_response = client.get(f"/v1/runs/{run['id']}")
    assert get_run_response.status_code == 200
    assert get_run_response.json()["id"] == run["id"]

    events_response = client.get(f"/v1/runs/{run['id']}/events")
    assert events_response.status_code == 200
    events = events_response.json()
    assert events == [
        {
            "id": events[0]["id"],
            "run_id": run["id"],
            "sequence": 1,
            "type": "run_created",
            "payload": {"status": "created"},
            "trace_id": None,
            "created_at": events[0]["created_at"],
        }
    ]


def test_create_run_for_missing_agent_returns_404(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))

    response = client.post(
        "/v1/agents/00000000-0000-0000-0000-000000000000/runs",
        json={"input": {"task": "noop"}},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Agent not found"}
