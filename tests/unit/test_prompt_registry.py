import pytest
from kernel_runtime import PromptRegistry, PromptVersion


def test_prompt_registry_registers_and_loads_versions() -> None:
    registry = PromptRegistry()
    first = registry.register(
        PromptVersion(name="research", version="v1", content="Summarize carefully.")
    )
    second = registry.register(
        PromptVersion(name="research", version="v2", content="Summarize with citations.")
    )

    assert registry.get(name="research", version="v1") == first
    assert registry.latest(name="research") == second


def test_prompt_registry_rejects_duplicate_versions() -> None:
    registry = PromptRegistry()
    registry.register(PromptVersion(name="research", version="v1", content="First."))

    with pytest.raises(ValueError, match="already exists"):
        registry.register(PromptVersion(name="research", version="v1", content="Duplicate."))
