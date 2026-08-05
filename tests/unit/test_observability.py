import json
import logging
from typing import Any, cast
from uuid import uuid4

import pytest
from kernel_observability import (
    SPAN_ID_PATTERN,
    TRACE_ID_PATTERN,
    InMemoryMetricsRecorder,
    JsonLogFormatter,
    LatencyTimer,
    ObservabilityContext,
    OpenTelemetryConfig,
    OpenTelemetryConfigurationError,
    build_log_fields,
    build_log_record,
    configure_opentelemetry,
    create_span_id,
    create_trace_id,
    ensure_span_id,
    ensure_trace_id,
    load_otel_config,
    log_event,
    normalize_labels,
    redact_log_fields,
)
from kernel_observability import otel as otel_module


def test_trace_and_span_ids_use_otel_compatible_hex_shapes() -> None:
    trace_id = create_trace_id()
    span_id = create_span_id()

    assert TRACE_ID_PATTERN.fullmatch(trace_id)
    assert SPAN_ID_PATTERN.fullmatch(span_id)


def test_ensure_trace_id_validates_explicit_values() -> None:
    trace_id = "a" * 32

    assert ensure_trace_id(trace_id) == trace_id
    with pytest.raises(ValueError, match="trace_id"):
        ensure_trace_id("not-a-trace")


def test_ensure_span_id_validates_explicit_values() -> None:
    span_id = "b" * 16

    assert ensure_span_id(span_id) == span_id
    with pytest.raises(ValueError, match="span_id"):
        ensure_span_id("not-a-span")


def test_observability_context_returns_non_empty_log_fields() -> None:
    run_id = uuid4()
    agent_id = uuid4()
    context = ObservabilityContext.create(
        trace_id="c" * 32,
        run_id=run_id,
        agent_id=agent_id,
    )

    assert context.to_log_fields() == {
        "trace_id": "c" * 32,
        "run_id": str(run_id),
        "agent_id": str(agent_id),
    }


def test_observability_context_child_span_keeps_trace_id() -> None:
    context = ObservabilityContext.create(trace_id="d" * 32)
    child = context.child_span(span_id="e" * 16)

    assert child.trace_id == context.trace_id
    assert child.span_id == "e" * 16


def test_build_log_fields_adds_safe_runtime_fields() -> None:
    context = ObservabilityContext.create(trace_id="f" * 32, span_id="1" * 16)

    fields = build_log_fields(
        context,
        status="succeeded",
        provider="mock",
        model="mock-small",
        tool_name=None,
        extra={"attempt": 2, "ignored": None},
    )

    assert fields == {
        "trace_id": "f" * 32,
        "span_id": "1" * 16,
        "status": "succeeded",
        "provider": "mock",
        "model": "mock-small",
        "attempt": 2,
    }


def test_log_field_redaction_removes_sensitive_values() -> None:
    redacted = redact_log_fields(
        {
            "trace_id": "a" * 32,
            "api_key": "sk-secret",
            "auth_token": "token-value",
            "password": "p@ss",
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "empty": None,
        }
    )

    assert redacted == {
        "trace_id": "a" * 32,
        "api_key": "[REDACTED]",
        "auth_token": "[REDACTED]",
        "password": "[REDACTED]",
        "input_tokens": 10,
        "output_tokens": 5,
        "total_tokens": 15,
    }


def test_build_log_record_adds_event_name() -> None:
    context = ObservabilityContext.create(trace_id="a" * 32)

    record = build_log_record(
        event="agent.run.started",
        context=context,
        status="running",
    )

    assert record == {
        "event": "agent.run.started",
        "trace_id": "a" * 32,
        "status": "running",
    }


def test_json_log_formatter_outputs_parseable_json() -> None:
    formatter = JsonLogFormatter()
    log_record = logging.LogRecord(
        name="agent_kernel.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="agent.run.started",
        args=(),
        exc_info=None,
    )
    cast(Any, log_record).structured = {
        "event": "agent.run.started",
        "trace_id": "b" * 32,
        "status": "running",
    }

    payload = json.loads(formatter.format(log_record))

    assert payload["event"] == "agent.run.started"
    assert payload["level"] == "info"
    assert payload["logger"] == "agent_kernel.test"
    assert payload["trace_id"] == "b" * 32
    assert payload["status"] == "running"
    assert "timestamp" in payload


