"""Fixture-only cross-process admission and provider transport integration.

No live transport, environment setup or runtime bootstrap is exposed here.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field

from scripts.pv1_harness import HarnessBlocked, Observation, reconcile


class Attempt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    executor: UUID
    task: UUID
    kind: Literal["generation", "embedding"]
    reserved: Decimal
    complete: bool = False


class State(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_class: Literal["fixture"] = "fixture"
    case_id: UUID
    binding: str = Field(pattern=r"^[0-9a-f]{64}$")
    seq: int = Field(ge=1)
    initialized: bool = False
    executors: dict[UUID, Literal["api", "worker"]] = Field(default_factory=dict)
    attempts: dict[UUID, Attempt] = Field(default_factory=dict)
    closed: bool = False


class FixtureLedger:
    """Append-only snapshots under flock; uncertain attempts retain their reserve.

    Successful fixture calls also consume their entire reservation. This is a
    conservative admission bound, NOT measured spend or provider billing proof.
    """

    def __init__(self, path: Path, case_id: UUID, binding: str) -> None:
        self.path, self.case_id, self.binding = path, case_id, binding

    def create(self) -> None:
        state = State(case_id=self.case_id, binding=self.binding, seq=1)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                stream.write((state.model_dump_json() + "\n").encode())
                stream.flush()
                os.fsync(stream.fileno())
                directory = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
                state.initialized, state.seq = True, 2
                stream.write((state.model_dump_json() + "\n").encode())
                stream.flush()
                os.fsync(stream.fileno())
            except OSError as exc:
                stream.write(b"!uncertain\n")
                stream.flush()
                raise HarnessBlocked("Ledger initialization failed") from exc

    def _read(self, raw: bytes) -> State:
        if not raw or len(raw) > 2_097_152 or not raw.endswith(b"\n"):
            raise HarnessBlocked("Missing, oversized or torn ledger")
        try:
            states = [State.model_validate_json(line) for line in raw.splitlines()]
        except ValueError as exc:
            raise HarnessBlocked("Invalid ledger") from exc
        for seq, state in enumerate(states, 1):
            if (state.seq, state.case_id, state.binding) != (seq, self.case_id, self.binding):
                raise HarnessBlocked("Ledger binding or sequence mismatch")
        if not states[-1].initialized:
            raise HarnessBlocked("Ledger initialization incomplete")
        return states[-1]

    def snapshot(self) -> State:
        with self.path.open("rb") as stream:
            fcntl.flock(stream, fcntl.LOCK_SH)
            return self._read(stream.read(2_097_153))

    def observation(
        self,
        journals: Path,
        expected: dict[UUID, int],
        *,
        failed_executors: frozenset[UUID] = frozenset(),
    ) -> Observation:
        state = self.snapshot()
        result = reconcile(
            journals,
            case_id=self.case_id,
            executors=frozenset(state.executors),
            expected=expected,
            failed_executors=failed_executors,
        )
        if result.verdict == "pass" and (
            not state.closed or any(not item.complete for item in state.attempts.values())
        ):
            return Observation("unknown", result.starts)
        return result

    def change(
        self,
        operation: Literal["register", "reserve", "complete", "close"],
        *,
        executor: UUID,
        role: Literal["api", "worker"] = "worker",
        attestation: str = "",
        attempt: UUID | None = None,
        task: UUID | None = None,
        kind: Literal["generation", "embedding"] = "generation",
        amount: Decimal = Decimal("0.125"),
    ) -> None:
        with self.path.open("r+b") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            state = self._read(stream.read(2_097_153))
            if state.closed:
                raise HarnessBlocked("Closed ledger")
            if operation == "register":
                if attestation != self.binding or executor in state.executors:
                    raise HarnessBlocked("Executor attestation denied")
                state.executors[executor] = role
            elif executor not in state.executors:
                raise HarnessBlocked("Unregistered executor")
            elif operation == "reserve":
                if attempt is None or task is None or attempt in state.attempts:
                    raise HarnessBlocked("Missing or reused attempt binding")
                if any(not item.complete for item in state.attempts.values()):
                    raise HarnessBlocked("Unresolved prior attempt")
                items = list(state.attempts.values())
                generation = [item for item in items if item.kind == "generation"]
                same_task = [item for item in items if item.task == task]
                tasks = {item.task for item in generation}
                cap = Decimal("1.25") if kind == "generation" else Decimal("0.10")
                subtotal = sum((item.reserved for item in items if item.kind == kind), Decimal(0))
                if (
                    not amount.is_finite()
                    or amount <= 0
                    or subtotal + amount > cap
                    or sum((item.reserved for item in same_task), Decimal(0)) + amount
                    > Decimal("0.25")
                    or (kind == "generation" and task not in tasks and len(tasks) >= 5)
                    or (kind == "generation" and sum(item.kind == kind for item in same_task) >= 2)
                ):
                    raise HarnessBlocked("Reservation exceeds frozen allocation")
                state.attempts[attempt] = Attempt(
                    executor=executor, task=task, kind=kind, reserved=amount
                )
            elif operation == "complete":
                if attempt not in state.attempts:
                    raise HarnessBlocked("Unknown attempt")
                item = state.attempts[attempt]
                if item.executor != executor or item.complete:
                    raise HarnessBlocked("Completion ownership mismatch")
                item.complete = True
            elif operation == "close":
                if any(not item.complete for item in state.attempts.values()):
                    raise HarnessBlocked("Cannot close uncertain window")
                state.closed = True
            state.seq += 1
            payload = (state.model_dump_json() + "\n").encode()
            if stream.tell() + len(payload) > 2_097_152:
                raise HarnessBlocked("Ledger capacity reached")
            try:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            except OSError as exc:
                # Leave a detectable corrupt tail even if failed fsync bytes are visible.
                stream.write(b"!uncertain\n")
                stream.flush()
                raise HarnessBlocked("Ledger durability failure") from exc


class FixtureAdmissionTransport(httpx.BaseTransport, httpx.AsyncBaseTransport):
    """Exact serialized request allowlist in front of an HTTPX MockTransport only."""

    def __init__(
        self,
        ledger: FixtureLedger,
        executor: UUID,
        task: UUID,
        *,
        kind: Literal["generation", "embedding"],
        url: str,
        approved_requests: frozenset[str],
        response: dict[str, object],
        status: int = 200,
    ) -> None:
        self.ledger, self.executor, self.task = ledger, executor, task
        self.kind, self.url, self.approved_requests = kind, url, approved_requests
        self.dispatches = 0
        self._mock = httpx.MockTransport(lambda _: httpx.Response(status, json=response))

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        digest = hashlib.sha256(request.content).hexdigest()
        if (
            request.method != "POST"
            or str(request.url) != self.url
            or digest not in self.approved_requests
        ):
            raise HarnessBlocked("Unapproved effective request")
        attempt = uuid4()
        self.ledger.change(
            "reserve",
            executor=self.executor,
            attempt=attempt,
            task=self.task,
            kind=self.kind,
            amount=Decimal("0.125") if self.kind == "generation" else Decimal("0.10"),
        )
        self.dispatches += 1
        response = self._mock.handle_request(request)
        response.read()
        if response.status_code != 200:
            raise HarnessBlocked("Uncertain fixture charge; stop without retry")
        try:
            body = response.json()
            usage = body["usage"]
            fields = (
                ("input_tokens", "output_tokens")
                if self.kind == "generation"
                else ("total_tokens",)
            )
            if any(type(usage[name]) is not int or usage[name] < 0 for name in fields):
                raise ValueError("Invalid usage")
            limits = {"input_tokens": 16000, "output_tokens": 1024, "total_tokens": 50000}
            if any(usage[name] > limits[name] for name in fields):
                raise ValueError("Usage exceeds fixture envelope")
        except (KeyError, TypeError, ValueError) as exc:
            raise HarnessBlocked("Unknown fixture usage") from exc
        self.ledger.change("complete", executor=self.executor, attempt=attempt)
        return response

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return self.handle_request(request)


def request_hash(payload: dict[str, object]) -> str:
    """Hash HTTPX's actual JSON encoding, not a differently canonicalized payload."""
    request = httpx.Request("POST", "https://fixture.invalid", json=payload)
    return hashlib.sha256(request.content).hexdigest()
