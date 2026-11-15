"""Offline-only pilot evidence primitives. No deployment or live network entry point."""

from __future__ import annotations

import fcntl
import hashlib
import os
import threading
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import httpcore
from pydantic import BaseModel, ConfigDict, Field


class HarnessBlocked(RuntimeError):
    """Fail closed; never classify this control failure as a retryable provider error."""


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    evidence_class: Literal["fixture"] = "fixture"
    case_id: UUID
    executor_id: UUID
    seq: int = Field(ge=1, strict=True)
    at: datetime
    event: Literal[
        "case_open",
        "dispatch_start",
        "response_headers",
        "response_validated",
        "dispatch_error",
        "case_close",
    ]
    attempt_id: UUID | None = None
    tool_call_id: UUID | None = None
    error: Literal["guard", "transport", "malformed_response", "identity_mismatch"] | None = None


def _scan(path: Path) -> tuple[list[Event], bool]:
    events: list[Event] = []
    try:
        with path.open("rb") as stream:
            raw = stream.read(4_194_305)
        if not raw or len(raw) > 4_194_304:
            return events, False
        for line in raw.splitlines(keepends=True):
            if not line.endswith(b"\n"):
                return events, False
            event = Event.model_validate_json(line)
            if event.seq != len(events) + 1:
                return events, False
            events.append(event)
        return events, True
    except (OSError, ValueError):
        return events, False


def read_events(path: Path) -> list[Event]:
    events, valid = _scan(path)
    if not valid:
        raise HarnessBlocked("Missing or corrupt fixture journal")
    return events


class Journal:
    """One executor journal; flock serializes appenders, fsync precedes delegation."""

    def __init__(self, root: Path, case_id: UUID, executor_id: UUID) -> None:
        if not isinstance(case_id, UUID) or not isinstance(executor_id, UUID):
            raise HarnessBlocked("Missing trusted case/executor binding")
        self.case_id, self.executor_id = case_id, executor_id
        self.path = root / f"{executor_id}.jsonl"
        self.failed = False
        self._lock = threading.Lock()
        self._opened = False
        self._last_seq = 0
        # root is supplied by a disposable test directory, never a runtime path.
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        directory = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        self.append("case_open")

    def append(
        self,
        event: str,
        *,
        attempt: UUID | None = None,
        tool: UUID | None = None,
        error: str | None = None,
    ) -> None:
        # Serialize the sticky failure flag with writes, including fsync exceptions.
        with self._lock:
            self._append(event, attempt=attempt, tool=tool, error=error)

    def _append(
        self,
        event: str,
        *,
        attempt: UUID | None,
        tool: UUID | None,
        error: str | None,
    ) -> None:
        if self.failed:
            raise HarnessBlocked("Journal previously failed")
        try:
            with self.path.open("r+b") as stream:
                fcntl.flock(stream, fcntl.LOCK_EX)
                raw = stream.read(1)
                events = read_events(self.path) if raw else []
                if (self._opened and not events) or (not self._opened and events):
                    raise HarnessBlocked("Journal lifecycle was replaced")
                if len(events) != self._last_seq:
                    raise HarnessBlocked("Journal sequence changed outside its writer")
                if event == "case_open" and self._opened:
                    raise HarnessBlocked("Case already opened")
                if any(
                    item.case_id != self.case_id or item.executor_id != self.executor_id
                    for item in events
                ):
                    raise HarnessBlocked("Journal binding mismatch")
                if events and events[-1].event == "case_close":
                    raise HarnessBlocked("Closed case")
                value = Event.model_validate(
                    {
                        "case_id": self.case_id,
                        "executor_id": self.executor_id,
                        "seq": len(events) + 1,
                        "at": datetime.now(UTC),
                        "event": event,
                        "attempt_id": attempt,
                        "tool_call_id": tool,
                        "error": error,
                    }
                )
                stream.seek(0, os.SEEK_END)
                stream.write((value.model_dump_json() + "\n").encode())
                stream.flush()
                os.fsync(stream.fileno())
                self._opened = True
                self._last_seq = value.seq
        except (OSError, ValueError, HarnessBlocked) as exc:
            self.failed = True
            raise HarnessBlocked("Fixture journal write failed") from exc


@dataclass(frozen=True)
class Observation:
    verdict: Literal["pass", "fail", "unknown"]
    starts: dict[UUID, int]


