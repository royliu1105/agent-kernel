from datetime import UTC, datetime, timedelta

from kernel_identity import (
    ApiKeyStatus,
    AuthorizationRequest,
    Permission,
    PrincipalType,
    WorkspaceAuthorizer,
    WorkspaceRole,
    verify_api_key,
)
from kernel_storage import (
    ApiKeyRepository,
    PrincipalRepository,
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)
from sqlalchemy.orm import Session, sessionmaker


def test_identity_repositories_create_workspace_principal_and_membership(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        principal = PrincipalRepository(session).create(
            type=PrincipalType.USER,
            display_name="Platform Owner",
        )
        workspace = WorkspaceRepository(session).create(
            name="Platform",
            slug="platform",
        )
        membership = WorkspaceMembershipRepository(session).assign(
            principal_id=principal.id,
            workspace_id=workspace.id,
            role=WorkspaceRole.OWNER,
        )

        loaded_principal = PrincipalRepository(session).get(principal.id)
        loaded_workspace = WorkspaceRepository(session).get_by_slug("platform")
        loaded_membership = WorkspaceMembershipRepository(session).get(
            principal_id=principal.id,
            workspace_id=workspace.id,
        )

    assert loaded_principal is not None
    assert loaded_principal.id == principal.id
    assert loaded_principal.type is PrincipalType.USER
    assert loaded_principal.display_name == "Platform Owner"
    assert loaded_principal.disabled is False
    assert loaded_workspace is not None
    assert loaded_workspace.id == workspace.id
    assert loaded_workspace.slug == "platform"
    assert membership is not None
    assert loaded_membership is not None
    assert loaded_membership.principal_id == membership.principal_id
    assert loaded_membership.workspace_id == membership.workspace_id
    assert loaded_membership.role is WorkspaceRole.OWNER


def test_membership_assignment_requires_existing_principal_and_workspace(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        principal = PrincipalRepository(session).create(
            type=PrincipalType.USER,
            display_name="No Workspace",
        )
        workspace = WorkspaceRepository(session).create(name="Ops", slug="ops")

        missing_workspace = WorkspaceMembershipRepository(session).assign(
            principal_id=principal.id,
            workspace_id=principal.id,
            role=WorkspaceRole.VIEWER,
        )
        missing_principal = WorkspaceMembershipRepository(session).assign(
            principal_id=workspace.id,
            workspace_id=workspace.id,
            role=WorkspaceRole.VIEWER,
        )

    assert missing_workspace is None
    assert missing_principal is None


def test_membership_assignment_updates_existing_role(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        principal = PrincipalRepository(session).create(
            type=PrincipalType.USER,
            display_name="Operator",
        )
        workspace = WorkspaceRepository(session).create(name="Ops", slug="ops")

        WorkspaceMembershipRepository(session).assign(
            principal_id=principal.id,
            workspace_id=workspace.id,
            role=WorkspaceRole.VIEWER,
        )
        updated = WorkspaceMembershipRepository(session).assign(
            principal_id=principal.id,
            workspace_id=workspace.id,
            role=WorkspaceRole.OPERATOR,
        )
        memberships = WorkspaceMembershipRepository(session).list_for_principal(principal.id)

    assert updated is not None
    assert updated.role is WorkspaceRole.OPERATOR
    assert [membership.role for membership in memberships] == [WorkspaceRole.OPERATOR]


def test_persisted_memberships_can_feed_workspace_authorizer(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        principal = PrincipalRepository(session).create(
            type=PrincipalType.USER,
            display_name="Viewer",
        )
        workspace = WorkspaceRepository(session).create(name="Read", slug="read")
        WorkspaceMembershipRepository(session).assign(
            principal_id=principal.id,
            workspace_id=workspace.id,
            role=WorkspaceRole.VIEWER,
        )
        memberships = WorkspaceMembershipRepository(session).list_for_principal(principal.id)

    decision = WorkspaceAuthorizer(memberships).authorize(
        AuthorizationRequest(
            principal=principal,
            workspace_id=workspace.id,
            permission=Permission.RUN_READ,
        )
    )

    assert decision.allowed is True


def test_api_key_repository_issues_hashed_key_and_authenticates_once_presented(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    plaintext_key = "ak_test_secret"
    with sqlite_session_factory() as session:
        principal = PrincipalRepository(session).create(
            type=PrincipalType.USER,
            display_name="API User",
        )
        workspace = WorkspaceRepository(session).create(name="API", slug="api")
        WorkspaceMembershipRepository(session).assign(
            principal_id=principal.id,
            workspace_id=workspace.id,
            role=WorkspaceRole.OPERATOR,
        )

        credential = ApiKeyRepository(session).issue(
            workspace_id=workspace.id,
            principal_id=principal.id,
            name="Local key",
            plaintext_key=plaintext_key,
        )
        assert credential is not None
        authenticated = ApiKeyRepository(session).authenticate(plaintext_key)

    assert credential.plaintext_key == plaintext_key
    assert credential.api_key.key_prefix == "ak_test_secr"
    assert verify_api_key(plaintext_key, credential.api_key.key_hash)
    assert plaintext_key != credential.api_key.key_hash
    assert authenticated is not None
    assert authenticated.id == credential.api_key.id
    assert authenticated.last_used_at is not None


def test_api_key_issue_requires_workspace_membership(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        principal = PrincipalRepository(session).create(
            type=PrincipalType.USER,
            display_name="No Membership",
        )
        workspace = WorkspaceRepository(session).create(name="Nope", slug="nope")

        credential = ApiKeyRepository(session).issue(
            workspace_id=workspace.id,
            principal_id=principal.id,
            name="Blocked",
            plaintext_key="ak_blocked",
        )

    assert credential is None


def test_api_key_repository_rejects_revoked_and_expired_keys(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        principal = PrincipalRepository(session).create(
            type=PrincipalType.SERVICE,
            display_name="Service",
        )
        workspace = WorkspaceRepository(session).create(name="Service", slug="service")
        WorkspaceMembershipRepository(session).assign(
            principal_id=principal.id,
            workspace_id=workspace.id,
            role=WorkspaceRole.OPERATOR,
        )

        active = ApiKeyRepository(session).issue(
            workspace_id=workspace.id,
            principal_id=principal.id,
            name="Active",
            plaintext_key="ak_active_secret",
        )
        expired = ApiKeyRepository(session).issue(
            workspace_id=workspace.id,
            principal_id=principal.id,
            name="Expired",
            plaintext_key="ak_expired_secret",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        assert active is not None
        assert expired is not None

        assert ApiKeyRepository(session).revoke(active.api_key.id) is True
        revoked_auth = ApiKeyRepository(session).authenticate("ak_active_secret")
        expired_auth = ApiKeyRepository(session).authenticate("ak_expired_secret")
        expired_record = ApiKeyRepository(session).get(expired.api_key.id)

    assert revoked_auth is None
    assert expired_auth is None
    assert expired_record is not None
    assert expired_record.status is ApiKeyStatus.EXPIRED
