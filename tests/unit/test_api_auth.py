from uuid import UUID

from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from kernel_identity import PrincipalType, WorkspaceRole
from kernel_storage import (
    AgentRepository,
    ApiKeyRepository,
    PrincipalRepository,
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)
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
