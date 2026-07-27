from kernel_core import Agent, Approval, Run, RunStatus, RunStep, RunStepType, ToolCall


def test_agent_run_models_have_expected_defaults() -> None:
    agent = Agent(name="research-agent")
    run = Run(agent_id=agent.id, input={"task": "summarize"})
    step = RunStep(run_id=run.id, index=0, type=RunStepType.MODEL_CALL)
    tool_call = ToolCall(run_id=run.id, step_id=step.id, tool_name="echo")
    approval = Approval(run_id=run.id, tool_call_id=tool_call.id, reason="Risky action")

    assert run.status is RunStatus.CREATED
    assert step.run_id == run.id
    assert tool_call.requires_approval is False
    assert approval.tool_call_id == tool_call.id
