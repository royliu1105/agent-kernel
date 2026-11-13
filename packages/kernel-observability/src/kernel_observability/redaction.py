"""Fail-closed telemetry fields: identifiers/counts, never application content."""

from __future__ import annotations

import re
from collections.abc import Mapping
from math import isfinite

REDACTED = "[REDACTED]"
Scalar = str | int | float | bool
_IDENTIFIER = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:/-]{0,127}\Z", re.ASCII)
_EVENT_NAMES = frozenset(
    {
        "agent.run",
        "agent.step",
        "agent.run.started",
        "agent.run.failed",
        "agent.run.completed",
        "llm.model_call",
        "llm.model_call.retrying",
        "llm.model_call.completed",
        "llm.model_fallback.selected",
        "tool.call",
        "tool.call.requested",
        "tool.call.retrying",
        "tool.call.completed",
        "approval.requested",
        "approval.wait",
        "rag.retrieve",
        "memory.read",
        "memory.write",
        "policy.evaluate",
        "exception",
        "log.unstructured",
        "worker.run.claimed",
        "worker.run.completed",
        "worker.run.failed",
        "worker.lease.lost",
    }
)
_SECRET = re.compile(r"(?i)(?:sk-|gh[pousr]_|github_pat_|AKIA|ASIA|bearer|://.*@)")
_KEY = re.compile(r"[a-zA-Z][a-zA-Z0-9_.-]{0,95}\Z", re.ASCII)
_SAFE_TEXT = frozenset(
    {
        "trace_id",
        "span_id",
        "run_id",
        "agent_id",
        "step_id",
        "tool_call_id",
        "approval_id",
        "eval_run_id",
        "document_id",
        "workspace_id",
        "status",
        "provider",
        "model",
        "tool_name",
        "error_type",
        "exception_type",
        "risk_level",
        "decision",
        "reason_code",
        "step_type",
        "pricing_version",
        "service_name",
        "logger",
        "level",
        "fallback_model",
        "fallback_provider",
        "run.id",
        "agent.id",
        "step.id",
        "step.type",
        "step.status",
        "provider.name",
        "model.name",
        "tool.name",
        "tool.risk_level",
        "approval.id",
        "document.id",
        "eval_run.id",
        "error.type",
        "exception.type",
        "service.name",
        "service.version",
        "deployment.environment.name",
    }
)
_SAFE_NUMERIC = frozenset(
    {
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "estimated_cost",
        "latency_ms",
        "attempt",
        "max_attempts",
        "retry_delay_ms",
        "delay_ms",
        "result_count",
        "size_bytes",
        "duration_ms",
        "cost.estimated",
        "tokens.input",
        "tokens.output",
        "tokens.total",
        "requires_approval",
        "retryable",
        "fallback_index",
        "tool_count",
        "step_count",
    }
)


def safe_identifier(value: object) -> str:
    if isinstance(value, str) and _IDENTIFIER.fullmatch(value) and not _SECRET.search(value):
        return value
    return REDACTED


def safe_event_name(value: object) -> str:
    if isinstance(value, str) and value in _EVENT_NAMES:
        return value
    return REDACTED


def redact_fields(fields: Mapping[str, object]) -> dict[str, Scalar]:
    """Allow only audited scalar fields; containers/unknown fields are opaque.

    No repr/str calls on arbitrary objects, no recursive traversal, bounded
    output. Nested credential/content structures therefore cannot bypass the
    boundary, create cycles, or cause unbounded telemetry allocations.
    """
    result: dict[str, Scalar] = {}
    for index, (key, value) in enumerate(fields.items()):
        if index >= 64:
            break
        if (
            value is None
            or not isinstance(key, str)
            or not _KEY.fullmatch(key)
            or _SECRET.search(key)
        ):
            continue
        if key == "event":
            result[key] = safe_event_name(value)
        elif key in _SAFE_TEXT:
            result[key] = safe_identifier(value)
        elif key in _SAFE_NUMERIC and isinstance(value, (int, float, bool)):
            finite = value.bit_length() <= 63 if isinstance(value, int) else isfinite(value)
            result[key] = value if finite else REDACTED
        else:
            result[key] = REDACTED
    return result