def reconcile(
    root: Path,
    *,
    case_id: UUID,
    executors: frozenset[UUID],
    expected: dict[UUID, int],
    failed_executors: frozenset[UUID] = frozenset(),
) -> Observation:
    """Observation-only predicate, NOT an approval/run/persisted-state verdict."""
    counts: Counter[UUID] = Counter()
    complete = bool(executors) and not failed_executors
    attempts: set[UUID] = set()
    paths = {root / f"{executor}.jsonl" for executor in executors}
    if set(root.glob("*.jsonl")) != paths:
        complete = False
    for executor in executors:
        events, valid = _scan(root / f"{executor}.jsonl")
        complete = complete and valid
        pending: dict[UUID, tuple[UUID, str]] = {}
        opened, closed = False, False
        for event in events:
            if event.case_id != case_id or event.executor_id != executor:
                complete = False
                continue
            attempt, tool = event.attempt_id, event.tool_call_id
            # Retain observed violations even if lifecycle coverage is incomplete.
            if event.event == "dispatch_start" and attempt is not None and tool is not None:
                counts[tool] += 1
            if closed:
                complete = False
                continue
            if event.error is not None:
                complete = False
            if event.event in {"case_open", "case_close"}:
                if attempt is not None or tool is not None or event.error is not None:
                    complete = False
                if event.event == "case_open":
                    if opened or event.seq != 1:
                        complete = False
                    opened = True
                else:
                    closed = True
                continue
            if not opened or attempt is None or tool is None:
                complete = False
                continue
            if event.event == "dispatch_start":
                if attempt in attempts:
                    complete = False
                attempts.add(attempt)
                pending[attempt] = (tool, "started")
            elif event.event == "response_headers" and pending.get(attempt) == (tool, "started"):
                pending[attempt] = (tool, "headers")
            elif event.event == "response_validated" and pending.get(attempt) == (tool, "headers"):
                del pending[attempt]
            else:
                # Errors, duplicate completion, or headers without a start cannot prove success.
                complete = False
        complete = complete and opened and closed and not pending
    if any(count > expected.get(tool, 0) for tool, count in counts.items()):
        return Observation("fail", dict(counts))
    if not complete:
        return Observation("unknown", dict(counts))
    return Observation(
        "pass" if all(counts[t] == n for t, n in expected.items()) else "fail", dict(counts)
    )


@dataclass
class Budget:
    """Serial fixture ledger; not durable cross-process billing enforcement."""

    ceiling: Decimal = Decimal("1.25")
    task_limit: Decimal = Decimal("0.25")
    spent: Decimal = Decimal(0)
    tasks: dict[UUID, Decimal] = field(default_factory=dict)
    pending: dict[UUID, tuple[UUID, Decimal]] = field(default_factory=dict)
    used: set[UUID] = field(default_factory=set)
    attempts: Counter[UUID] = field(default_factory=Counter)
    blocked: bool = False

    def reserve(self, attempt: UUID, task: UUID, amount: Decimal) -> None:
        if (
            self.blocked
            or self.pending
            or attempt in self.used
            or not amount.is_finite()
            or amount <= 0
            or self.spent + amount > self.ceiling
            or (task not in self.attempts and len(self.attempts) >= 5)
            or self.attempts[task] >= 2
            or self.tasks.get(task, Decimal(0)) + amount > self.task_limit
        ):
            raise HarnessBlocked("Budget admission denied")
        self.used.add(attempt)
        self.attempts[task] += 1
        self.pending[attempt] = (task, amount)

    def settle(self, attempt: UUID, actual: Decimal | None) -> None:
        if self.blocked or attempt not in self.pending:
            raise HarnessBlocked("Unknown budget attempt")
        task, reserved = self.pending[attempt]
        if actual is None or not actual.is_finite() or actual < 0 or actual > reserved:
            self.blocked = True
            raise HarnessBlocked("Charges unresolved or above reservation")
        self.spent += actual
        self.tasks[task] = self.tasks.get(task, Decimal(0)) + actual
        del self.pending[attempt]

    def check_payload(self, body: bytes, *, approved_sha256: str, provider: str) -> None:
        if provider != "deepseek" or hashlib.sha256(body).hexdigest() != approved_sha256:
            self.blocked = True
            raise HarnessBlocked("Unapproved tool payload")


class FixturePool:
    """Synthetic pool ONLY; no callable live delegate or socket backend exists."""

    def __init__(
        self,
        journal: Journal,
        tool_call_id: UUID,
        *,
        body: bytes,
        status: int = 200,
        headers: list[tuple[bytes, bytes]] | None = None,
    ) -> None:
        if not isinstance(tool_call_id, UUID):
            raise HarnessBlocked("Missing trusted tool binding")
        self.journal, self.tool_call_id = journal, tool_call_id
        self.body, self.status = body, status
        self.headers = headers or [(b"content-type", b"application/json")]
        self.attempt: UUID | None = None
        self.delegations = 0

    async def handle_async_request(self, request: httpcore.Request) -> httpcore.Response:
        if (
            request.method != b"GET"
            or request.url.target
            != (
                b"/repos/royliu1105/agent-kernel/actions/runs/43634747295"
                b"?exclude_pull_requests=true"
            )
            or any(name.lower() in {b"authorization", b"cookie"} for name, _ in request.headers)
        ):
            raise HarnessBlocked("Unexpected fixture request")
        if self.attempt is not None:
            raise HarnessBlocked("Unfinished fixture attempt")
        self.attempt = uuid4()
        self.journal.append("dispatch_start", attempt=self.attempt, tool=self.tool_call_id)
        self.delegations += 1
        response = httpcore.Response(self.status, headers=self.headers, content=self.body)
        self.journal.append("response_headers", attempt=self.attempt, tool=self.tool_call_id)
        return response

    def validated(self, data: object) -> None:
        if self.attempt is None:
            raise HarnessBlocked("No dispatched attempt")
        if not isinstance(data, dict) or (
            data.get("id"),
            data.get("run_attempt"),
            data.get("head_sha"),
        ) != (43634747295, 1, "2bb3f4ab1d50afa1cc2686b42b1ebcaf5db1f726"):
            self.journal.append(
                "dispatch_error",
                attempt=self.attempt,
                tool=self.tool_call_id,
                error="identity_mismatch",
            )
            raise HarnessBlocked("Fixture identity mismatch")
        self.journal.append("response_validated", attempt=self.attempt, tool=self.tool_call_id)
        self.attempt = None

    async def aclose(self) -> None:
        pass
