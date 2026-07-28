"""Policy models for tool execution decisions."""

from __future__ import annotations

from enum import StrEnum

from kernel_core import RiskLevel
from pydantic import BaseModel, ConfigDict, Field


class PolicyDecisionType(StrEnum):
    """Allowed policy decisions for a tool request."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PolicyModel(BaseModel):
    """Base model for policy package value objects."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PolicyDecision(PolicyModel):
    """Decision returned by policy evaluation."""

    decision: PolicyDecisionType
    reason: str
    risk_level: RiskLevel
    tool_name: str


class ToolPolicy(PolicyModel):
    """Static policy configuration for Day 9 tool decisions."""

    tool_decisions: dict[str, PolicyDecisionType] = Field(default_factory=dict)
    risk_decisions: dict[RiskLevel, PolicyDecisionType] = Field(
        default_factory=lambda: {
            RiskLevel.READ_ONLY: PolicyDecisionType.ALLOW,
            RiskLevel.EXTERNAL_WRITE: PolicyDecisionType.REQUIRE_APPROVAL,
            RiskLevel.FILESYSTEM_WRITE: PolicyDecisionType.REQUIRE_APPROVAL,
            RiskLevel.NETWORK: PolicyDecisionType.REQUIRE_APPROVAL,
            RiskLevel.DANGEROUS: PolicyDecisionType.DENY,
        }
    )
