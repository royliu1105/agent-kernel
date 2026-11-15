"""Offline transport integration; no database, container or provider connection."""

from __future__ import annotations

import multiprocessing
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from kernel_providers import DeepSeekProvider, LLMMessage, LLMRequest, MessageRole
from kernel_rag import DashScopeEmbeddingProvider

from scripts.pv1_harness import HarnessBlocked, Journal
from scripts.pv2_offline_harness import FixtureAdmissionTransport, FixtureLedger, request_hash

BINDING = "a" * 64
URL = "https://api.deepseek.com/responses"
PAYLOAD: dict[str, object] = {"model": "deepseek-v4-flash", "input": [], "max_output_tokens": 1024}
RESPONSE: dict[str, object] = {
    "output_text": "fixture",
    "usage": {"input_tokens": 1, "output_tokens": 1},
}


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("No network allowed")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


@pytest.fixture
def ledger(tmp_path: Path) -> FixtureLedger:
    result = FixtureLedger(tmp_path / "case.jsonl", uuid4(), BINDING)
    result.create()
    return result


def register(ledger: FixtureLedger, role: str = "worker") -> UUID:
    executor = uuid4()
    ledger.change(
        "register",
        executor=executor,
        role="api" if role == "api" else "worker",
        attestation=BINDING,
    )
    return executor


def transport(
    ledger: FixtureLedger, executor: UUID, task: UUID, **kwargs: Any
) -> FixtureAdmissionTransport:
    return FixtureAdmissionTransport(
        ledger,
        executor,
        task,
        kind="generation",
        url=URL,
        approved_requests=frozenset({request_hash(PAYLOAD)}),
        **kwargs,
    )


async def complete(hook: FixtureAdmissionTransport) -> None:
    await DeepSeekProvider(api_key="synthetic", transport=hook).complete(
        LLMRequest(model="deepseek-v4-flash", messages=(), max_output_tokens=1024)
    )


@pytest.mark.asyncio
async def test_real_adapter_initial_and_new_executor_continuation_share_budget(
    ledger: FixtureLedger,
) -> None:
    task = uuid4()
    first = transport(ledger, register(ledger), task, response=RESPONSE)
    await complete(first)
    reopened = FixtureLedger(ledger.path, ledger.case_id, BINDING)
    resumed = transport(reopened, register(reopened, "api"), task, response=RESPONSE)
    await complete(resumed)
    with pytest.raises(HarnessBlocked, match="allocation"):
        await complete(resumed)
    assert first.dispatches == resumed.dispatches == 1
    state = reopened.snapshot()
    assert len(state.attempts) == 2
    assert sum(item.reserved for item in state.attempts.values()) == Decimal("0.25")
    assert all(item.complete for item in state.attempts.values())
    assert b"synthetic" not in ledger.path.read_bytes()
    assert b'fixture"' not in ledger.path.read_bytes().replace(b'"evidence_class":"fixture"', b"")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response", [(503, RESPONSE), (200, {}), (200, {"usage": {"input_tokens": True}})]
)
async def test_unknown_charge_blocks_retry_and_replacement(
    ledger: FixtureLedger, status: int, response: dict[str, object]
) -> None:
    task = uuid4()
    first = transport(ledger, register(ledger), task, response=response, status=status)
    with pytest.raises(HarnessBlocked):
        await complete(first)
    replacement = transport(ledger, register(ledger, "api"), task, response=RESPONSE)
    with pytest.raises(HarnessBlocked, match="Unresolved"):
        await complete(replacement)
    assert first.dispatches == 1 and replacement.dispatches == 0
    assert not next(iter(ledger.snapshot().attempts.values())).complete


