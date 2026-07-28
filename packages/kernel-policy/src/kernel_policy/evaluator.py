"""Policy evaluator for tool metadata."""

from __future__ import annotations

from kernel_tools import ToolMetadata

from kernel_policy.models import PolicyDecision, PolicyDecisionType, ToolPolicy


class ToolPolicyEvaluator:
    """Evaluate tool metadata against static Day 9 policy rules."""

    def __init__(self, policy: ToolPolicy | None = None) -> None:
        self._policy = policy or ToolPolicy()

    def evaluate(self, metadata: ToolMetadata) -> PolicyDecision:
        tool_decision = self._policy.tool_decisions.get(metadata.name)
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
