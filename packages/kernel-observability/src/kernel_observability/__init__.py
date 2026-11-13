"""Observability primitives for Agent Kernel."""

from kernel_observability.aggregation import (
    METRIC_DEFINITIONS,
    PROMETHEUS_CONTENT_TYPE,
    AggregatingMetricsRecorder,
)
from kernel_observability.asgi import HttpMetricsMiddleware
from kernel_observability.http import MetricsHttpServer
from kernel_observability.logging import (
    JsonLogFormatter,
    build_log_fields,
    build_log_record,
    configure_safe_logging,
    log_event,
    redact_log_fields,
    uvicorn_log_config,
)
from kernel_observability.metrics import (
    ExposableMetricsRecorder,
    InMemoryMetricsRecorder,
    MetricPoint,
    MetricsRecorder,
    NoOpMetricsRecorder,
    normalize_labels,
    prometheus_text_from_points,
)
from kernel_observability.operations import trace_operation
from kernel_observability.otel import (
    DEFAULT_OTEL_ENDPOINT,
    DEFAULT_OTEL_EXPORTER,
    DEFAULT_OTEL_SERVICE_NAME,
    OTEL_ENABLED_ENV,
    OTEL_ENDPOINT_ENV,
    OTEL_EXPORTER_ENV,
    OTEL_SERVICE_NAME_ENV,
    OTEL_TRACES_ENDPOINT_ENV,
    SUPPORTED_OTEL_EXPORTERS,
    OpenTelemetryConfig,
    OpenTelemetryConfigurationError,
    OpenTelemetryConfigurationResult,
    configure_opentelemetry,
    load_otel_config,
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
    "HttpMetricsMiddleware",
    "trace_operation",
    "MetricsHttpServer",
    "AggregatingMetricsRecorder",
    "ExposableMetricsRecorder",
    "METRIC_DEFINITIONS",
    "PROMETHEUS_CONTENT_TYPE",
    "SPAN_ID_PATTERN",
    "TRACE_ID_PATTERN",
    "DEFAULT_OTEL_ENDPOINT",
    "DEFAULT_OTEL_EXPORTER",
    "DEFAULT_OTEL_SERVICE_NAME",
    "ObservabilityContext",
    "JsonLogFormatter",
    "InMemoryMetricsRecorder",
    "LatencyTimer",
    "MetricPoint",
    "MetricsRecorder",
    "NoOpMetricsRecorder",
    "OTEL_ENABLED_ENV",
    "OTEL_ENDPOINT_ENV",
    "OTEL_EXPORTER_ENV",
    "OTEL_SERVICE_NAME_ENV",
    "OTEL_TRACES_ENDPOINT_ENV",
    "OpenTelemetryConfig",
    "OpenTelemetryConfigurationError",
    "OpenTelemetryConfigurationResult",
    "SUPPORTED_OTEL_EXPORTERS",
    "build_log_fields",
    "build_log_record",
    "configure_opentelemetry",
    "configure_safe_logging",
    "uvicorn_log_config",
    "create_span_id",
    "create_trace_id",
    "ensure_span_id",
    "ensure_trace_id",
    "load_otel_config",
    "log_event",
    "normalize_labels",
    "prometheus_text_from_points",
    "redact_log_fields",
]
