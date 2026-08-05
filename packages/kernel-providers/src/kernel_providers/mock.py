"""Deterministic provider for tests, local execution, and eval baselines."""

from __future__ import annotations

from collections.abc import Iterable

from kernel_providers.base import (
    LLMFinishReason,
    LLMMessage,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMUsage,
)


class MockLLMProvider:
    """A deterministic provider that never performs network I/O."""

    def __init__(
        self,
        *,
        response_prefix: str = "Mock response",
        fail_with: LLMProviderError | None = None,
        tool_calls: tuple[LLMToolCall, ...] = (),
    ) -> None:
        self._response_prefix = response_prefix
        self._fail_with = fail_with
        self._tool_calls = tool_calls

    @property
    def name(self) -> str:
        return "mock"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if self._fail_with is not None:
            raise self._fail_with

        prompt = _last_user_content(request.messages)
        text = f"{self._response_prefix}: {prompt}"
        return LLMResponse(
            provider=self.name,
            model=request.model,
            text=text,
            usage=LLMUsage(
                input_tokens=_estimate_tokens(message.content for message in request.messages),
                output_tokens=_estimate_tokens([text]),
                estimated_cost=0.0,
            ),
            finish_reason=(
                LLMFinishReason.TOOL_CALLS if self._tool_calls else LLMFinishReason.STOP
            ),
            tool_calls=self._tool_calls,
            raw={"deterministic": True},
        )


def _last_user_content(messages: tuple[LLMMessage, ...]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    if messages:
        return messages[-1].content
    return ""


def _estimate_tokens(values: Iterable[str]) -> int:
    return sum(max(1, len(str(value).split())) for value in values)
