"""Synthetic harness controls; no sockets, database, Docker, or live acceptance."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

import httpcore
import httpx
import pytest
from kernel_tools.external.config import (
    ExternalAccess,
    ExternalToolContract,
    HttpEndpoint,
    OpenAPIBinding,
    OpenAPIConfig,
)
from kernel_tools.external.http import _GuardedTransport
from kernel_tools.external.openapi import OpenAPITool
from kernel_tools.external.security import ExternalToolError
from kernel_tools.models import ToolExecutionContext

from scripts.pv1_harness import Budget, FixturePool, HarnessBlocked, Journal, read_events, reconcile

BODY = json.dumps(
    {"id": 43634747295, "run_attempt": 1, "head_sha": "2bb3f4ab1d50afa1cc2686b42b1ebcaf5db1f726"}
).encode()


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Fixture harness must not resolve or connect")

    for name in ("getaddrinfo", "create_connection"):
        monkeypatch.setattr(socket, name, forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


@pytest.fixture
def journal(tmp_path: Path) -> Journal:
    return Journal(tmp_path, uuid4(), uuid4())


def verdict(journal: Journal, expected: dict[UUID, int]) -> str:
    return reconcile(
        journal.path.parent,
        case_id=journal.case_id,
        executors=frozenset({journal.executor_id}),
        expected=expected,
        failed_executors=frozenset({journal.executor_id}) if journal.failed else frozenset(),
    ).verdict


async def invoke(pool: FixturePool, *, allowed: bool = True) -> dict[str, Any]:
    endpoint = HttpEndpoint(url="https://api.github.com", max_response_bytes=32768)
    transport = _GuardedTransport(endpoint)
    # Fixture-only injection below the maintained origin/path/size guards.
    await transport._pool.aclose()
    transport._pool = cast(httpcore.AsyncConnectionPool, pool)
    workspace = uuid4()
    binding = OpenAPIBinding(
        operation_id="github_ci_run_status",
        contract=ExternalToolContract(
            name="github_ci_run_status",
            read_only=True,
            idempotent=True,
            retry_safe=False,
            policy_decision="require_approval",
        ),
    )
    config = OpenAPIConfig(
        name="pv1_fixture",
        document=Path("unused-fixture.json"),
        endpoint=endpoint,
        bindings=(binding,),
        access=ExternalAccess(workspace_ids=(workspace,)),
    )
    async with httpx.AsyncClient(
        transport=transport, trust_env=False, follow_redirects=False
    ) as client:
        tool = OpenAPITool(
            client=client,
            config=config,
            binding=binding,
            method="get",
            path="/repos/royliu1105/agent-kernel/actions/runs/43634747295",
            schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["exclude_pull_requests"],
                        "properties": {"exclude_pull_requests": {"type": "boolean", "const": True}},
                    }
                },
            },
        )
        output = await tool.execute_with_context(
            {"query": {"exclude_pull_requests": True}},
            context=ToolExecutionContext(
                workspace_id=workspace if allowed else uuid4(),
                run_id=uuid4(),
                tool_call_id=pool.tool_call_id,
            ),
        )
        pool.validated(output["data"])
        return output


@pytest.mark.asyncio
async def test_known_dispatch_uses_real_adapter_and_guard(journal: Journal) -> None:
    tool = uuid4()
    pool = FixturePool(journal, tool, body=BODY)
    output = await invoke(pool)
    journal.append("case_close")
    assert output["untrusted"] is True
    assert pool.delegations == 1
    assert verdict(journal, {tool: 1}) == "pass"
    assert b"head_sha" not in journal.path.read_bytes()
    assert journal.path.stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_duplicate_dispatch_fails_even_with_incomplete_tail(journal: Journal) -> None:
    tool = uuid4()
    pool = FixturePool(journal, tool, body=BODY)
    await invoke(pool)
    await invoke(pool)
    with journal.path.open("ab") as stream:
        stream.write(b'{"truncated":')
    assert pool.delegations == 2
    assert verdict(journal, {tool: 1}) == "fail"


def test_zero_requires_complete_window_and_every_executor(journal: Journal) -> None:
    tool = uuid4()
    assert verdict(journal, {tool: 0}) == "unknown"
    journal.append("case_close")
    assert verdict(journal, {tool: 0}) == "pass"
    result = reconcile(
        journal.path.parent,
        case_id=journal.case_id,
        executors=frozenset({journal.executor_id, uuid4()}),
        expected={tool: 0},
    )
    assert result.verdict == "unknown"


@pytest.mark.asyncio
async def test_workspace_denial_does_not_dispatch(journal: Journal) -> None:
    pool = FixturePool(journal, uuid4(), body=BODY)
    with pytest.raises(ExternalToolError, match="access denied"):
        await invoke(pool, allowed=False)
    journal.append("case_close")
    assert pool.delegations == 0
    assert verdict(journal, {pool.tool_call_id: 0}) == "pass"


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["https://other.invalid/x", "https://api.github.com/other"])
async def test_guard_denial_before_pool(journal: Journal, url: str) -> None:
    endpoint = HttpEndpoint(url="https://api.github.com/repos")
    transport = _GuardedTransport(endpoint)
    await transport._pool.aclose()
    pool = FixturePool(journal, uuid4(), body=BODY)
    transport._pool = cast(httpcore.AsyncConnectionPool, pool)
    async with httpx.AsyncClient(transport=transport, trust_env=False) as client:
        with pytest.raises(ExternalToolError, match="not approved"):
            await client.get(url)
    assert pool.delegations == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body,status,headers",
    [
        (b"bad-json", 200, None),
        (b"{}", 200, None),
        (BODY, 302, [(b"location", b"https://other.invalid")]),
        (BODY, 200, [(b"content-encoding", b"gzip")]),
        (b"x" * 32769, 200, None),
        (BODY, 503, None),
    ],
)
async def test_incomplete_or_invalid_response_never_passes(
    journal: Journal,
    body: bytes,
    status: int,
    headers: list[tuple[bytes, bytes]] | None,
) -> None:
    pool = FixturePool(journal, uuid4(), body=body, status=status, headers=headers)
    with pytest.raises((ExternalToolError, HarnessBlocked)):
        await invoke(pool)
    journal.append("case_close")
    assert pool.delegations == 1
    assert verdict(journal, {pool.tool_call_id: 1}) == "unknown"
    with pytest.raises(ExternalToolError):
        await invoke(pool)
    assert pool.delegations == 1


@pytest.mark.asyncio
async def test_journal_before_send_fsync_failure_blocks_dispatch(
    journal: Journal,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_: int) -> None:
        raise OSError("synthetic persistence failure")

    monkeypatch.setattr(os, "fsync", fail)
    pool = FixturePool(journal, uuid4(), body=BODY)
    with pytest.raises(ExternalToolError):
        await invoke(pool)
    assert pool.delegations == 0
    assert journal.failed
    assert verdict(journal, {pool.tool_call_id: 1}) == "unknown"


@pytest.mark.asyncio
@pytest.mark.parametrize("boundary", ["response_headers", "response_validated", "case_close"])
async def test_journal_after_send_failure_is_not_success(
    journal: Journal,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
) -> None:
    original = journal.append

    def append(event: str, **kwargs: Any) -> None:
        if event == boundary:
            journal.failed = True
            raise HarnessBlocked("synthetic completion failure")
        original(event, **kwargs)

    monkeypatch.setattr(journal, "append", append)
    pool = FixturePool(journal, uuid4(), body=BODY)
    with pytest.raises((ExternalToolError, HarnessBlocked)):
        await invoke(pool)
        journal.append("case_close")
    assert pool.delegations == 1
    assert verdict(journal, {pool.tool_call_id: 1}) == "unknown"


def test_crash_after_start_and_corrupt_sequence_remain_unknown(journal: Journal) -> None:
    tool = uuid4()
    journal.append("dispatch_start", attempt=uuid4(), tool=tool)
    assert verdict(journal, {tool: 1}) == "unknown"
    rows = journal.path.read_text().replace('"seq":2', '"seq":4')
    journal.path.write_text(rows)
    with pytest.raises(HarnessBlocked):
        read_events(journal.path)
    assert verdict(journal, {tool: 1}) == "unknown"


def test_concurrent_writes_are_serialized_and_cannot_overwrite(journal: Journal) -> None:
    tool = uuid4()
    with ThreadPoolExecutor(max_workers=4) as workers:
        list(
            workers.map(
                lambda _: journal.append("dispatch_start", attempt=uuid4(), tool=tool), range(20)
            )
        )
    assert [event.seq for event in read_events(journal.path)] == list(range(1, 22))
    with pytest.raises(FileExistsError):
        Journal(journal.path.parent, journal.case_id, journal.executor_id)
    assert verdict(journal, {tool: 1}) == "fail"


@pytest.mark.asyncio
async def test_replacement_and_second_tool_keep_prior_counts(journal: Journal) -> None:
    second = Journal(journal.path.parent, journal.case_id, uuid4())
    first_tool, second_tool = uuid4(), uuid4()
    await invoke(FixturePool(journal, first_tool, body=BODY))
    journal.append("case_close")
    await invoke(FixturePool(second, second_tool, body=BODY))
    second.append("case_close")
    result = reconcile(
        journal.path.parent,
        case_id=journal.case_id,
        executors=frozenset({journal.executor_id, second.executor_id}),
        expected={first_tool: 1, second_tool: 1},
    )
    assert result.verdict == "pass"
    assert result.starts == {first_tool: 1, second_tool: 1}


def test_unknown_charges_block_next_ledger_admission() -> None:
    budget = Budget()
    attempt, task = uuid4(), uuid4()
    budget.reserve(attempt, task, Decimal("0.10"))
    with pytest.raises(HarnessBlocked):
        budget.settle(attempt, None)
    with pytest.raises(HarnessBlocked):
        budget.reserve(uuid4(), task, Decimal("0.10"))
    assert budget.pending == {attempt: (task, Decimal("0.10"))}


@pytest.mark.parametrize("cost", ["NaN", "Infinity", "-1", "0.26"])
def test_budget_invalid_or_excess_reservation_denied(cost: str) -> None:
    with pytest.raises(HarnessBlocked):
        Budget().reserve(uuid4(), uuid4(), Decimal(cost))


def test_budget_respects_task_attempt_slots_and_keeps_locked_reserve() -> None:
    budget = Budget()
    for _ in range(5):
        task = uuid4()
        for _ in range(2):
            attempt = uuid4()
            budget.reserve(attempt, task, Decimal("0.10"))
            budget.settle(attempt, Decimal("0.10"))
        with pytest.raises(HarnessBlocked):
            budget.reserve(uuid4(), task, Decimal("0.01"))
    with pytest.raises(HarnessBlocked):
        budget.reserve(uuid4(), uuid4(), Decimal("0.01"))
    assert budget.spent == Decimal("1.00")


@pytest.mark.parametrize("body,provider", [(BODY + b" ", "deepseek"), (BODY, "dashscope")])
def test_changed_or_wrong_provider_payload_blocks_budget(body: bytes, provider: str) -> None:
    budget = Budget()
    with pytest.raises(HarnessBlocked):
        budget.check_payload(
            body, approved_sha256=hashlib.sha256(BODY).hexdigest(), provider=provider
        )
    with pytest.raises(HarnessBlocked):
        budget.reserve(uuid4(), uuid4(), Decimal("0.01"))


def test_exact_payload_and_known_usage_admitted_once() -> None:
    budget = Budget()
    budget.check_payload(
        BODY, approved_sha256=hashlib.sha256(BODY).hexdigest(), provider="deepseek"
    )
    attempt, task = uuid4(), uuid4()
    budget.reserve(attempt, task, Decimal("0.10"))
    budget.settle(attempt, Decimal("0.01"))
    with pytest.raises(HarnessBlocked):
        budget.reserve(attempt, task, Decimal("0.10"))
    assert budget.spent == Decimal("0.01")


def test_missing_tool_binding_rejected_before_observation(journal: Journal) -> None:
    with pytest.raises(HarnessBlocked, match="binding"):
        FixturePool(journal, cast(UUID, None), body=BODY)
    assert len(read_events(journal.path)) == 1


def test_initial_directory_sync_failure_does_not_open_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_: int) -> None:
        raise OSError("fixture directory durability failure")

    monkeypatch.setattr(os, "fsync", fail)
    case, executor = uuid4(), uuid4()
    with pytest.raises(OSError):
        Journal(tmp_path, case, executor)
    assert (
        reconcile(
            tmp_path, case_id=case, executors=frozenset({executor}), expected={uuid4(): 0}
        ).verdict
        == "unknown"
    )


@pytest.mark.parametrize("actual", [None, Decimal("NaN"), Decimal("-1"), Decimal("0.11")])
def test_uncertain_or_over_reservation_charge_never_releases_reserve(
    actual: Decimal | None,
) -> None:
    budget = Budget()
    attempt, task = uuid4(), uuid4()
    budget.reserve(attempt, task, Decimal("0.10"))
    with pytest.raises(HarnessBlocked):
        budget.settle(attempt, actual)
    assert attempt in budget.pending and budget.blocked


def test_total_and_task_cost_caps_block_admission() -> None:
    budget = Budget(ceiling=Decimal("0.12"))
    attempt, task = uuid4(), uuid4()
    budget.reserve(attempt, task, Decimal("0.10"))
    budget.settle(attempt, Decimal("0.10"))
    with pytest.raises(HarnessBlocked):
        budget.reserve(uuid4(), uuid4(), Decimal("0.03"))
    per_task = Budget()
    attempt = uuid4()
    per_task.reserve(attempt, task, Decimal("0.20"))
    per_task.settle(attempt, Decimal("0.20"))
    with pytest.raises(HarnessBlocked):
        per_task.reserve(uuid4(), task, Decimal("0.06"))


@pytest.mark.asyncio
async def test_truncated_journal_cannot_restart_observation(journal: Journal) -> None:
    journal.path.write_bytes(b"")
    pool = FixturePool(journal, uuid4(), body=BODY)
    with pytest.raises(ExternalToolError):
        await invoke(pool)
    assert pool.delegations == 0
    assert journal.failed


def test_nonempty_journal_rollback_blocks_next_write(journal: Journal) -> None:
    opened = journal.path.read_bytes()
    journal.append("dispatch_start", attempt=uuid4(), tool=uuid4())
    journal.path.write_bytes(opened)
    with pytest.raises(HarnessBlocked):
        journal.append("dispatch_start", attempt=uuid4(), tool=uuid4())
    assert journal.failed
    assert journal.path.read_bytes() == opened


def test_concurrent_writers_cannot_bypass_sticky_sync_failure(
    journal: Journal,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered, release, second_started = threading.Event(), threading.Event(), threading.Event()
    sync_calls = 0

    def fail_once(_: int) -> None:
        nonlocal sync_calls
        sync_calls += 1
        if sync_calls == 1:
            entered.set()
            assert release.wait(5)
            raise OSError("fixture sync failure")

    def write(*, second: bool = False) -> None:
        if second:
            second_started.set()
        with pytest.raises(HarnessBlocked):
            journal.append("dispatch_start", attempt=uuid4(), tool=uuid4())

    monkeypatch.setattr(os, "fsync", fail_once)
    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(write)
        try:
            assert entered.wait(5)
            second = workers.submit(write, second=True)
            assert second_started.wait(5)
        finally:
            release.set()
        first.result()
        second.result()
    assert sync_calls == 1
    assert journal.failed
    assert len(read_events(journal.path)) == 2


@pytest.mark.asyncio
async def test_dispatch_after_close_is_a_failure_not_hidden_as_unknown(journal: Journal) -> None:
    tool = uuid4()
    await invoke(FixturePool(journal, tool, body=BODY))
    journal.append("case_close")
    events = read_events(journal.path)
    late = events[1].model_copy(update={"seq": len(events) + 1, "attempt_id": uuid4()})
    with journal.path.open("ab") as stream:
        stream.write((late.model_dump_json() + "\n").encode())
    result = reconcile(
        journal.path.parent,
        case_id=journal.case_id,
        executors=frozenset({journal.executor_id}),
        expected={tool: 1},
    )
    assert result.starts == {tool: 2}
    assert result.verdict == "fail"
