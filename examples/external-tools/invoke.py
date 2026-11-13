"""Exercise registration and policy; production approvals belong to the runtime."""

import argparse
import asyncio
import json
from pathlib import Path

from kernel_policy import (
    PolicyAwareToolExecutor,
    PolicyDecisionType,
    ToolApprovalRequiredError,
    ToolPolicy,
    ToolPolicyEvaluator,
)
from kernel_tools import ToolRegistry, ToolRequest
from kernel_tools.external import load_external_tools, read_external_tools_config


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("tool")
    parser.add_argument("arguments", help="JSON object")
    parser.add_argument("--allow-this-call", action="store_true")
    args = parser.parse_args()
    registry = ToolRegistry()
    config = read_external_tools_config(args.config)
    policy = (
        ToolPolicy(tool_decisions={args.tool: PolicyDecisionType.ALLOW})
        if args.allow_this_call
        else ToolPolicy()
    )
    async with load_external_tools(registry, config):
        executor = PolicyAwareToolExecutor(
            registry=registry, evaluator=ToolPolicyEvaluator(policy=policy)
        )
        try:
            result = await executor.execute(
                ToolRequest(
                    tool_name=args.tool,
                    arguments=json.loads(args.arguments),
                )
            )
        except ToolApprovalRequiredError:
            print("Approval required. Review the operation before passing --allow-this-call.")
        else:
            print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
