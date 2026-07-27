"""Model routing for provider selection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from kernel_providers import LLMProvider


class UnknownModelRouteError(ValueError):
    """Raised when a model reference cannot be routed to a provider."""


@dataclass(frozen=True)
class ModelRoute:
    provider_name: str
    model: str
    provider: LLMProvider


class ModelRouter:
    """Route explicit provider-prefixed model references to providers."""

    def __init__(self, providers: Mapping[str, LLMProvider]) -> None:
        self._providers = dict(providers)

    def route(self, model_ref: str) -> ModelRoute:
        provider_name, model = _split_model_ref(model_ref)
        provider = self._providers.get(provider_name)
        if provider is None:
            raise UnknownModelRouteError(f"No provider registered for {provider_name!r}.")
        return ModelRoute(provider_name=provider_name, model=model, provider=provider)


def _split_model_ref(model_ref: str) -> tuple[str, str]:
    provider_name, separator, model = model_ref.partition(":")
    if separator == "" or provider_name == "" or model == "":
        raise UnknownModelRouteError(f"Model {model_ref!r} must use '<provider>:<model>' format.")
    return provider_name, model
