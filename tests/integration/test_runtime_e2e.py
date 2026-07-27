import pytest
from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from kernel_providers import MockLLMProvider
from kernel_runtime import ModelRouter, QueuedRunWorker, RunExecutionService
from sqlalchemy.orm import Session, sessionmaker


@pytest.mark.asyncio
async def test_api_created_run_is_executed_by_worker(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))

    agent_response = client.post("/v1/agents", json={"name": "e2e-agent"})
    assert agent_response.status_code == 201
    agent = agent_response.json()

    run_response = client.post(
        f"/v1/agents/{agent['id']}/runs",
        json={"input": {"task": "hello e2e", "model": "mock:e2e"}},
    )
    assert run_response.status_code == 201
    run = run_response.json()

    queue_response = client.post(f"/v1/runs/{run['id']}/queue")
    assert queue_response.status_code == 200
    assert queue_response.json()["status"] == "queued"

    worker = QueuedRunWorker(
        session_factory=sqlite_session_factory,
        execution_service=RunExecutionService(
            router=ModelRouter({"mock": MockLLMProvider(response_prefix="E2E")})
        ),
    )
    worker_result = await worker.run_once(limit=10)
    assert worker_result.processed_count == 1
    assert worker_result.succeeded_count == 1

    inspect_response = client.get(f"/v1/runs/{run['id']}")
    assert inspect_response.status_code == 200
    completed = inspect_response.json()
    assert completed["status"] == "succeeded"
    assert completed["output"] == {
        "text": "E2E: hello e2e",
        "provider": "mock",
        "model": "e2e",
        "usage": {
            "input_tokens": 2,
            "output_tokens": 3,
            "estimated_cost": 0.0,
        },
    }

    events_response = client.get(f"/v1/runs/{run['id']}/events")
    assert events_response.status_code == 200
    assert [event["type"] for event in events_response.json()] == [
        "run_created",
        "run_queued",
        "run_started",
        "run_completed",
    ]
