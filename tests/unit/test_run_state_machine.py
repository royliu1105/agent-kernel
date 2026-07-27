import pytest
from kernel_core import Agent, Run, RunEventType, RunStatus
from kernel_runtime import InvalidRunTransitionError, RunStateMachine


def test_run_state_machine_allows_queue_transition() -> None:
    agent = Agent(name="research-agent")
    run = Run(agent_id=agent.id)

    transition = RunStateMachine().queue(run)

    assert transition.from_status is RunStatus.CREATED
    assert transition.to_status is RunStatus.QUEUED
    assert transition.event_type is RunEventType.RUN_QUEUED


def test_run_state_machine_rejects_terminal_transition() -> None:
    agent = Agent(name="research-agent")
    run = Run(agent_id=agent.id, status=RunStatus.SUCCEEDED)

    with pytest.raises(InvalidRunTransitionError) as error:
        RunStateMachine().queue(run)

    assert error.value.from_status is RunStatus.SUCCEEDED
    assert error.value.to_status is RunStatus.QUEUED
