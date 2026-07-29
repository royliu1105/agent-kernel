import json
import logging
from typing import Any, cast
from uuid import uuid4

import pytest
from kernel_observability import (
    SPAN_ID_PATTERN,
    TRACE_ID_PATTERN,
    JsonLogFormatter,
    ObservabilityContext,
    build_log_fields,
    build_log_record,
    create_span_id,
    create_trace_id,
    ensure_span_id,
    ensure_trace_id,
    log_event,
    redact_log_fields,
)


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
