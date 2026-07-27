"""Run lifecycle state machine."""

from __future__ import annotations

from dataclasses import dataclass

from kernel_core import Run, RunEventType, RunStatus


class InvalidRunTransitionError(ValueError):
    """Raised when a run is asked to move through an illegal transition."""

    def __init__(self, *, from_status: RunStatus, to_status: RunStatus) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Cannot transition run from {from_status.value} to {to_status.value}.")


@dataclass(frozen=True)
class RunTransition:
    """A validated run status transition and the timeline event it should emit."""

    from_status: RunStatus
    to_status: RunStatus
    event_type: RunEventType


class RunStateMachine:
    """Validate run status transitions before persistence."""

    _allowed_transitions: dict[RunStatus, frozenset[RunStatus]] = {
        RunStatus.CREATED: frozenset({RunStatus.QUEUED, RunStatus.CANCELED}),
        RunStatus.QUEUED: frozenset({RunStatus.RUNNING, RunStatus.CANCELED}),
        RunStatus.RUNNING: frozenset(
            {
                RunStatus.WAITING_APPROVAL,
                RunStatus.SUCCEEDED,
                RunStatus.FAILED,
                RunStatus.CANCELED,
            }
        ),
        RunStatus.WAITING_APPROVAL: frozenset({RunStatus.RESUMING, RunStatus.CANCELED}),
        RunStatus.RESUMING: frozenset({RunStatus.RUNNING, RunStatus.CANCELED}),
        RunStatus.SUCCEEDED: frozenset(),
        RunStatus.FAILED: frozenset(),
        RunStatus.CANCELED: frozenset(),
    }
    _event_by_status: dict[RunStatus, RunEventType] = {
        RunStatus.QUEUED: RunEventType.RUN_QUEUED,
        RunStatus.RUNNING: RunEventType.RUN_STARTED,
        RunStatus.SUCCEEDED: RunEventType.RUN_COMPLETED,
        RunStatus.FAILED: RunEventType.RUN_FAILED,
        RunStatus.CANCELED: RunEventType.RUN_CANCELED,
    }

    def validate(self, run: Run, to_status: RunStatus) -> RunTransition:
        """Return a transition if legal, otherwise raise."""

        if to_status not in self._allowed_transitions[run.status]:
            raise InvalidRunTransitionError(from_status=run.status, to_status=to_status)

        return RunTransition(
            from_status=run.status,
            to_status=to_status,
            event_type=self._event_by_status[to_status],
        )

    def queue(self, run: Run) -> RunTransition:
        """Validate that a run can be queued."""

        return self.validate(run, RunStatus.QUEUED)

    def start(self, run: Run) -> RunTransition:
        """Validate that a run can start execution."""

        return self.validate(run, RunStatus.RUNNING)

    def succeed(self, run: Run) -> RunTransition:
        """Validate that a run can complete successfully."""

        return self.validate(run, RunStatus.SUCCEEDED)

    def fail(self, run: Run) -> RunTransition:
        """Validate that a run can fail."""

        return self.validate(run, RunStatus.FAILED)

    def cancel(self, run: Run) -> RunTransition:
        """Validate that a run can be canceled."""

        return self.validate(run, RunStatus.CANCELED)
