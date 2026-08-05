from uuid import uuid4

from kernel_identity import (
    AuthorizationRequest,
    Permission,
    Principal,
    PrincipalType,
    Workspace,
    WorkspaceAuthorizer,
    WorkspaceMembership,
    WorkspaceRole,
)


def test_owner_can_admin_workspace() -> None:
    workspace = Workspace(name="Platform", slug="platform")
    principal = Principal(type=PrincipalType.USER, display_name="Owner")
    authorizer = WorkspaceAuthorizer(
        [
            WorkspaceMembership(
                principal_id=principal.id,
                workspace_id=workspace.id,
                role=WorkspaceRole.OWNER,
            )
        ]
    )

    decision = authorizer.authorize(
        AuthorizationRequest(
            principal=principal,
            workspace_id=workspace.id,
            permission=Permission.WORKSPACE_ADMIN,
        )
    )

    assert decision.allowed is True
    assert decision.role is WorkspaceRole.OWNER


def test_operator_can_review_approvals_but_cannot_admin_workspace() -> None:
    workspace = Workspace(name="Ops", slug="ops")
    principal = Principal(type=PrincipalType.USER, display_name="Operator")
    authorizer = WorkspaceAuthorizer(
        [
            WorkspaceMembership(
                principal_id=principal.id,
                workspace_id=workspace.id,
                role=WorkspaceRole.OPERATOR,
            )
        ]
    )

    approval_decision = authorizer.authorize(
        AuthorizationRequest(
            principal=principal,
            workspace_id=workspace.id,
            permission=Permission.APPROVAL_REVIEW,
        )
    )
    admin_decision = authorizer.authorize(
        AuthorizationRequest(
            principal=principal,
            workspace_id=workspace.id,
            permission=Permission.WORKSPACE_ADMIN,
        )
    )

    assert approval_decision.allowed is True
    assert admin_decision.allowed is False
    assert "does not grant" in admin_decision.reason


def test_viewer_is_read_only() -> None:
    workspace = Workspace(name="Read", slug="read")
    principal = Principal(type=PrincipalType.USER, display_name="Viewer")
    authorizer = WorkspaceAuthorizer(
        [
            WorkspaceMembership(
                principal_id=principal.id,
                workspace_id=workspace.id,
                role=WorkspaceRole.VIEWER,
            )
        ]
    )

    read_decision = authorizer.authorize(
        AuthorizationRequest(
            principal=principal,
            workspace_id=workspace.id,
            permission=Permission.RUN_READ,
        )
    )
    write_decision = authorizer.authorize(
        AuthorizationRequest(
            principal=principal,
            workspace_id=workspace.id,
            permission=Permission.RUN_WRITE,
        )
    )

    assert read_decision.allowed is True
    assert write_decision.allowed is False


def test_membership_is_workspace_scoped() -> None:
    workspace = Workspace(name="A", slug="a")
    other_workspace_id = uuid4()
    principal = Principal(type=PrincipalType.SERVICE, display_name="Worker")
    authorizer = WorkspaceAuthorizer(
        [
            WorkspaceMembership(
                principal_id=principal.id,
                workspace_id=workspace.id,
                role=WorkspaceRole.OPERATOR,
            )
        ]
    )

    decision = authorizer.authorize(
        AuthorizationRequest(
            principal=principal,
            workspace_id=other_workspace_id,
            permission=Permission.RUN_WRITE,
        )
    )

    assert decision.allowed is False
    assert decision.role is None
    assert decision.reason == "Principal is not a member of the workspace."


def test_disabled_principal_is_denied_even_with_membership() -> None:
    workspace = Workspace(name="Disabled", slug="disabled")
    principal = Principal(type=PrincipalType.USER, display_name="Disabled", disabled=True)
    authorizer = WorkspaceAuthorizer(
        [
            WorkspaceMembership(
                principal_id=principal.id,
                workspace_id=workspace.id,
                role=WorkspaceRole.OWNER,
            )
        ]
    )

    decision = authorizer.authorize(
        AuthorizationRequest(
            principal=principal,
            workspace_id=workspace.id,
            permission=Permission.WORKSPACE_ADMIN,
        )
    )

    assert decision.allowed is False
    assert decision.role is None
    assert decision.reason == "Principal is disabled."
