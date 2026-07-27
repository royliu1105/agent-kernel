import pytest
from kernel_providers import LLMMessage, LLMProviderError, LLMRequest, MessageRole, MockLLMProvider


@pytest.mark.asyncio
async def test_mock_provider_returns_deterministic_response() -> None:
    provider = MockLLMProvider()
    request = LLMRequest(
        model="mock-small",
        messages=(LLMMessage(role=MessageRole.USER, content="summarize notes"),),
    )

    first = await provider.complete(request)
    second = await provider.complete(request)

    assert first == second
    assert first.provider == "mock"
    assert first.model == "mock-small"
    assert first.text == "Mock response: summarize notes"
    assert first.usage.input_tokens == 2
    assert first.usage.output_tokens == 4
    assert first.usage.estimated_cost == 0.0


@pytest.mark.asyncio
async def test_mock_provider_can_fail_deterministically() -> None:
    provider = MockLLMProvider(
        fail_with=LLMProviderError("provider unavailable", error_type="mock_failure")
    )
    request = LLMRequest(
        model="mock-small",
        messages=(LLMMessage(role=MessageRole.USER, content="summarize notes"),),
    )

    with pytest.raises(LLMProviderError) as error:
        await provider.complete(request)

    assert error.value.error_type == "mock_failure"
    assert str(error.value) == "provider unavailable"
