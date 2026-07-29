"""Trace and span correlation primitives."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID, uuid4

TRACE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
SPAN_ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")


def create_trace_id() -> str:
    """Create an OpenTelemetry-compatible 32-character lowercase hex trace ID."""

    return uuid4().hex


def create_span_id() -> str:
    """Create an OpenTelemetry-compatible 16-character lowercase hex span ID."""

    return uuid4().hex[:16]


def ensure_trace_id(trace_id: str | None = None) -> str:
    """Return a valid trace ID, generating one when no trace ID is provided."""

    if trace_id is None:
        return create_trace_id()
    if not TRACE_ID_PATTERN.fullmatch(trace_id):
        raise ValueError("trace_id must be a 32-character lowercase hex string.")
    return trace_id


def ensure_span_id(span_id: str | None = None) -> str:
    """Return a valid span ID, generating one when no span ID is provided."""

    if span_id is None:
        return create_span_id()
    if not SPAN_ID_PATTERN.fullmatch(span_id):
        raise ValueError("span_id must be a 16-character lowercase hex string.")
    return span_id


@dataclass(frozen=True)
class ObservabilityContext:
    """Correlation fields that can be attached to logs, spans, and events."""

    trace_id: str
    span_id: str | None = None
    run_id: UUID | None = None
    agent_id: UUID | None = None
    step_id: UUID | None = None
    tool_call_id: UUID | None = None
    approval_id: UUID | None = None
    eval_run_id: UUID | None = None

    @classmethod
    def create(
        cls,
        *,
        trace_id: str | None = None,
        span_id: str | None = None,
        run_id: UUID | None = None,
        agent_id: UUID | None = None,
        step_id: UUID | None = None,
        tool_call_id: UUID | None = None,
        approval_id: UUID | None = None,
        eval_run_id: UUID | None = None,
    ) -> ObservabilityContext:
        """Create a validated observability context."""

        return cls(
            trace_id=ensure_trace_id(trace_id),
            span_id=ensure_span_id(span_id) if span_id is not None else None,
            run_id=run_id,
            agent_id=agent_id,
            step_id=step_id,
            tool_call_id=tool_call_id,
            approval_id=approval_id,
            eval_run_id=eval_run_id,
        )

    def child_span(self, *, span_id: str | None = None) -> ObservabilityContext:
        """Create a child context with the same trace ID and a new span ID."""

        return ObservabilityContext(
            trace_id=self.trace_id,
            span_id=ensure_span_id(span_id),
            run_id=self.run_id,
            agent_id=self.agent_id,
            step_id=self.step_id,
            tool_call_id=self.tool_call_id,
            approval_id=self.approval_id,
            eval_run_id=self.eval_run_id,
        )

    def to_log_fields(self) -> dict[str, str]:
        """Return non-empty correlation fields as string values."""

        fields: dict[str, str] = {"trace_id": self.trace_id}
        if self.span_id is not None:
            fields["span_id"] = self.span_id
        if self.run_id is not None:
            fields["run_id"] = str(self.run_id)
        if self.agent_id is not None:
            fields["agent_id"] = str(self.agent_id)
        if self.step_id is not None:
            fields["step_id"] = str(self.step_id)
        if self.tool_call_id is not None:
            fields["tool_call_id"] = str(self.tool_call_id)
        if self.approval_id is not None:
            fields["approval_id"] = str(self.approval_id)
        if self.eval_run_id is not None:
            fields["eval_run_id"] = str(self.eval_run_id)
        return fields