def test_log_event_emits_structured_extra(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("agent_kernel.test")
    context = ObservabilityContext.create(trace_id="c" * 32)

    with caplog.at_level(logging.INFO, logger="agent_kernel.test"):
        log_event(
            logger,
            level=logging.INFO,
            event="agent.run.started",
            context=context,
            status="running",
        )

    assert caplog.records[0].message == "agent.run.started"
    assert cast(Any, caplog.records[0]).structured == {
        "event": "agent.run.started",
        "trace_id": "c" * 32,
        "status": "running",
    }


def test_latency_timer_reports_non_negative_milliseconds() -> None:
    timer = LatencyTimer.start()

    assert timer.elapsed_ms() >= 0


def test_in_memory_metrics_recorder_tracks_counters_and_observations() -> None:
    recorder = InMemoryMetricsRecorder()

    recorder.increment("tool_calls_total", labels={"tool_name": "echo", "status": "succeeded"})
    recorder.increment(
        "tool_calls_total",
        value=2,
        labels={"status": "succeeded", "tool_name": "echo"},
    )
    recorder.observe(
        "tool_call_latency_ms",
        12,
        labels={"tool_name": "echo", "status": "succeeded"},
    )

    labels = {"tool_name": "echo", "status": "succeeded"}
    assert recorder.counter_value("tool_calls_total", labels=labels) == 3
    assert recorder.observations("tool_call_latency_ms", labels=labels) == (12,)
    assert recorder.counter_points()[0].value == 3
    assert recorder.observation_points()[0].value == 12


def test_normalize_labels_returns_stable_sorted_label_key() -> None:
    assert normalize_labels({"b": "2", "a": "1"}) == (("a", "1"), ("b", "2"))


def test_load_otel_config_defaults_to_disabled() -> None:
    config = load_otel_config({})

    assert config == OpenTelemetryConfig(
        enabled=False,
        service_name="agent-kernel",
        exporter="otlp-http",
        endpoint="http://localhost:4318",
    )


def test_load_otel_config_parses_exporter_environment() -> None:
    config = load_otel_config(
        {
            "AGENT_KERNEL_OTEL_ENABLED": "true",
            "AGENT_KERNEL_OTEL_SERVICE_NAME": "agent-kernel-api",
            "AGENT_KERNEL_OTEL_EXPORTER": "console",
            "AGENT_KERNEL_OTEL_ENDPOINT": "http://collector:4318",
        }
    )

    assert config == OpenTelemetryConfig(
        enabled=True,
        service_name="agent-kernel-api",
        exporter="console",
        endpoint="http://collector:4318",
    )


def test_load_otel_config_rejects_invalid_values() -> None:
    with pytest.raises(OpenTelemetryConfigurationError, match="boolean"):
        load_otel_config({"AGENT_KERNEL_OTEL_ENABLED": "sometimes"})
    with pytest.raises(OpenTelemetryConfigurationError, match="AGENT_KERNEL_OTEL_EXPORTER"):
        load_otel_config({"AGENT_KERNEL_OTEL_EXPORTER": "zipkin"})


def test_configure_opentelemetry_is_noop_when_disabled() -> None:
    otel_module.reset_opentelemetry_configuration_for_tests()

    result = configure_opentelemetry(OpenTelemetryConfig(enabled=False))

    assert result.enabled is False
    assert result.configured is False
    assert result.reason == "disabled"


def test_configure_opentelemetry_wires_otlp_http_exporter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    otel_module.reset_opentelemetry_configuration_for_tests()
    trace_api = _FakeTraceApi()

    monkeypatch.setattr(
        otel_module,
        "_import_otel_sdk",
        lambda: otel_module._OpenTelemetrySdk(
            trace_api=trace_api,
            resource_class=_FakeResource,
            tracer_provider_class=_FakeTracerProvider,
            batch_span_processor_class=_FakeBatchSpanProcessor,
            console_span_exporter_class=_FakeConsoleSpanExporter,
            otlp_span_exporter_class=_FakeOtlpSpanExporter,
        ),
    )

    result = configure_opentelemetry(
        OpenTelemetryConfig(
            enabled=True,
            service_name="agent-kernel-api",
            exporter="otlp-http",
            endpoint="http://collector:4318",
        )
    )

    assert result.enabled is True
    assert result.configured is True
    assert result.service_name == "agent-kernel-api"
    assert isinstance(trace_api.provider, _FakeTracerProvider)
    assert trace_api.provider.resource == {"service.name": "agent-kernel-api"}
    processor = trace_api.provider.processors[0]
    assert isinstance(processor.exporter, _FakeOtlpSpanExporter)
    assert processor.exporter.endpoint == "http://collector:4318/v1/traces"

    second = configure_opentelemetry(OpenTelemetryConfig(enabled=True))
    assert second.configured is False
    assert second.reason == "already_configured"


def test_configure_opentelemetry_reports_missing_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    otel_module.reset_opentelemetry_configuration_for_tests()

    def raise_missing_sdk() -> object:
        raise OpenTelemetryConfigurationError("missing sdk")

    monkeypatch.setattr(otel_module, "_import_otel_sdk", raise_missing_sdk)

    with pytest.raises(OpenTelemetryConfigurationError, match="missing sdk"):
        configure_opentelemetry(OpenTelemetryConfig(enabled=True))


class _FakeTraceApi:
    def __init__(self) -> None:
        self.provider: _FakeTracerProvider | None = None

    def set_tracer_provider(self, provider: object) -> None:
        assert isinstance(provider, _FakeTracerProvider)
        self.provider = provider


class _FakeResource:
    @classmethod
    def create(cls, attributes: dict[str, str]) -> dict[str, str]:
        return attributes


class _FakeTracerProvider:
    def __init__(self, *, resource: dict[str, str]) -> None:
        self.resource = resource
        self.processors: list[_FakeBatchSpanProcessor] = []

    def add_span_processor(self, processor: object) -> None:
        assert isinstance(processor, _FakeBatchSpanProcessor)
        self.processors.append(processor)


class _FakeBatchSpanProcessor:
    def __init__(self, exporter: object) -> None:
        self.exporter = exporter


class _FakeConsoleSpanExporter:
    pass


class _FakeOtlpSpanExporter:
    def __init__(self, *, endpoint: str) -> None:
        self.endpoint = endpoint
