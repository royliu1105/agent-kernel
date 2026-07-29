from uuid import uuid4

import pytest
from kernel_observability import (
    SPAN_ID_PATTERN,
    TRACE_ID_PATTERN,
    ObservabilityContext,
    build_log_fields,
    create_span_id,
    create_trace_id,
    ensure_span_id,
    ensure_trace_id,
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
