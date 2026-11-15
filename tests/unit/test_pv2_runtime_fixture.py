from pathlib import Path
from uuid import uuid4

import pytest
from kernel_providers import LLMMessage, LLMProviderError, LLMRequest, LLMResponse, MessageRole

from scripts.pv1_harness import HarnessBlocked
from scripts.pv2_offline_harness import FixtureLedger
from scripts.pv2_runtime_fixture import RuntimeFixtureProvider


@pytest.mark.asyncio
@pytest.mark.parametrize("before", [True, False])
async def test_fixture_admission_retains_unknown_attempt(tmp_path: Path, before: bool) -> None:
    ledger = FixtureLedger(tmp_path / "ledger.jsonl", uuid4(), "a" * 64)
    ledger.create()
    executor, run = uuid4(), uuid4()
    ledger.change("register", executor=executor, attestation=ledger.binding)
    provider = RuntimeFixtureProvider(
        ledger,
        executor,
        run,
        [
            LLMProviderError("fixture", error_type="rate_limit"),
            LLMResponse(provider="pv2-fixture", model="fixture", text="ok"),
        ],
        task="task",
        failure_before_dispatch=before,
    )
    request = LLMRequest(
        model="fixture",
        messages=(LLMMessage(role=MessageRole.USER, content="task"),),
        metadata={"run_id": str(run)},
    )
    with pytest.raises(LLMProviderError) as first:
        await provider.complete(request)
    assert first.value.error_type == "rate_limit"
    if before:
        assert not ledger.snapshot().attempts
        assert (await provider.complete(request)).text == "ok"
    else:
        with pytest.raises(LLMProviderError) as second:
            await provider.complete(request)
        assert second.value.error_type == "pv2_admission_denied"
    assert provider.dispatches == 1
    assert next(iter(ledger.snapshot().attempts.values())).complete is before


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatch", ["run", "model", "task"])
async def test_fixture_request_binding_blocks_before_budget(tmp_path: Path, mismatch: str) -> None:
    ledger = FixtureLedger(tmp_path / "ledger.jsonl", uuid4(), "a" * 64)
    ledger.create()
    executor, run = uuid4(), uuid4()
    ledger.change("register", executor=executor, attestation=ledger.binding)
    provider = RuntimeFixtureProvider(
        ledger,
        executor,
        run,
        [LLMResponse(provider="pv2-fixture", model="fixture", text="ok")],
        task="task",
    )
    request = LLMRequest(
        model="other" if mismatch == "model" else "fixture",
        messages=(
            LLMMessage(role=MessageRole.USER, content="other" if mismatch == "task" else "task"),
        ),
        metadata={"run_id": str(uuid4() if mismatch == "run" else run)},
    )
    with pytest.raises(HarnessBlocked):
        await provider.complete(request)
    assert provider.dispatches == 0 and not ledger.snapshot().attempts
