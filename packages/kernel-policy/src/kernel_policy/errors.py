"""Typed policy errors."""

from __future__ import annotations

from kernel_policy.models import PolicyDecision


class PolicyError(RuntimeError):
    """Base error for policy failures."""

    def __init__(self, message: str, *, error_type: str) -> None:
        self.error_type = error_type
        super().__init__(message)


class ToolDeniedError(PolicyError):
    """Raised when policy denies tool execution."""

    def __init__(self, decision: PolicyDecision) -> None:
        self.decision = decision
        super().__init__(
            f"Tool {decision.tool_name!r} was denied by policy: {decision.reason}",
            error_type="tool_denied",
        )


class ToolApprovalRequiredError(PolicyError):
    """Raised when policy requires approval before execution."""

    def __init__(self, decision: PolicyDecision) -> None:
        self.decision = decision
        super().__init__(
            f"Tool {decision.tool_name!r} requires approval: {decision.reason}",
            error_type="tool_approval_required",
        )
