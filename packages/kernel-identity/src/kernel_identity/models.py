"""Identity and authorization domain models."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class PrincipalType(StrEnum):
    """Supported authenticated actor types."""

    USER = "user"
    SERVICE = "service"


class WorkspaceStatus(StrEnum):
    """Lifecycle states for a workspace."""

    ACTIVE = "active"
    DISABLED = "disabled"


class WorkspaceRole(StrEnum):
    """Built-in workspace roles for the Beta RBAC baseline."""

    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(StrEnum):
    """Fine-grained permissions checked by API, CLI, worker, and Web surfaces."""

    WORKSPACE_READ = "workspace:read"
    WORKSPACE_ADMIN = "workspace:admin"
    AGENT_READ = "agent:read"
    AGENT_WRITE = "agent:write"
    RUN_READ = "run:read"
    RUN_WRITE = "run:write"
    APPROVAL_REVIEW = "approval:review"
    TOOL_EXECUTE = "tool:execute"
    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_WRITE = "knowledge:write"
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    EVAL_READ = "eval:read"
    EVAL_WRITE = "eval:write"


class IdentityModel(BaseModel):
    """Base class for identity value objects."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Principal(IdentityModel):
    """Authenticated user or service actor."""

    id: UUID = Field(default_factory=uuid4)
    type: PrincipalType
    display_name: str = Field(min_length=1, max_length=255)
    disabled: bool = False


class Workspace(IdentityModel):
    """Workspace boundary for scoped Agent Kernel resources."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE


class WorkspaceMembership(IdentityModel):
    """Role assignment for a principal inside one workspace."""

    principal_id: UUID
    workspace_id: UUID
    role: WorkspaceRole


class AuthorizationRequest(IdentityModel):
    """Permission check input."""

    principal: Principal
    workspace_id: UUID
    permission: Permission


class AuthorizationDecision(IdentityModel):
    """Permission check result."""

    allowed: bool
    reason: str
    principal_id: UUID
    workspace_id: UUID
    permission: Permission
    role: WorkspaceRole | None = None
