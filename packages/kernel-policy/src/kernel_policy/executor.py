"""Policy-aware tool execution."""

from __future__ import annotations

from kernel_tools import ToolExecutor, ToolRegistry, ToolRequest, ToolResult

from kernel_policy.errors import ToolApprovalRequiredError, ToolDeniedError
from kernel_policy.evaluator import ToolPolicyEvaluator
from kernel_policy.models import PolicyDecisionType


class PolicyAwareToolExecutor:
    """Evaluate policy before delegating allowed requests to the tool executor."""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        evaluator: ToolPolicyEvaluator | None = None,
        executor: ToolExecutor | None = None,
    ) -> None:
        self._registry = registry
        self._evaluator = evaluator or ToolPolicyEvaluator()
        self._executor = executor or ToolExecutor(registry=registry)

    async def execute(self, request: ToolRequest) -> ToolResult:
        tool = self._registry.get(request.tool_name)
        decision = self._evaluator.evaluate(tool.metadata)
        if decision.decision is PolicyDecisionType.DENY:
            raise ToolDeniedError(decision)
        if decision.decision is PolicyDecisionType.REQUIRE_APPROVAL:
            raise ToolApprovalRequiredError(decision)
        return await self._executor.execute(request)