@pytest.mark.asyncio
async def test_changed_effective_prompt_denied_before_dispatch(ledger: FixtureLedger) -> None:
    hook = transport(ledger, register(ledger), uuid4(), response=RESPONSE)
    with pytest.raises(HarnessBlocked, match="effective request"):
        await DeepSeekProvider(api_key="synthetic", transport=hook).complete(
            LLMRequest(
                model="deepseek-v4-flash",
                messages=(LLMMessage(role=MessageRole.USER, content="changed"),),
                max_output_tokens=1024,
            )
        )
    assert hook.dispatches == 0 and not ledger.snapshot().attempts


def test_real_embedding_batches_cannot_bypass_shared_allowance(ledger: FixtureLedger) -> None:
    payload: dict[str, object] = {
        "model": "text-embedding-v3",
        "input": ["fixture"] * 10,
        "dimensions": 64,
    }
    hook = FixtureAdmissionTransport(
        ledger,
        register(ledger),
        uuid4(),
        kind="embedding",
        url="https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings",
        approved_requests=frozenset({request_hash(payload)}),
        response={
            "data": [{"index": i, "embedding": [0.1] * 64} for i in range(10)],
            "usage": {"total_tokens": 10},
        },
    )
    provider = DashScopeEmbeddingProvider(
        env={"DASHSCOPE_API_KEY": "synthetic", "DASHSCOPE_EMBEDDING_DIMENSIONS": "64"},
        transport=hook,
    )
    with pytest.raises(HarnessBlocked, match="allocation"):
        provider.embed_texts(["fixture"] * 20)
    assert hook.dispatches == 1
    assert sum(item.reserved for item in ledger.snapshot().attempts.values()) == Decimal("0.10")


def test_manifest_registration_and_close_are_enforced(ledger: FixtureLedger) -> None:
    with pytest.raises(HarnessBlocked, match="attestation"):
        ledger.change("register", executor=uuid4(), attestation="b" * 64)
    with pytest.raises(HarnessBlocked, match="Unregistered"):
        ledger.change("reserve", executor=uuid4(), attempt=uuid4(), task=uuid4())
    executor = register(ledger)
    ledger.change("close", executor=executor)
    with pytest.raises(HarnessBlocked, match="Closed"):
        register(ledger)
    assert ledger.path.stat().st_mode & 0o777 == 0o600


def test_concurrent_instances_admit_only_one_unresolved_request(ledger: FixtureLedger) -> None:
    executor = register(ledger)

    def reserve(_: int) -> bool:
        reopened = FixtureLedger(ledger.path, ledger.case_id, BINDING)
        try:
            reopened.change("reserve", executor=executor, attempt=uuid4(), task=uuid4())
            return True
        except HarnessBlocked:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(16))) == 1
    assert len(ledger.snapshot().attempts) == 1


def _crash_after_reserve(path: Path, case: UUID, executor: UUID) -> None:
    FixtureLedger(path, case, BINDING).change(
        "reserve", executor=executor, attempt=uuid4(), task=uuid4()
    )
    os._exit(7)


def test_process_death_keeps_reservation_and_prevents_replay(ledger: FixtureLedger) -> None:
    executor = register(ledger)
    process = multiprocessing.get_context("fork").Process(
        target=_crash_after_reserve, args=(ledger.path, ledger.case_id, executor)
    )
    process.start()
    process.join(10)
    if process.is_alive():
        process.kill()
        process.join()
        pytest.fail("Fixture subprocess did not exit")
    assert process.exitcode == 7
    with pytest.raises(HarnessBlocked, match="Unresolved"):
        ledger.change("reserve", executor=register(ledger), attempt=uuid4(), task=uuid4())
    with pytest.raises(HarnessBlocked, match="uncertain"):
        ledger.change("close", executor=executor)


@pytest.mark.parametrize("tail", [b"truncated", b"{}\n"])
def test_corrupt_ledger_fails_closed(ledger: FixtureLedger, tail: bytes) -> None:
    with ledger.path.open("ab") as stream:
        stream.write(tail)
    with pytest.raises(HarnessBlocked):
        register(ledger)


