"""Workspace-scoped RBAC authorizer."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from kernel_identity.models import (
    AuthorizationDecision,
    AuthorizationRequest,
    Permission,
    WorkspaceMembership,
    WorkspaceRole,
)

ROLE_PERMISSIONS: Mapping[WorkspaceRole, frozenset[Permission]] = {
    WorkspaceRole.OWNER: frozenset(Permission),
    WorkspaceRole.ADMIN: frozenset(Permission),
    WorkspaceRole.OPERATOR: frozenset(
        {
            Permission.WORKSPACE_READ,
            Permission.AGENT_READ,
            Permission.AGENT_WRITE,
            Permission.RUN_READ,
            Permission.RUN_WRITE,
            Permission.APPROVAL_REVIEW,
            Permission.TOOL_EXECUTE,
            Permission.KNOWLEDGE_READ,
            Permission.KNOWLEDGE_WRITE,
            Permission.MEMORY_READ,
            Permission.MEMORY_WRITE,
            Permission.EVAL_READ,
            Permission.EVAL_WRITE,
        }
    ),
    WorkspaceRole.VIEWER: frozenset(
        {
            Permission.WORKSPACE_READ,
            Permission.AGENT_READ,
            Permission.RUN_READ,
            Permission.KNOWLEDGE_READ,
            Permission.MEMORY_READ,
            Permission.EVAL_READ,
        }
    ),
}


class WorkspaceAuthorizer:
    """Authorize principals against workspace memberships and built-in roles."""

    def __init__(
        self,
        memberships: Iterable[WorkspaceMembership],
        role_permissions: Mapping[WorkspaceRole, frozenset[Permission]] | None = None,
    ) -> None:
        self._memberships = {
            (membership.principal_id, membership.workspace_id): membership
            for membership in memberships
        }
        self._role_permissions = role_permissions or ROLE_PERMISSIONS

    def authorize(self, request: AuthorizationRequest) -> AuthorizationDecision:
        principal = request.principal
        if principal.disabled:
            return AuthorizationDecision(
                allowed=False,
                reason="Principal is disabled.",
                principal_id=principal.id,
                workspace_id=request.workspace_id,
                permission=request.permission,
            )

        membership = self._memberships.get((principal.id, request.workspace_id))
        if membership is None:
            return AuthorizationDecision(
                allowed=False,
                reason="Principal is not a member of the workspace.",
                principal_id=principal.id,
                workspace_id=request.workspace_id,
                permission=request.permission,
            )

        permissions = self._role_permissions.get(membership.role, frozenset())
        if request.permission not in permissions:
            return AuthorizationDecision(
                allowed=False,
                reason=(
                    f"Workspace role {membership.role.value!r} does not grant "
                    f"{request.permission.value!r}."
                ),
                principal_id=principal.id,
                workspace_id=request.workspace_id,
                permission=request.permission,
                role=membership.role,
            )

        return AuthorizationDecision(
            allowed=True,
            reason=(
                f"Workspace role {membership.role.value!r} grants "
                f"{request.permission.value!r}."
            ),
            principal_id=principal.id,
            workspace_id=request.workspace_id,
            permission=request.permission,
            role=membership.role,
        )
