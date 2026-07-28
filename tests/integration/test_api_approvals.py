from uuid import UUID

from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from kernel_core import RiskLevel, ToolCallStatus
from kernel_storage import AgentRepository, ApprovalRepository, RunRepository, ToolCallRepository
from sqlalchemy.orm import Session, sessionmaker


def test_approval_api_lists_gets_and_approves(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    approval_id = _create_requested_approval(sqlite_session_factory)
    client = TestClient(create_app(session_factory=sqlite_session_factory))

    list_response = client.get("/v1/approvals")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [str(approval_id)]

    filtered_response = client.get("/v1/approvals?status=requested")
    assert filtered_response.status_code == 200
    assert [item["id"] for item in filtered_response.json()] == [str(approval_id)]

    get_response = client.get(f"/v1/approvals/{approval_id}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "requested"

    approve_response = client.post(
        f"/v1/approvals/{approval_id}/approve",
        json={"decision_note": "Approved by API test."},
    )
    assert approve_response.status_code == 200
    approved = approve_response.json()
    assert approved["status"] == "approved"
    assert approved["decision_note"] == "Approved by API test."
    assert approved["resolved_at"] is not None

    duplicate_response = client.post(f"/v1/approvals/{approval_id}/approve", json={})
    assert duplicate_response.status_code == 409
    assert "already been decided" in duplicate_response.json()["detail"]


def test_approval_api_rejects_with_reason(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    approval_id = _create_requested_approval(sqlite_session_factory)
    client = TestClient(create_app(session_factory=sqlite_session_factory))

    reject_response = client.post(
        f"/v1/approvals/{approval_id}/reject",
        json={"reason": "Too risky."},
    )

    assert reject_response.status_code == 200
    rejected = reject_response.json()
    assert rejected["status"] == "rejected"
    assert rejected["decision_note"] == "Too risky."


def test_approval_api_returns_404_for_missing_approval(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    missing_id = "00000000-0000-0000-0000-000000000000"

    get_response = client.get(f"/v1/approvals/{missing_id}")
    approve_response = client.post(f"/v1/approvals/{missing_id}/approve", json={})
    reject_response = client.post(
        f"/v1/approvals/{missing_id}/reject",
        json={"reason": "Nope."},
    )

    assert get_response.status_code == 404
    assert approve_response.status_code == 404
    assert reject_response.status_code == 404


def _create_requested_approval(session_factory: sessionmaker[Session]) -> UUID:
    with session_factory() as session:
        agent = AgentRepository(session).create(name="api-approval-agent")
        run = RunRepository(session).create(agent_id=agent.id, input_payload={"task": "approve"})
        tool_call_repository = ToolCallRepository(session)
        tool_call = tool_call_repository.create_requested(
            run_id=run.id,
            tool_name="network-tool",
            arguments={},
            risk_level=RiskLevel.NETWORK,
        )
        assert tool_call is not None
        waiting = tool_call_repository.record_policy_decision(
            tool_call_id=tool_call.id,
            decision="require_approval",
            reason="Network tool requires approval.",
            status=ToolCallStatus.WAITING_APPROVAL,
            requires_approval=True,
        )
        assert waiting is not None
        approval = ApprovalRepository(session).create_requested(
            tool_call_id=waiting.id,
            reason="Network tool requires approval.",
        )
        assert approval is not None
        return approval.id
