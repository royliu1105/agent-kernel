import asyncio
from typing import Any

from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from kernel_core import RiskLevel, RunEventType, RunStatus
from kernel_observability import TRACE_ID_PATTERN
from kernel_runtime import RunExecutionService
from kernel_storage import AgentRepository, ApprovalRepository, RunRepository
from kernel_tools import ToolMetadata, ToolRegistry, create_default_tool_registry
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
    assert TRACE_ID_PATTERN.fullmatch(run["trace_id"])

    get_run_response = client.get(f"/v1/runs/{run['id']}")
    assert get_run_response.status_code == 200
    loaded_run = get_run_response.json()
    assert loaded_run["id"] == run["id"]
    assert loaded_run["trace_id"] == run["trace_id"]

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
            "trace_id": run["trace_id"],
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


def test_queue_and_cancel_run_transitions(sqlite_session_factory: sessionmaker[Session]) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    agent = client.post("/v1/agents", json={"name": "ops-agent"}).json()
    run = client.post(
        f"/v1/agents/{agent['id']}/runs",
        json={"input": {"task": "queue then cancel"}},
    ).json()

    queue_response = client.post(f"/v1/runs/{run['id']}/queue")
    assert queue_response.status_code == 200
    assert queue_response.json()["status"] == "queued"

    cancel_response = client.post(f"/v1/runs/{run['id']}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "canceled"

    events_response = client.get(f"/v1/runs/{run['id']}/events")
    assert events_response.status_code == 200
    events = events_response.json()
    assert [event["type"] for event in events] == [
        "run_created",
        "run_queued",
        "run_canceled",
    ]
    assert {event["trace_id"] for event in events} == {run["trace_id"]}


def test_invalid_api_transition_returns_409(sqlite_session_factory: sessionmaker[Session]) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    agent = client.post("/v1/agents", json={"name": "ops-agent"}).json()
    run = client.post(f"/v1/agents/{agent['id']}/runs", json={"input": {}}).json()

    cancel_response = client.post(f"/v1/runs/{run['id']}/cancel")
    assert cancel_response.status_code == 200

    queue_response = client.post(f"/v1/runs/{run['id']}/queue")
    assert queue_response.status_code == 409
    assert "Cannot transition run from canceled to queued" in queue_response.json()["detail"]


def test_resume_waiting_run_through_api(sqlite_session_factory: sessionmaker[Session]) -> None:
    execution_service = RunExecutionService(tool_registry=_approval_tool_registry())
    client = TestClient(
        create_app(
            session_factory=sqlite_session_factory,
            execution_service=execution_service,
        )
    )
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="api-resume-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "external_write", "arguments": {"value": "draft"}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        waiting = asyncio.run(execution_service.execute(run_id=run.id, repository=run_repository))
        approval = ApprovalRepository(session).list_for_run(run.id)[0]

    assert waiting.status is RunStatus.WAITING_APPROVAL

    approve_response = client.post(
        f"/v1/approvals/{approval.id}/approve",
        json={"decision_note": "Approved from API."},
    )
    resume_response = client.post(
        f"/v1/runs/{run.id}/resume",
        json={"approval_id": str(approval.id)},
    )

    assert approve_response.status_code == 200
    assert resume_response.status_code == 200
    resumed = resume_response.json()
    assert resumed["status"] == "succeeded"
    assert resumed["output"]["tool"]["result"] == {"written": "draft"}


def test_resume_requested_approval_returns_409(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    execution_service = RunExecutionService(tool_registry=_approval_tool_registry())
    client = TestClient(
        create_app(
            session_factory=sqlite_session_factory,
            execution_service=execution_service,
        )
    )
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="api-resume-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "external_write", "arguments": {"value": "draft"}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        asyncio.run(execution_service.execute(run_id=run.id, repository=run_repository))
        approval = ApprovalRepository(session).list_for_run(run.id)[0]

    resume_response = client.post(
        f"/v1/runs/{run.id}/resume",
        json={"approval_id": str(approval.id)},
    )

    assert resume_response.status_code == 409
    assert "has not been decided yet" in resume_response.json()["detail"]


class ExternalWriteTool:
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="external_write",
            description="Test-only external write tool.",
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
                "additionalProperties": False,
            },
            risk_level=RiskLevel.EXTERNAL_WRITE,
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"written": arguments["value"]}


def _approval_tool_registry() -> ToolRegistry:
    registry = create_default_tool_registry()
    registry.register(ExternalWriteTool())
    return registry
