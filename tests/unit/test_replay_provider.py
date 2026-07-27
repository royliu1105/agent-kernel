import pytest
from kernel_providers import (
    LLMMessage,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    MessageRole,
    ReplayLLMProvider,
)


@pytest.mark.asyncio
async def test_replay_provider_returns_recorded_response_by_model() -> None:
    provider = ReplayLLMProvider(
        {
            "case-001": LLMResponse(
                provider="fixture",
                model="fixture-model",
                text="Recorded response",
                usage=LLMUsage(input_tokens=3, output_tokens=2, estimated_cost=0.0),
                raw={"fixture": "case-001"},
            )
        }
    )

    response = await provider.complete(
        LLMRequest(
            model="case-001",
            messages=(LLMMessage(role=MessageRole.USER, content="ignored for baseline"),),
        )
    )

    assert response.provider == "replay"
    assert response.model == "case-001"
    assert response.text == "Recorded response"
    assert response.usage.input_tokens == 3
    assert response.raw == {"fixture": "case-001"}


@pytest.mark.asyncio
async def test_replay_provider_fails_clearly_for_missing_fixture() -> None:
    provider = ReplayLLMProvider()

    with pytest.raises(LLMProviderError) as error_info:
        await provider.complete(
            LLMRequest(
                model="missing-case",
                messages=(LLMMessage(role=MessageRole.USER, content="hello"),),
            )
        )

    assert error_info.value.error_type == "replay_not_found"
