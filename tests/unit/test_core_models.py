from kernel_core import (
    Agent,
    Approval,
    MemoryItem,
    MemoryType,
    Run,
    RunEvent,
    RunEventType,
    RunStatus,
    RunStep,
    RunStepType,
    ToolCall,
)


def test_agent_run_models_have_expected_defaults() -> None:
    agent = Agent(name="research-agent")
    run = Run(agent_id=agent.id, input={"task": "summarize"})
    step = RunStep(run_id=run.id, index=0, type=RunStepType.MODEL_CALL)
    event = RunEvent(run_id=run.id, sequence=1, type=RunEventType.RUN_CREATED)
    tool_call = ToolCall(run_id=run.id, step_id=step.id, tool_name="echo")
    approval = Approval(run_id=run.id, tool_call_id=tool_call.id, reason="Risky action")

    assert run.status is RunStatus.CREATED
    assert event.sequence == 1
    assert step.run_id == run.id
    assert tool_call.requires_approval is False
    assert approval.tool_call_id == tool_call.id


def test_memory_item_model_has_expected_defaults() -> None:
    memory = MemoryItem(
        type=MemoryType.USER_PREFERENCE,
        scope="user:roy",
        content={"language": "zh"},
    )

    assert memory.type is MemoryType.USER_PREFERENCE
    assert memory.scope == "user:roy"
    assert memory.content == {"language": "zh"}
    assert memory.source_run_id is None
    assert memory.confidence == 1.0
    assert memory.metadata == {}
