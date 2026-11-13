"""Policy evaluator for tool metadata."""

from __future__ import annotations

from kernel_tools import ToolMetadata
from kernel_tools.external.config import ExternalToolMetadata

from kernel_policy.models import PolicyDecision, PolicyDecisionType, ToolPolicy


class ToolPolicyEvaluator:
    """Evaluate tool metadata against static Day 9 policy rules."""

    def __init__(self, policy: ToolPolicy | None = None) -> None:
        self._policy = policy or ToolPolicy()

    def evaluate(self, metadata: ToolMetadata) -> PolicyDecision:
        tool_decision = self._policy.tool_decisions.get(metadata.name)
        if isinstance(metadata, ExternalToolMetadata) and metadata.policy_decision is not None:
            binding_decision = PolicyDecisionType(metadata.policy_decision)
            # Explicit policies compose conservatively: a central allow must not
            # silently remove the binding's approval or denial requirement.
            rank = {
                PolicyDecisionType.ALLOW: 0,
                PolicyDecisionType.REQUIRE_APPROVAL: 1,
                PolicyDecisionType.DENY: 2,
            }
            decision = max(
                (binding_decision, tool_decision or binding_decision), key=rank.__getitem__
            )
            return PolicyDecision(
                decision=decision,
                reason=f"Explicit external binding policy for {metadata.name!r}.",
                risk_level=metadata.risk_level,
                tool_name=metadata.name,
            )
        if tool_decision is not None:
            return PolicyDecision(
                decision=tool_decision,
                reason=f"Explicit tool policy for {metadata.name!r}.",
                risk_level=metadata.risk_level,
                tool_name=metadata.name,
            )

        risk_decision = self._policy.risk_decisions.get(
            metadata.risk_level,
            PolicyDecisionType.REQUIRE_APPROVAL,
        )
        return PolicyDecision(
            decision=risk_decision,
            reason=f"Default risk policy for {metadata.risk_level.value!r}.",
            risk_level=metadata.risk_level,
            tool_name=metadata.name,
        )
