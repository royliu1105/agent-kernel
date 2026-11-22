"""Direct (non-Run) policy-aware tool execution."""

from __future__ import annotations

from kernel_tools import ToolExecutor, ToolMetadata, ToolRegistry, ToolRequest, ToolResult

from kernel_policy.errors import ToolApprovalRequiredError, ToolDeniedError
from kernel_policy.evaluator import ToolPolicyEvaluator
from kernel_policy.models import PolicyDecision, PolicyDecisionType


def enforce_direct_execution(decision: PolicyDecision) -> None:
    """Apply policy for callers outside the Run lifecycle.

    Only ``ALLOW`` may proceed. ``DENY`` and ``REQUIRE_APPROVAL`` raise. Run
    execution must not use this helper: it persists approvals and pauses the
    Run instead of raising ``ToolApprovalRequiredError``.
    """

    if decision.decision is PolicyDecisionType.DENY:
        raise ToolDeniedError(decision)
    if decision.decision is PolicyDecisionType.REQUIRE_APPROVAL:
        raise ToolApprovalRequiredError(decision)


class PolicyAwareToolExecutor:
    """Evaluate policy, then execute — for scripts, examples, and unit tests.

    Production Agent Runs do **not** go through this class. They use
    ``RunExecutionService`` in ``kernel-runtime``, which calls the same
    ``ToolPolicyEvaluator`` and then persists tool/approval/Run state.

    Use this helper only when there is no Run to pause or resume.
    """

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

    def decide(self, metadata: ToolMetadata) -> PolicyDecision:
        """Return the shared policy decision for tool metadata."""

        return self._evaluator.evaluate(metadata)

    async def execute(self, request: ToolRequest) -> ToolResult:
        tool = self._registry.get(request.tool_name)
        enforce_direct_execution(self.decide(tool.metadata))
        return await self._executor.execute(request)