@pytest.mark.asyncio
async def test_persistence_failure_blocks_delegation_and_future_writer(
    ledger: FixtureLedger, monkeypatch: pytest.MonkeyPatch
) -> None:
    executor = register(ledger)
    hook = transport(ledger, executor, uuid4(), response=RESPONSE)

    def fail(_: int) -> None:
        raise OSError("fixture durability failure")

    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(HarnessBlocked):
        await complete(hook)
    assert hook.dispatches == 0
    with pytest.raises(HarnessBlocked):
        ledger.snapshot()


def test_manifest_reconciliation_needs_all_executor_journals(
    ledger: FixtureLedger, tmp_path: Path
) -> None:
    journals = tmp_path / "journals"
    journals.mkdir()
    worker, api = register(ledger), register(ledger, "api")
    tool = uuid4()
    first = Journal(journals, ledger.case_id, worker)
    first.append("case_close")
    ledger.change("close", executor=worker)
    assert ledger.observation(journals, {tool: 0}).verdict == "unknown"
    second = Journal(journals, ledger.case_id, api)
    second.append("case_close")
    assert ledger.observation(journals, {tool: 0}).verdict == "pass"
    assert (
        ledger.observation(journals, {tool: 0}, failed_executors=frozenset({api})).verdict
        == "unknown"
    )
    unexpected = Journal(journals, ledger.case_id, uuid4())
    unexpected.append("case_close")
    assert ledger.observation(journals, {tool: 0}).verdict == "unknown"


@pytest.mark.asyncio
async def test_excess_usage_keeps_charge_unresolved(ledger: FixtureLedger) -> None:
    hook = transport(
        ledger,
        register(ledger),
        uuid4(),
        response={"usage": {"input_tokens": 16001, "output_tokens": 1}},
    )
    with pytest.raises(HarnessBlocked, match="usage"):
        await complete(hook)
    assert not next(iter(ledger.snapshot().attempts.values())).complete


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-1", "0", "0.251"])
def test_invalid_reservation_is_not_persisted(ledger: FixtureLedger, amount: str) -> None:
    executor = register(ledger)
    with pytest.raises(HarnessBlocked):
        ledger.change(
            "reserve", executor=executor, task=uuid4(), attempt=uuid4(), amount=Decimal(amount)
        )
    assert not ledger.snapshot().attempts


def test_shared_generation_cap_and_task_slots(ledger: FixtureLedger) -> None:
    executor = register(ledger)
    for _ in range(5):
        task = uuid4()
        for _ in range(2):
            attempt = uuid4()
            ledger.change("reserve", executor=executor, task=task, attempt=attempt)
            ledger.change("complete", executor=executor, attempt=attempt)
    with pytest.raises(HarnessBlocked):
        ledger.change("reserve", executor=executor, task=uuid4(), attempt=uuid4())
    assert sum(item.reserved for item in ledger.snapshot().attempts.values()) == Decimal("1.25")


@pytest.mark.parametrize("failure_at", [1, 2, 3])
def test_failed_initialization_cannot_be_reopened(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_at: int,
) -> None:
    ledger = FixtureLedger(tmp_path / "failed.jsonl", uuid4(), BINDING)
    original = os.fsync
    calls = 0

    def fail(fd: int) -> None:
        nonlocal calls
        calls += 1
        if calls == failure_at:
            raise OSError("fixture initialization failure")
        original(fd)

    with monkeypatch.context() as scoped:
        scoped.setattr(os, "fsync", fail)
        with pytest.raises((OSError, HarnessBlocked)):
            ledger.create()
    reopened = FixtureLedger(ledger.path, ledger.case_id, BINDING)
    with pytest.raises(HarnessBlocked):
        register(reopened)


def test_interrupted_initialization_refuses_admission(ledger: FixtureLedger) -> None:
    first_snapshot = ledger.path.read_bytes().splitlines(keepends=True)[0]
    ledger.path.write_bytes(first_snapshot)
    with pytest.raises(HarnessBlocked, match="incomplete"):
        register(ledger)
