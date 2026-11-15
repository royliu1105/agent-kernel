"""Web identity and agent discovery against the isolated PostgreSQL fixture."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from kernel_core import RiskLevel
from kernel_identity import (
    ApiKeyCredential,
    ApiKeyStatus,
    Permission,
    PrincipalType,
    WorkspaceRole,
    WorkspaceStatus,
)
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
from kernel_storage.models import (
    AgentRecord,
    ApiKeyRecord,
    PrincipalRecord,
    WorkspaceMembershipRecord,
    WorkspaceRecord,
)
from sqlalchemy import delete, update
from sqlalchemy.orm import Session, sessionmaker


def test_approval_detail_binds_scoped_arguments_without_raw_provider_payload(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    operator = _issue_key(postgres_session_factory)
    viewer = _issue_key(postgres_session_factory, WorkspaceRole.VIEWER)
    other = _issue_key(postgres_session_factory)
    with postgres_session_factory() as session:
        agent = AgentRepository(session).create(
            name="Approval details", workspace_id=operator.api_key.workspace_id
        )
        run = RunRepository(session).create(
            agent_id=agent.id, workspace_id=operator.api_key.workspace_id, input_payload={}
        )
        tool = ToolCallRepository(session).create_requested(
            run_id=run.id,
            tool_name="inventory_lookup",
            arguments={"item_id": "synthetic"},
            risk_level=RiskLevel.READ_ONLY,
            requires_approval=True,
            raw_provider_payload={"private_transport_metadata": "not-in-response"},
        )
        assert tool is not None
        approval = ApprovalRepository(session).create_requested(
            tool_call_id=tool.id, reason="Review"
        )
        assert approval is not None
    endpoint = f"/v1/approvals/{approval.id}/tool-call"
    with TestClient(
        create_app(session_factory=postgres_session_factory, api_key_auth_enabled=True)
    ) as client:
        response = client.get(endpoint, headers=_headers(operator))
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "id": str(tool.id),
            "run_id": str(run.id),
            "tool_name": "inventory_lookup",
            "arguments": {"item_id": "synthetic"},
            "status": "waiting_approval",
            "risk_level": "read_only",
            "approval_id": str(approval.id),
        }
        assert "not-in-response" not in response.text
        assert client.get(endpoint).status_code == 401
        assert client.get(endpoint, headers=_headers(viewer)).status_code == 403
        assert client.get(endpoint, headers=_headers(other)).status_code == 404
        assert (
            client.get(f"/v1/approvals/{uuid4()}/tool-call", headers=_headers(operator)).status_code
            == 404
        )


@pytest.fixture(autouse=True)
def isolated_api_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_KERNEL_RUN_QUEUE_BACKEND", "database")
    monkeypatch.setenv("AGENT_KERNEL_EMBEDDING_PROVIDER", "mock")
    monkeypatch.delenv("AGENT_KERNEL_EXTERNAL_TOOLS_CONFIG", raising=False)
    for scope in ("", "PRINCIPAL_", "API_KEY_"):
        monkeypatch.setenv(f"AGENT_KERNEL_RATE_LIMIT_{scope}REQUESTS", "0")


def _issue_key(
    factory: sessionmaker[Session], role: WorkspaceRole = WorkspaceRole.OPERATOR
) -> ApiKeyCredential:
    with factory() as session:
        principal = PrincipalRepository(session).create(
            type=PrincipalType.USER, display_name="Web User"
        )
        workspace = WorkspaceRepository(session).create(name="Web", slug=uuid4().hex)
        WorkspaceMembershipRepository(session).assign(
            principal_id=principal.id, workspace_id=workspace.id, role=role
        )
        credential = ApiKeyRepository(session).issue(
            principal_id=principal.id, workspace_id=workspace.id, name="Web test"
        )
        assert credential is not None
        return credential


def _headers(credential: ApiKeyCredential) -> dict[str, str]:
    return {"Authorization": f"Bearer {credential.plaintext_key}"}


@pytest.mark.parametrize("role", [WorkspaceRole.VIEWER, WorkspaceRole.OPERATOR])
@pytest.mark.parametrize("header", ["Authorization", "X-Agent-Kernel-Api-Key"])
def test_identity_reports_current_workspace_role_and_permissions(
    postgres_session_factory: sessionmaker[Session], role: WorkspaceRole, header: str
) -> None:
    credential = _issue_key(postgres_session_factory, role)
    key = credential.api_key
    with postgres_session_factory() as session:
        other = WorkspaceRepository(session).create(name="Other", slug=uuid4().hex)
        WorkspaceMembershipRepository(session).assign(
            principal_id=key.principal_id, workspace_id=other.id, role=WorkspaceRole.OWNER
        )
    permissions = {
        "workspace:read",
        "agent:read",
        "run:read",
        "knowledge:read",
        "memory:read",
        "eval:read",
    }
    if role is WorkspaceRole.OPERATOR:
        permissions.update(
            {
                "agent:write",
                "run:write",
                "approval:review",
                "tool:execute",
                "knowledge:write",
                "memory:write",
                "eval:write",
            }
        )
    value = credential.plaintext_key
    if header == "Authorization":
        value = f"Bearer {value}"
    with TestClient(
        create_app(session_factory=postgres_session_factory, api_key_auth_enabled=True),
        headers={header: value},
    ) as client:
        response = client.get("/v1/auth/me")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "authenticated": True,
            "principal_id": str(key.principal_id),
            "display_name": "Web User",
            "workspace_id": str(key.workspace_id),
            "role": role.value,
            "permissions": sorted(permissions),
        }
        for secret in (credential.plaintext_key, key.key_hash, key.key_prefix):
            assert secret not in response.text
            assert secret not in str(response.headers)
        assert client.get("/v1/agents").status_code == 200
        created = client.post("/v1/agents", json={"name": "Web agent"})
        assert created.status_code == (403 if role is WorkspaceRole.VIEWER else 201)
        approvals = client.get("/v1/approvals")
        assert approvals.status_code == (403 if role is WorkspaceRole.VIEWER else 200)


@pytest.mark.parametrize(
    ("state", "expected_status"),
    [
        ("missing", 401),
        ("invalid", 401),
        ("revoked", 401),
        ("expired", 401),
        ("expired_status", 401),
        ("disabled_principal", 401),
        ("deleted_principal", 401),
        ("inactive_workspace", 401),
        ("deleted_workspace", 401),
        ("removed_membership", 403),
    ],
)
def test_identity_and_agent_list_reject_unavailable_credentials(
    postgres_session_factory: sessionmaker[Session], state: str, expected_status: int
) -> None:
    credential = _issue_key(postgres_session_factory)
    key = credential.api_key
    with TestClient(
        create_app(session_factory=postgres_session_factory, api_key_auth_enabled=True)
    ) as client:
        assert client.get("/v1/auth/me", headers=_headers(credential)).status_code == 200
        with postgres_session_factory() as session:
            if state == "revoked":
                assert ApiKeyRepository(session).revoke(key.id)
            elif state in {"expired", "expired_status"}:
                record = session.get(ApiKeyRecord, str(key.id))
                assert record is not None
                if state == "expired":
                    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
                else:
                    record.status = ApiKeyStatus.EXPIRED.value
            elif state == "disabled_principal":
                PrincipalRepository(session).set_disabled(
                    principal_id=key.principal_id, disabled=True
                )
            elif state == "deleted_principal":
                session.execute(
                    delete(PrincipalRecord).where(PrincipalRecord.id == str(key.principal_id))
                )
            elif state == "inactive_workspace":
                session.execute(
                    update(WorkspaceRecord)
                    .where(WorkspaceRecord.id == str(key.workspace_id))
                    .values(status=WorkspaceStatus.DISABLED.value)
                )
            elif state == "deleted_workspace":
                session.execute(
                    delete(WorkspaceRecord).where(WorkspaceRecord.id == str(key.workspace_id))
                )
            elif state == "removed_membership":
                session.execute(
                    delete(WorkspaceMembershipRecord).where(
                        WorkspaceMembershipRecord.principal_id == str(key.principal_id),
                        WorkspaceMembershipRecord.workspace_id == str(key.workspace_id),
                    )
                )
            session.commit()
        headers = _headers(credential)
        if state == "missing":
            headers = {}
        elif state == "invalid":
            headers = {"Authorization": "Bearer invalid-web-test-key"}
        for path in ("/v1/auth/me", "/v1/agents"):
            response = client.get(path, headers=headers)
            assert response.status_code == expected_status
            assert set(response.json()) == {"detail"}
            if path == "/v1/auth/me":
                assert response.headers["cache-control"] == "no-store"
            for secret in (credential.plaintext_key, key.key_hash, key.key_prefix):
                assert secret not in response.text
                assert secret not in str(response.headers)


def test_identity_reflects_role_and_display_name_changes(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    credential = _issue_key(postgres_session_factory)
    key = credential.api_key
    with TestClient(
        create_app(session_factory=postgres_session_factory, api_key_auth_enabled=True),
        headers=_headers(credential),
    ) as client:
        assert client.get("/v1/auth/me").json()["role"] == "operator"
        with postgres_session_factory() as session:
            WorkspaceMembershipRepository(session).assign(
                principal_id=key.principal_id,
                workspace_id=key.workspace_id,
                role=WorkspaceRole.VIEWER,
            )
            session.execute(
                update(PrincipalRecord)
                .where(PrincipalRecord.id == str(key.principal_id))
                .values(display_name="Renamed User")
            )
            session.commit()
        response = client.get("/v1/auth/me")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["role"] == "viewer"
        assert response.json()["display_name"] == "Renamed User"
        assert "agent:write" not in response.json()["permissions"]
        assert client.post("/v1/agents", json={"name": "Denied"}).status_code == 403


def test_agent_list_is_scoped_bounded_and_stably_ordered(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    a = _issue_key(postgres_session_factory, WorkspaceRole.VIEWER)
    b = _issue_key(postgres_session_factory)
    with postgres_session_factory() as session:
        repository = AgentRepository(session)
        own = [
            repository.create(name=f"Own {i}", workspace_id=a.api_key.workspace_id)
            for i in range(101)
        ]
        foreign = repository.create(name="Foreign", workspace_id=b.api_key.workspace_id)
        repository.create(name="Unscoped")
        # Equal timestamps exercise the ID tie-breaker without relying on clock resolution.
        session.execute(
            update(AgentRecord)
            .where(AgentRecord.workspace_id == str(a.api_key.workspace_id))
            .values(created_at=datetime(2020, 1, 1, tzinfo=UTC))
        )
        session.commit()
    expected = sorted((str(agent.id) for agent in own), reverse=True)
    with TestClient(
        create_app(session_factory=postgres_session_factory, api_key_auth_enabled=True)
    ) as client:
        response = client.get("/v1/agents", headers=_headers(a))
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == expected[:100]
        assert {item["workspace_id"] for item in response.json()} == {str(a.api_key.workspace_id)}
        for limit in (1, 2, 1000):
            response = client.get("/v1/agents", params={"limit": limit}, headers=_headers(a))
            assert response.status_code == 200
            assert [item["id"] for item in response.json()] == expected[:limit]
        for invalid_limit in (0, -1, 1001, "invalid"):
            response = client.get(
                "/v1/agents", params={"limit": invalid_limit}, headers=_headers(a)
            )
            assert response.status_code == 422
        # Caller-supplied workspace selectors never override the authenticated scope.
        forged = client.get(
            "/v1/agents",
            params={"workspace_id": str(b.api_key.workspace_id)},
            headers={**_headers(a), "X-Workspace-Id": str(b.api_key.workspace_id)},
        )
        assert [item["id"] for item in forged.json()] == expected[:100]
        response = client.get("/v1/agents", headers=_headers(b))
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [str(foreign.id)]
        empty = _issue_key(postgres_session_factory, WorkspaceRole.VIEWER)
        response = client.get("/v1/agents", headers=_headers(empty))
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.parametrize("send_key", [False, True])
def test_anonymous_identity_matches_auth_disabled_behavior(
    postgres_session_factory: sessionmaker[Session], send_key: bool
) -> None:
    credential = _issue_key(postgres_session_factory)
    with postgres_session_factory() as session:
        scoped = AgentRepository(session).create(
            name="Scoped", workspace_id=credential.api_key.workspace_id
        )
    with TestClient(
        create_app(session_factory=postgres_session_factory, api_key_auth_enabled=False),
        headers=_headers(credential) if send_key else {},
    ) as client:
        response = client.get("/v1/auth/me")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "authenticated": False,
            "principal_id": None,
            "display_name": None,
            "workspace_id": None,
            "role": None,
            "permissions": sorted(permission.value for permission in Permission),
        }
        created = client.post("/v1/agents", json={"name": "Anonymous"})
        assert created.status_code == 201
        assert created.json()["workspace_id"] is None
        response = client.get("/v1/agents")
        assert response.status_code == 200
        assert {item["id"] for item in response.json()} == {str(scoped.id), created.json()["id"]}
        assert client.get("/v1/approvals").status_code == 200
