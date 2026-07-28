from typing import Any

import pytest
from kernel_core import RiskLevel
from kernel_policy import (
    PolicyAwareToolExecutor,
    PolicyDecisionType,
    ToolApprovalRequiredError,
    ToolDeniedError,
    ToolPolicy,
    ToolPolicyEvaluator,
)
from kernel_tools import EchoTool, ToolMetadata, ToolRegistry, ToolRequest


def test_default_policy_allows_read_only_tool() -> None:
    decision = ToolPolicyEvaluator().evaluate(EchoTool().metadata)

    assert decision.decision is PolicyDecisionType.ALLOW
    assert decision.risk_level is RiskLevel.READ_ONLY
    assert decision.tool_name == "echo"


def test_default_policy_requires_approval_for_write_and_network_risks() -> None:
    evaluator = ToolPolicyEvaluator()

    for risk_level in (
        RiskLevel.EXTERNAL_WRITE,
        RiskLevel.FILESYSTEM_WRITE,
        RiskLevel.NETWORK,
    ):
        decision = evaluator.evaluate(
            ToolMetadata(
                name=f"{risk_level.value}-tool",
                description="Risky tool.",
                risk_level=risk_level,
            )
        )

        assert decision.decision is PolicyDecisionType.REQUIRE_APPROVAL


def test_default_policy_denies_dangerous_tools() -> None:
    decision = ToolPolicyEvaluator().evaluate(
        ToolMetadata(
            name="dangerous-tool",
            description="Dangerous tool.",
            risk_level=RiskLevel.DANGEROUS,
        )
    )

    assert decision.decision is PolicyDecisionType.DENY


def test_tool_name_policy_overrides_risk_default() -> None:
    evaluator = ToolPolicyEvaluator(
        ToolPolicy(tool_decisions={"dangerous-tool": PolicyDecisionType.REQUIRE_APPROVAL})
    )

    decision = evaluator.evaluate(
        ToolMetadata(
            name="dangerous-tool",
            description="Dangerous but explicitly reviewable.",
            risk_level=RiskLevel.DANGEROUS,
        )
    )

    assert decision.decision is PolicyDecisionType.REQUIRE_APPROVAL
    assert "Explicit tool policy" in decision.reason


@pytest.mark.asyncio
async def test_policy_aware_executor_executes_allowed_safe_tool() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())
    executor = PolicyAwareToolExecutor(registry=registry)

    result = await executor.execute(
        ToolRequest(tool_name="echo", arguments={"message": "hello policy"})
    )

    assert result.output == {"message": "hello policy"}


@pytest.mark.asyncio
async def test_policy_aware_executor_does_not_execute_denied_tool() -> None:
    tool = CountingRiskyTool(name="dangerous-tool", risk_level=RiskLevel.DANGEROUS)
    registry = ToolRegistry()
    registry.register(tool)
    executor = PolicyAwareToolExecutor(registry=registry)

    with pytest.raises(ToolDeniedError) as error_info:
        await executor.execute(ToolRequest(tool_name="dangerous-tool", arguments={}))

    assert error_info.value.error_type == "tool_denied"
    assert error_info.value.decision.decision is PolicyDecisionType.DENY
    assert tool.execution_count == 0


@pytest.mark.asyncio
async def test_policy_aware_executor_does_not_execute_approval_required_tool() -> None:
    tool = CountingRiskyTool(name="network-tool", risk_level=RiskLevel.NETWORK)
    registry = ToolRegistry()
    registry.register(tool)
    executor = PolicyAwareToolExecutor(registry=registry)

    with pytest.raises(ToolApprovalRequiredError) as error_info:
        await executor.execute(ToolRequest(tool_name="network-tool", arguments={}))

    assert error_info.value.error_type == "tool_approval_required"
    assert error_info.value.decision.decision is PolicyDecisionType.REQUIRE_APPROVAL
    assert tool.execution_count == 0


@pytest.mark.asyncio
async def test_policy_aware_executor_respects_explicit_allow_override() -> None:
    tool = CountingRiskyTool(name="reviewed-network-tool", risk_level=RiskLevel.NETWORK)
    registry = ToolRegistry()
    registry.register(tool)
    executor = PolicyAwareToolExecutor(
        registry=registry,
        evaluator=ToolPolicyEvaluator(
            ToolPolicy(tool_decisions={"reviewed-network-tool": PolicyDecisionType.ALLOW})
        ),
    )

    result = await executor.execute(ToolRequest(tool_name="reviewed-network-tool", arguments={}))

    assert result.output == {"executed": True}
    assert tool.execution_count == 1


class CountingRiskyTool:
    def __init__(self, *, name: str, risk_level: RiskLevel) -> None:
        self._name = name
        self._risk_level = risk_level
        self.execution_count = 0

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self._name,
            description="Count whether policy allowed execution.",
            risk_level=self._risk_level,
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self.execution_count += 1
        return {"executed": True}
