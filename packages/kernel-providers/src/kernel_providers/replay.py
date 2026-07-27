"""Replay provider for deterministic regression fixtures."""

from __future__ import annotations

from collections.abc import Mapping

from kernel_providers.base import LLMProviderError, LLMRequest, LLMResponse


class ReplayLLMProvider:
    """Return pre-recorded responses by model name.

    The first baseline deliberately matches only on routed model name. Prompt-aware matching can be
    added with eval datasets once replay cases have a stable file format.
    """

    def __init__(self, responses: Mapping[str, LLMResponse] | None = None) -> None:
        self._responses = dict(responses or {})

    @property
    def name(self) -> str:
        return "replay"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        response = self._responses.get(request.model)
        if response is None:
            raise LLMProviderError(
                f"No replay response registered for model {request.model!r}.",
                error_type="replay_not_found",
            )
        return response.model_copy(update={"provider": self.name, "model": request.model})
