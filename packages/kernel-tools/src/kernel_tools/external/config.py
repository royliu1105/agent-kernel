"""Operator-owned external tool configuration, separate from remote metadata."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal
from uuid import UUID

from kernel_core import RiskLevel
from pydantic import Field, SecretStr, model_validator

from kernel_tools.models import ToolMetadata, ToolModel

ExternalPolicyDecision = Literal["allow", "deny", "require_approval"]


class ExternalToolMetadata(ToolMetadata):
    """Trusted binding policy, never derived from remote metadata."""

    policy_decision: ExternalPolicyDecision | None = None


class ExternalToolContract(ToolModel):
    """Only a trusted operator may choose policy and replay semantics."""

    name: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")
    description: str = Field(default="Operator-configured external operation.", max_length=512)
    risk_level: RiskLevel = RiskLevel.NETWORK
    read_only: bool = False
    idempotent: bool = False
    retry_safe: bool = False
    policy_decision: ExternalPolicyDecision | None = None
    timeout_ms: int = Field(default=10_000, ge=1, le=300_000)

    @model_validator(mode="after")
    def validate_replay(self) -> ExternalToolContract:
        if self.risk_level is RiskLevel.READ_ONLY and not self.read_only:
            raise ValueError("READ_ONLY risk requires an operator-reviewed read-only contract.")
        if self.retry_safe and not (self.read_only and self.idempotent):
            raise ValueError("Automatic retries require a read-only, idempotent contract.")
        return self


class ExternalAccess(ToolModel):
    """Credentials are shared only with explicitly allowed trusted workspaces."""

    workspace_ids: tuple[UUID, ...] = ()
    allow_unscoped: bool = False


class HttpEndpoint(ToolModel):
    """An exact operator-approved endpoint, never obtained from tool arguments."""

    url: str
    headers: dict[str, SecretStr] = Field(default_factory=dict, repr=False)
    allow_private_network: bool = False
    timeout_ms: int = Field(default=10_000, ge=1, le=300_000)
    max_response_bytes: int = Field(default=1_048_576, ge=1, le=16_777_216)


class StdioEndpoint(ToolModel):
    command: str
    args: tuple[str, ...] = ()
    env: dict[str, SecretStr] = Field(default_factory=dict, repr=False)
    cwd: Path | None = None

    @model_validator(mode="after")
    def absolute_command(self) -> StdioEndpoint:
        if not Path(self.command).is_absolute():
            raise ValueError("MCP stdio command must be an operator-approved absolute path.")
        return self


class MCPBinding(ToolModel):
    """Explicit allowlist entry; resource remote_name is its exact URI."""

    kind: Literal["tool", "resource", "prompt"] = "tool"
    remote_name: str = Field(min_length=1, max_length=2_048)
    contract: ExternalToolContract


class MCPServerConfig(ToolModel):
    name: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")
    stdio: StdioEndpoint | None = None
    http: HttpEndpoint | None = None
    bindings: tuple[MCPBinding, ...]
    access: ExternalAccess = Field(default_factory=ExternalAccess)
    discovery_timeout_ms: int = Field(default=15_000, ge=1, le=300_000)
    max_catalog_entries: int = Field(default=100, ge=1, le=1_000)

    @model_validator(mode="after")
    def one_transport(self) -> MCPServerConfig:
        if (self.stdio is None) == (self.http is None):
            raise ValueError("Configure exactly one MCP transport.")
        return self


class OpenAPIBinding(ToolModel):
    operation_id: str
    contract: ExternalToolContract
    idempotency_header: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{1,64}$")

    @model_validator(mode="after")
    def idempotency_contract(self) -> OpenAPIBinding:
        if self.idempotency_header and not self.contract.idempotent:
            raise ValueError("An idempotency header requires an explicit idempotent contract.")
        return self


class OpenAPIConfig(ToolModel):
    name: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")
    document: Path
    endpoint: HttpEndpoint
    bindings: tuple[OpenAPIBinding, ...]
    access: ExternalAccess = Field(default_factory=ExternalAccess)


class ExternalToolsConfig(ToolModel):
    mcp: tuple[MCPServerConfig, ...] = ()
    openapi: tuple[OpenAPIConfig, ...] = ()


def read_external_tools_config(path: Path) -> ExternalToolsConfig:
    """Load a local, operator-owned JSON file; never call this on uploaded content."""
    with path.open("rb") as stream:
        data = stream.read(1_048_577)
    if len(data) > 1_048_576:
        raise ValueError("External tool configuration exceeds 1 MiB.")
    return ExternalToolsConfig.model_validate_json(data)


def external_tools_config_from_env(
    environ: Mapping[str, str] | None = None,
) -> ExternalToolsConfig:
    """Absent configuration is a no-op; malformed configuration fails startup."""
    environment = os.environ if environ is None else environ
    path = environment.get("AGENT_KERNEL_EXTERNAL_TOOLS_CONFIG", "").strip()
    return read_external_tools_config(Path(path)) if path else ExternalToolsConfig()
