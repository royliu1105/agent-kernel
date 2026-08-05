"""OpenTelemetry exporter configuration helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

OTEL_ENABLED_ENV = "AGENT_KERNEL_OTEL_ENABLED"
OTEL_SERVICE_NAME_ENV = "AGENT_KERNEL_OTEL_SERVICE_NAME"
OTEL_EXPORTER_ENV = "AGENT_KERNEL_OTEL_EXPORTER"
OTEL_ENDPOINT_ENV = "AGENT_KERNEL_OTEL_ENDPOINT"
OTEL_TRACES_ENDPOINT_ENV = "AGENT_KERNEL_OTEL_TRACES_ENDPOINT"

DEFAULT_OTEL_SERVICE_NAME = "agent-kernel"
DEFAULT_OTEL_EXPORTER = "otlp-http"
DEFAULT_OTEL_ENDPOINT = "http://localhost:4318"
SUPPORTED_OTEL_EXPORTERS = frozenset({"otlp-http", "console"})

_CONFIGURED = False


class OpenTelemetryConfigurationError(RuntimeError):
    """Raised when OpenTelemetry is enabled but cannot be configured."""


@dataclass(frozen=True)
class OpenTelemetryConfig:
    """Environment-driven OpenTelemetry exporter configuration."""

    enabled: bool = False
    service_name: str = DEFAULT_OTEL_SERVICE_NAME
    exporter: str = DEFAULT_OTEL_EXPORTER
    endpoint: str = DEFAULT_OTEL_ENDPOINT


@dataclass(frozen=True)
class OpenTelemetryConfigurationResult:
    """Result of attempting to configure OpenTelemetry tracing."""

    enabled: bool
    configured: bool
    service_name: str
    exporter: str | None
    endpoint: str | None
    reason: str | None = None


@dataclass(frozen=True)
class _OpenTelemetrySdk:
    trace_api: Any
    resource_class: Any
    tracer_provider_class: Any
    batch_span_processor_class: Any
    console_span_exporter_class: Any
    otlp_span_exporter_class: Any


def load_otel_config(env: Mapping[str, str] | None = None) -> OpenTelemetryConfig:
    """Load OpenTelemetry exporter settings from environment variables."""

    values = env or os.environ
    enabled = _parse_bool(values.get(OTEL_ENABLED_ENV))
    service_name = values.get(OTEL_SERVICE_NAME_ENV, DEFAULT_OTEL_SERVICE_NAME).strip()
    exporter = values.get(OTEL_EXPORTER_ENV, DEFAULT_OTEL_EXPORTER).strip().lower()
    endpoint = values.get(
        OTEL_TRACES_ENDPOINT_ENV,
        values.get(OTEL_ENDPOINT_ENV, DEFAULT_OTEL_ENDPOINT),
    ).strip()

    if not service_name:
        service_name = DEFAULT_OTEL_SERVICE_NAME
    if not exporter:
        exporter = DEFAULT_OTEL_EXPORTER
    if exporter not in SUPPORTED_OTEL_EXPORTERS:
        supported = ", ".join(sorted(SUPPORTED_OTEL_EXPORTERS))
        raise OpenTelemetryConfigurationError(
            f"{OTEL_EXPORTER_ENV} must be one of: {supported}."
        )
    if not endpoint:
        endpoint = DEFAULT_OTEL_ENDPOINT

    return OpenTelemetryConfig(
        enabled=enabled,
        service_name=service_name,
        exporter=exporter,
        endpoint=endpoint,
    )


def configure_opentelemetry(
    config: OpenTelemetryConfig | None = None,
) -> OpenTelemetryConfigurationResult:
    """Configure OpenTelemetry tracing once for the current process."""

    global _CONFIGURED

    resolved = config or load_otel_config()
    if not resolved.enabled:
        return OpenTelemetryConfigurationResult(
            enabled=False,
            configured=False,
            service_name=resolved.service_name,
            exporter=None,
            endpoint=None,
            reason="disabled",
        )
    if _CONFIGURED:
        return OpenTelemetryConfigurationResult(
            enabled=True,
            configured=False,
            service_name=resolved.service_name,
            exporter=resolved.exporter,
            endpoint=resolved.endpoint,
            reason="already_configured",
        )

    sdk = _import_otel_sdk()
    resource = sdk.resource_class.create({"service.name": resolved.service_name})
    provider = sdk.tracer_provider_class(resource=resource)
    exporter = _create_span_exporter(config=resolved, sdk=sdk)
    provider.add_span_processor(sdk.batch_span_processor_class(exporter))
    sdk.trace_api.set_tracer_provider(provider)
    _CONFIGURED = True

    return OpenTelemetryConfigurationResult(
        enabled=True,
        configured=True,
        service_name=resolved.service_name,
        exporter=resolved.exporter,
        endpoint=resolved.endpoint,
    )


def reset_opentelemetry_configuration_for_tests() -> None:
    """Reset process-local OpenTelemetry configuration guard for tests."""

    global _CONFIGURED
    _CONFIGURED = False


def _parse_bool(value: str | None) -> bool:
    if value is None or value.strip() == "":
        return False
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise OpenTelemetryConfigurationError(f"{OTEL_ENABLED_ENV} must be a boolean value.")


def _create_span_exporter(*, config: OpenTelemetryConfig, sdk: _OpenTelemetrySdk) -> Any:
    if config.exporter == "console":
        return sdk.console_span_exporter_class()
    if config.exporter == "otlp-http":
        return sdk.otlp_span_exporter_class(endpoint=_traces_endpoint(config.endpoint))
    supported = ", ".join(sorted(SUPPORTED_OTEL_EXPORTERS))
    raise OpenTelemetryConfigurationError(f"{OTEL_EXPORTER_ENV} must be one of: {supported}.")


def _traces_endpoint(endpoint: str) -> str:
    normalized = endpoint.rstrip("/")
    if normalized.endswith("/v1/traces"):
        return normalized
    return f"{normalized}/v1/traces"


def _import_otel_sdk() -> _OpenTelemetrySdk:
    try:
        from opentelemetry import trace as trace_api  # type: ignore[import-not-found]
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import-not-found]
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource  # type: ignore[import-not-found]
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-not-found]
        from opentelemetry.sdk.trace.export import (  # type: ignore[import-not-found]
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
    except ImportError as error:
        raise OpenTelemetryConfigurationError(
            "OpenTelemetry is enabled but required packages are not installed. "
            "Install opentelemetry-sdk and opentelemetry-exporter-otlp-proto-http "
            "in the deployment image."
        ) from error

    return _OpenTelemetrySdk(
        trace_api=trace_api,
        resource_class=Resource,
        tracer_provider_class=TracerProvider,
        batch_span_processor_class=BatchSpanProcessor,
        console_span_exporter_class=ConsoleSpanExporter,
        otlp_span_exporter_class=OTLPSpanExporter,
    )
