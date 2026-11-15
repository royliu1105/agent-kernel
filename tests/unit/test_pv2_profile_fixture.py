"""Installed transport hooks, with sockets forbidden and a disposable evidence tree."""

from __future__ import annotations

import importlib
import json
import re
import socket
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from kernel_providers import LLMMessage, LLMProviderError, LLMRequest, MessageRole

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("No network permitted in PV2 hook tests")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.syspath_prepend(str(ROOT / "tests/fixtures"))
    module = importlib.import_module("pv2_profile")
    runtime = importlib.import_module("cf2_runtime")
    monkeypatch.setattr(runtime, "EVIDENCE", tmp_path)
    monkeypatch.setattr(module, "EVIDENCE", tmp_path)
    monkeypatch.setattr(module, "guard", lambda: None)
    monkeypatch.setattr(
        module, "PROMPT_PATH", ROOT / "docs/pilots/prompts/pv1-runbook-assistant-v1.txt"
    )
    runtime.save("identities.json", {"operator": {"workspace_id": str(uuid4())}})
    module.setup()
    for key, value in module.LIMITS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("PV2_PROFILE", "1")
    monkeypatch.setenv("CF2_ROLE", "worker")
    journal = module.install()
    try:
        yield module
    finally:
        journal.append("case_close")
        patch.stopall()


def request(module: ModuleType, case: str = "approve") -> LLMRequest:
    return LLMRequest(
        model=module.MODEL,
        max_output_tokens=2048,
        metadata={"run_id": str(uuid4())},
        messages=(
            LLMMessage(role=MessageRole.SYSTEM, content=module.PROMPT_PATH.read_text()),
            LLMMessage(role=MessageRole.USER, content=json.dumps({"case": case})),
        ),
    )


def test_profile_constants_match_frozen_contract(fixture: ModuleType) -> None:
    text = (ROOT / "docs/pilots/pv1-2026-11-15-runbook-assistant.md").read_text()
    section = text.split("## Finalized Technical Profile\n", 1)[1].split("\n## ", 1)[0]
    profile = json.loads(re.findall(r"```json\n(.*?)\n```", section, re.DOTALL)[0])
    assert profile["first_batch_environment"] == fixture.LIMITS
    assert profile["model"] == "deepseek:" + fixture.MODEL


@pytest.mark.asyncio
async def test_installed_deepseek_hook_limits_dispatch_and_retains_usage(
    fixture: ModuleType,
) -> None:
    import kernel_runtime.router as router

    provider = router.create_default_model_router().route("deepseek:" + fixture.MODEL).provider
    value = request(fixture)
    assert (await provider.complete(value)).tool_calls[0].name == "github_ci_run_status"
    await provider.complete(value)
    with pytest.raises(LLMProviderError, match="admission"):
        await provider.complete(value)
    assert len(fixture.ledger().snapshot().attempts) == 2


@pytest.mark.asyncio
async def test_installed_hook_blocks_retry_after_uncertain_dispatch(fixture: ModuleType) -> None:
    import kernel_runtime.router as router

    provider = router.create_default_model_router().route("deepseek:" + fixture.MODEL).provider
    value = request(fixture, "retry_after")
    with pytest.raises(LLMProviderError) as first:
        await provider.complete(value)
    assert first.value.error_type == "rate_limit"
    with pytest.raises(LLMProviderError) as second:
        await provider.complete(value)
    assert second.value.error_type == "pv2_admission_denied"
    attempts = fixture.ledger().snapshot().attempts
    assert len(attempts) == 1 and not next(iter(attempts.values())).complete


def test_installed_embedding_uses_frozen_dimensions_and_shared_budget(fixture: ModuleType) -> None:
    import kernel_rag.embeddings as embeddings

    from scripts.pv1_harness import HarnessBlocked

    provider = embeddings.create_embedding_provider(
        {"AGENT_KERNEL_EMBEDDING_PROVIDER": "dashscope"}
    )
    assert provider.model == "text-embedding-v3" and provider.dimensions == 1024
    assert len(provider.embed_texts(["fixture"])[0]) == 1024
    with pytest.raises(HarnessBlocked):
        provider.embed_texts(["fixture"])
