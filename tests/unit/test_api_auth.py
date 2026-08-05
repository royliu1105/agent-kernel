from uuid import UUID

from agent_kernel_api.auth import api_key_auth_enabled_from_env
from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from kernel_core import RiskLevel, ToolCallStatus
from kernel_identity import PrincipalType, WorkspaceRole
from kernel_storage import (
    AgentRepository,
    ApiKeyRepository,
    ApprovalRepository,
    PrincipalRepository,
    RunRepository,
    ToolCallRepository,
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)
from pytest import MonkeyPatch
from sqlalchemy.orm import Session, sessionmaker


def test_healthz_stays_public_when_api_key_auth_is_enabled(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "agent-kernel-api"}


def test_api_key_auth_rejects_missing_key(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.post("/v1/agents", json={"name": "blocked"})

    assert response.status_code == 401
    assert response.json() == {"detail": "API key is required."}


def test_api_key_auth_rejects_invalid_key(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.post(
        "/v1/agents",
        json={"name": "blocked"},
        headers={"Authorization": "Bearer ak_invalid"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "API key is invalid, revoked, or expired."}


def test_api_key_auth_enabled_from_env_parses_truthy_and_falsey_values(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_KERNEL_API_KEY_AUTH_ENABLED", "true")
    assert api_key_auth_enabled_from_env() is True

    monkeypatch.setenv("AGENT_KERNEL_API_KEY_AUTH_ENABLED", "1")
    assert api_key_auth_enabled_from_env() is True

    monkeypatch.setenv("AGENT_KERNEL_API_KEY_AUTH_ENABLED", "off")
    assert api_key_auth_enabled_from_env() is False

    monkeypatch.delenv("AGENT_KERNEL_API_KEY_AUTH_ENABLED", raising=False)
    assert api_key_auth_enabled_from_env() is False


def test_api_key_auth_accepts_bearer_key_and_updates_last_used(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    plaintext_key = _issue_api_key(sqlite_session_factory, "ak_bearer_secret")
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.post(
        "/v1/agents",
        json={"name": "authenticated"},
        headers={"Authorization": f"Bearer {plaintext_key}"},
    )
    with sqlite_session_factory() as session:
        authenticated_key = ApiKeyRepository(session).authenticate(plaintext_key)

    assert response.status_code == 201
    assert response.json()["name"] == "authenticated"
    assert authenticated_key is not None
    assert authenticated_key.last_used_at is not None


def test_api_key_auth_accepts_agent_kernel_api_key_header(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    plaintext_key = _issue_api_key(sqlite_session_factory, "ak_header_secret")
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.post(
        "/v1/agents",
        json={"name": "header-authenticated"},
        headers={"X-Agent-Kernel-Api-Key": plaintext_key},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "header-authenticated"


def test_route_authorization_rejects_viewer_write(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    plaintext_key = _issue_api_key(
        sqlite_session_factory,
        "ak_viewer_secret",
        role=WorkspaceRole.VIEWER,
    )
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.post(
        "/v1/agents",
        json={"name": "blocked"},
        headers={"Authorization": f"Bearer {plaintext_key}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Permission 'agent:write' is required."}


def test_route_authorization_allows_viewer_read(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    plaintext_key, workspace_id = _issue_api_key_with_workspace(
        sqlite_session_factory,
        "ak_viewer_read_secret",
        role=WorkspaceRole.VIEWER,
    )
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(
            name="readable-agent",
            workspace_id=workspace_id,
        )
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.get(
        f"/v1/agents/{agent.id}",
        headers={"Authorization": f"Bearer {plaintext_key}"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "readable-agent"


def test_route_authorization_allows_operator_write(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    plaintext_key = _issue_api_key(
        sqlite_session_factory,
        "ak_operator_write_secret",
        role=WorkspaceRole.OPERATOR,
    )
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.post(
        "/v1/agents",
        json={"name": "operator-created"},
        headers={"Authorization": f"Bearer {plaintext_key}"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "operator-created"


def test_route_authorization_rejects_viewer_approval_review(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    plaintext_key, workspace_id = _issue_api_key_with_workspace(
        sqlite_session_factory,
        "ak_viewer_approval_review",
        role=WorkspaceRole.VIEWER,
    )
    _approval_id = _create_requested_approval(sqlite_session_factory, workspace_id=workspace_id)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.get(
        "/v1/approvals",
        headers={"Authorization": f"Bearer {plaintext_key}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Permission 'approval:review' is required."}


def test_authenticated_agent_create_uses_api_key_workspace(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    plaintext_key, workspace_id = _issue_api_key_with_workspace(
        sqlite_session_factory,
        "ak_scoped_agent_secret",
        role=WorkspaceRole.OPERATOR,
    )
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.post(
        "/v1/agents",
        json={"name": "scoped-agent"},
        headers={"Authorization": f"Bearer {plaintext_key}"},
    )

    assert response.status_code == 201
    assert response.json()["workspace_id"] == str(workspace_id)


def test_agent_read_is_workspace_scoped(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    key_a = _issue_api_key(sqlite_session_factory, "ak_workspace_a")
    key_b = _issue_api_key(sqlite_session_factory, "ak_workspace_b")
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )
    created = client.post(
        "/v1/agents",
        json={"name": "private-agent"},
        headers={"Authorization": f"Bearer {key_a}"},
    ).json()

    response = client.get(
        f"/v1/agents/{created['id']}",
        headers={"Authorization": f"Bearer {key_b}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Agent not found"}


def test_run_create_requires_agent_in_current_workspace(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    key_a = _issue_api_key(sqlite_session_factory, "ak_run_workspace_a")
    key_b = _issue_api_key(sqlite_session_factory, "ak_run_workspace_b")
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )
    created = client.post(
        "/v1/agents",
        json={"name": "run-agent"},
        headers={"Authorization": f"Bearer {key_a}"},
    ).json()

    response = client.post(
        f"/v1/agents/{created['id']}/runs",
        json={"input": {"task": "blocked"}},
        headers={"Authorization": f"Bearer {key_b}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Agent not found"}


def test_run_read_is_workspace_scoped(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    key_a = _issue_api_key(sqlite_session_factory, "ak_run_read_workspace_a")
    key_b = _issue_api_key(sqlite_session_factory, "ak_run_read_workspace_b")
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )
    agent = client.post(
        "/v1/agents",
        json={"name": "run-read-agent"},
        headers={"Authorization": f"Bearer {key_a}"},
    ).json()
    run = client.post(
        f"/v1/agents/{agent['id']}/runs",
        json={"input": {"task": "private"}},
        headers={"Authorization": f"Bearer {key_a}"},
    ).json()

    response = client.get(
        f"/v1/runs/{run['id']}",
        headers={"Authorization": f"Bearer {key_b}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}


def test_approval_list_is_workspace_scoped(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    key_a, workspace_a = _issue_api_key_with_workspace(
        sqlite_session_factory,
        "ak_approval_list_a",
    )
    _key_b, workspace_b = _issue_api_key_with_workspace(
        sqlite_session_factory,
        "ak_approval_list_b",
    )
    approval_a = _create_requested_approval(sqlite_session_factory, workspace_id=workspace_a)
    _approval_b = _create_requested_approval(sqlite_session_factory, workspace_id=workspace_b)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.get(
        "/v1/approvals",
        headers={"Authorization": f"Bearer {key_a}"},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(approval_a)]


def test_approval_get_and_decision_are_workspace_scoped(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    key_a, workspace_a = _issue_api_key_with_workspace(
        sqlite_session_factory,
        "ak_approval_decision_a",
    )
    key_b, workspace_b = _issue_api_key_with_workspace(
        sqlite_session_factory,
        "ak_approval_decision_b",
    )
    approval_a = _create_requested_approval(sqlite_session_factory, workspace_id=workspace_a)
    approval_b = _create_requested_approval(sqlite_session_factory, workspace_id=workspace_b)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    hidden_get = client.get(
        f"/v1/approvals/{approval_a}",
        headers={"Authorization": f"Bearer {key_b}"},
    )
    hidden_approve = client.post(
        f"/v1/approvals/{approval_a}/approve",
        json={"decision_note": "Cross workspace."},
        headers={"Authorization": f"Bearer {key_b}"},
    )
    same_workspace_reject = client.post(
        f"/v1/approvals/{approval_b}/reject",
        json={"reason": "Same workspace reject."},
        headers={"Authorization": f"Bearer {key_b}"},
    )

    assert hidden_get.status_code == 404
    assert hidden_get.json() == {"detail": "Approval not found"}
    assert hidden_approve.status_code == 404
    assert hidden_approve.json() == {"detail": "Approval not found"}
    assert same_workspace_reject.status_code == 200
    assert same_workspace_reject.json()["status"] == "rejected"
    assert same_workspace_reject.json()["decision_note"] == "Same workspace reject."

    allowed_get = client.get(
        f"/v1/approvals/{approval_a}",
        headers={"Authorization": f"Bearer {key_a}"},
    )
    assert allowed_get.status_code == 200
    assert allowed_get.json()["id"] == str(approval_a)


def test_approval_decision_records_authenticated_reviewer(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    plaintext_key, workspace_id = _issue_api_key_with_workspace(
        sqlite_session_factory,
        "ak_approval_reviewer",
    )
    approval_id = _create_requested_approval(sqlite_session_factory, workspace_id=workspace_id)
    with sqlite_session_factory() as session:
        api_key = ApiKeyRepository(session).authenticate(plaintext_key)
        assert api_key is not None
        principal_id = api_key.principal_id
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.post(
        f"/v1/approvals/{approval_id}/approve",
        json={"decision_note": "Approved by authenticated reviewer."},
        headers={"Authorization": f"Bearer {plaintext_key}"},
    )

    assert response.status_code == 200
    assert response.json()["reviewed_by"] == str(principal_id)


def test_run_resume_rejects_cross_workspace_approval(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    key_a, workspace_a = _issue_api_key_with_workspace(
        sqlite_session_factory,
        "ak_resume_workspace_a",
    )
    _key_b, workspace_b = _issue_api_key_with_workspace(
        sqlite_session_factory,
        "ak_resume_workspace_b",
    )
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="resume-agent", workspace_id=workspace_a)
        run = RunRepository(session).create(
            agent_id=agent.id,
            workspace_id=workspace_a,
            input_payload={"task": "resume"},
        )
    approval_b = _create_requested_approval(sqlite_session_factory, workspace_id=workspace_b)
    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.post(
        f"/v1/runs/{run.id}/resume",
        json={"approval_id": str(approval_b)},
        headers={"Authorization": f"Bearer {key_a}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Approval not found"}


def test_api_key_auth_rejects_disabled_principal(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    plaintext_key = _issue_api_key(sqlite_session_factory, "ak_disabled_secret")
    with sqlite_session_factory() as session:
        api_key = ApiKeyRepository(session).authenticate(plaintext_key)
        assert api_key is not None
        principal = PrincipalRepository(session).set_disabled(
            principal_id=api_key.principal_id,
            disabled=True,
        )
        assert principal is not None

    client = TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=True)
    )

    response = client.post(
        "/v1/agents",
        json={"name": "blocked"},
        headers={"Authorization": f"Bearer {plaintext_key}"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "API key principal is unavailable."}


def test_api_key_auth_is_disabled_by_default(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))

    response = client.post("/v1/agents", json={"name": "local-dev"})

    assert response.status_code == 201
    assert response.json()["name"] == "local-dev"


def _issue_api_key(
    sqlite_session_factory: sessionmaker[Session],
    plaintext_key: str,
    *,
    role: WorkspaceRole = WorkspaceRole.OPERATOR,
) -> str:
    plaintext, _workspace_id = _issue_api_key_with_workspace(
        sqlite_session_factory,
        plaintext_key,
        role=role,
    )
    return plaintext


def _issue_api_key_with_workspace(
    sqlite_session_factory: sessionmaker[Session],
    plaintext_key: str,
    *,
    role: WorkspaceRole = WorkspaceRole.OPERATOR,
) -> tuple[str, UUID]:
    with sqlite_session_factory() as session:
        principal = PrincipalRepository(session).create(
            type=PrincipalType.USER,
            display_name="API User",
        )
        workspace = WorkspaceRepository(session).create(name="API", slug=plaintext_key)
        WorkspaceMembershipRepository(session).assign(
            principal_id=principal.id,
            workspace_id=workspace.id,
            role=role,
        )
        credential = ApiKeyRepository(session).issue(
            workspace_id=workspace.id,
            principal_id=principal.id,
            name="Test key",
            plaintext_key=plaintext_key,
        )
        assert credential is not None
        return credential.plaintext_key, workspace.id


def _create_requested_approval(
    sqlite_session_factory: sessionmaker[Session],
    *,
    workspace_id: UUID,
) -> UUID:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(
            name="approval-agent",
            workspace_id=workspace_id,
        )
        run = RunRepository(session).create(
            agent_id=agent.id,
            workspace_id=workspace_id,
            input_payload={"task": "approve"},
        )
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
