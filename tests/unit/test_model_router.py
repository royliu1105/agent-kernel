import pytest
from kernel_providers import MockLLMProvider, OpenAIProvider, ReplayLLMProvider
from kernel_runtime import ModelRouter, UnknownModelRouteError


def test_model_router_selects_provider_by_prefix() -> None:
    provider = MockLLMProvider()
    route = ModelRouter({"mock": provider}).route("mock:mock-small")

    assert route.provider_name == "mock"
    assert route.model == "mock-small"
    assert route.provider is provider


def test_model_router_selects_openai_provider_by_prefix() -> None:
    provider = OpenAIProvider(api_key="test-key")
    route = ModelRouter({"openai": provider}).route("openai:gpt-4.1-mini")

    assert route.provider_name == "openai"
    assert route.model == "gpt-4.1-mini"
    assert route.provider is provider


def test_model_router_selects_replay_provider_by_prefix() -> None:
    provider = ReplayLLMProvider()
    route = ModelRouter({"replay": provider}).route("replay:case-001")

    assert route.provider_name == "replay"
    assert route.model == "case-001"
    assert route.provider is provider


def test_model_router_rejects_unknown_provider() -> None:
    with pytest.raises(UnknownModelRouteError, match="No provider registered"):
        ModelRouter({"mock": MockLLMProvider()}).route("openai:gpt-4.1-mini")


def test_model_router_requires_prefixed_model_ref() -> None:
    with pytest.raises(UnknownModelRouteError, match="<provider>:<model>"):
        ModelRouter({"mock": MockLLMProvider()}).route("mock-small")
