"""Observability primitives for Agent Kernel."""

from kernel_observability.logging import build_log_fields
from kernel_observability.tracing import (
    SPAN_ID_PATTERN,
    TRACE_ID_PATTERN,
    ObservabilityContext,
    create_span_id,
    create_trace_id,
    ensure_span_id,
    ensure_trace_id,
)

__all__ = [
    "SPAN_ID_PATTERN",
    "TRACE_ID_PATTERN",
    "ObservabilityContext",
    "build_log_fields",
    "create_span_id",
    "create_trace_id",
    "ensure_span_id",
    "ensure_trace_id",
]
