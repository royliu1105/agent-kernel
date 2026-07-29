"""Observability primitives for Agent Kernel."""

from kernel_observability.logging import (
    JsonLogFormatter,
    build_log_fields,
    build_log_record,
    log_event,
    redact_log_fields,
)
from kernel_observability.metrics import (
    InMemoryMetricsRecorder,
    MetricPoint,
    MetricsRecorder,
    NoOpMetricsRecorder,
    normalize_labels,
)
from kernel_observability.timing import LatencyTimer
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
    "JsonLogFormatter",
    "InMemoryMetricsRecorder",
    "LatencyTimer",
    "MetricPoint",
    "MetricsRecorder",
    "NoOpMetricsRecorder",
    "build_log_fields",
    "build_log_record",
    "create_span_id",
    "create_trace_id",
    "ensure_span_id",
    "ensure_trace_id",
    "log_event",
    "normalize_labels",
    "redact_log_fields",
]
