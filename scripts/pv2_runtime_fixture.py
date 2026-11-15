"""Bound scripted provider for real API/Worker tests; no live provider delegate."""

from __future__ import annotations

from uuid import UUID, uuid4

from kernel_providers import LLMProviderError, LLMRequest, LLMResponse

from scripts.pv1_harness import HarnessBlocked
from scripts.pv2_offline_harness import FixtureLedger


class RuntimeFixtureProvider:
    name = "pv2-fixture"

    def __init__(
        self,
        ledger: FixtureLedger,
        executor: UUID,
        run_id: UUID,
        outcomes: list[LLMResponse | LLMProviderError],
        *,
        task: str,
        failure_before_dispatch: bool = False,
    ) -> None:
        self.ledger, self.executor, self.run_id = ledger, executor, run_id
        self.outcomes = list(outcomes)
        self.task, self.failure_before_dispatch = task, failure_before_dispatch
        self.requests: list[LLMRequest] = []
        self.dispatches = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if (
            request.metadata.get("run_id") != str(self.run_id)
            or request.model != "fixture"
            or not request.messages
            or request.messages[0].content != self.task
        ):
            raise HarnessBlocked("Runtime fixture request binding mismatch")
        self.requests.append(request)
        if not self.outcomes:
            raise HarnessBlocked("Unexpected provider continuation")
        outcome = self.outcomes[0]
        if self.failure_before_dispatch and isinstance(outcome, LLMProviderError):
            self.outcomes.pop(0)
            raise outcome
        attempt = uuid4()
        try:
            self.ledger.change(
                "reserve",
                executor=self.executor,
                task=self.run_id,
                attempt=attempt,
            )
        except HarnessBlocked as exc:
            raise LLMProviderError(
                "Fixture admission denied", error_type="pv2_admission_denied"
            ) from exc
        self.outcomes.pop(0)
        self.dispatches += 1
        if isinstance(outcome, LLMProviderError):
            # Simulate a retryable upstream error whose charge is still unknown.
            raise outcome
        self.ledger.change("complete", executor=self.executor, attempt=attempt)
        return outcome
