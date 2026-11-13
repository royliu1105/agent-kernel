"""Optional operation spans with persisted run trace IDs and safe attributes."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from importlib import import_module
from typing import Any

from kernel_observability.redaction import redact_fields, safe_event_name, safe_identifier
from kernel_observability.tracing import TRACE_ID_PATTERN

_PERSISTED_TRACE_ID: ContextVar[int | None] = ContextVar("persisted_trace_id", default=None)


def create_persisted_trace_id_generator() -> Any:
    """SDK factory used only when OTel is enabled; preserves normal random IDs."""
    random_generator = import_module("opentelemetry.sdk.trace.id_generator").RandomIdGenerator()

    class Generator:
        def generate_trace_id(self) -> int:
            value = _PERSISTED_TRACE_ID.get()
            return int(value if value is not None else random_generator.generate_trace_id())

        def generate_span_id(self) -> int:
            return int(random_generator.generate_span_id())

        def is_trace_id_random(self) -> bool:
            return _PERSISTED_TRACE_ID.get() is None

    return Generator()


@contextmanager
def trace_operation(
    name: str,
    *,
    trace_id: str | None = None,
    attributes: Mapping[str, object] | None = None,
    tracer: Any | None = None,
) -> Iterator[Any]:
    """Wrap sync or async work with ``with``; disabled by default and task-local.

    Supply persisted trace_id on the root run operation. Nested operations reuse
    the active span as parent. The optional tracer injection is for isolated SDK
    tests; production uses the provider configured at process startup.
    """
    from kernel_observability.otel import is_opentelemetry_configured

    if tracer is None and not is_opentelemetry_configured():
        yield None
        return
    trace = import_module("opentelemetry.trace")
    token = None
    context = None
    if trace_id is not None:
        if not TRACE_ID_PATTERN.fullmatch(trace_id) or int(trace_id, 16) == 0:
            # Invalid persisted correlation must not break an application run.
            yield None
            return
        value = int(trace_id, 16)
        token = _PERSISTED_TRACE_ID.set(value)
        current = trace.get_current_span().get_span_context()
        if current.is_valid and current.trace_id != value:
            context = trace.set_span_in_context(trace.INVALID_SPAN)
    resolved = tracer if tracer is not None else trace.get_tracer("kernel_observability")
    try:
        with resolved.start_as_current_span(
            safe_event_name(name),
            attributes=redact_fields(attributes or {}),
            context=context,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            try:
                yield span
            except Exception as error:
                category = safe_identifier(type(error).__name__)
                span.set_attribute("error.type", category)
                span.add_event("exception", {"exception.type": category})
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                raise
    finally:
        if token is not None:
            _PERSISTED_TRACE_ID.reset(token)
