"""Identity, workspace, and RBAC primitives for Agent Kernel."""

from kernel_identity.authorizer import ROLE_PERMISSIONS, WorkspaceAuthorizer
from kernel_identity.keys import api_key_prefix, generate_api_key, hash_api_key, verify_api_key
from kernel_identity.models import (
    ApiKey,
    ApiKeyCredential,
    ApiKeyStatus,
    AuthorizationDecision,
    AuthorizationRequest,
    Permission,
    Principal,
    PrincipalType,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
    WorkspaceStatus,
)

__all__ = [
    "ROLE_PERMISSIONS",
    "ApiKey",
    "ApiKeyCredential",
    "ApiKeyStatus",
    "AuthorizationDecision",
    "AuthorizationRequest",
    "Permission",
    "Principal",
    "PrincipalType",
    "Workspace",
    "WorkspaceAuthorizer",
    "WorkspaceMembership",
    "WorkspaceRole",
    "WorkspaceStatus",
    "api_key_prefix",
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
]
