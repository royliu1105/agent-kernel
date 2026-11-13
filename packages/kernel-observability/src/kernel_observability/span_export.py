"""Sanitize SDK spans at the exporter boundary, including automatic exceptions."""

from __future__ import annotations

from collections.abc import Sequence
from importlib import import_module
from typing import Any

from kernel_observability.redaction import redact_fields, safe_event_name, safe_identifier


def sanitized_span(span: Any) -> Any:
    """Build a new public ReadableSpan; never mutate shared SDK snapshots."""
    Resource = import_module("opentelemetry.sdk.resources").Resource
    trace_sdk = import_module("opentelemetry.sdk.trace")
    Event, ReadableSpan = trace_sdk.Event, trace_sdk.ReadableSpan
    InstrumentationScope = import_module(
        "opentelemetry.sdk.util.instrumentation"
    ).InstrumentationScope
    trace = import_module("opentelemetry.trace")
    Link, Status = trace.Link, trace.Status

    def clean_context(context: Any) -> Any:
        if context is None:
            return None
        return trace.SpanContext(
            trace_id=context.trace_id,
            span_id=context.span_id,
            is_remote=context.is_remote,
            trace_flags=context.trace_flags,
        )

    scope = span.instrumentation_scope
    return ReadableSpan(
        name=safe_event_name(span.name),
        context=clean_context(span.context),
        parent=clean_context(span.parent),
        resource=Resource(redact_fields(span.resource.attributes)),
        attributes=redact_fields(span.attributes or {}),
        events=tuple(
            Event(
                safe_event_name(event.name),
                attributes=redact_fields(event.attributes or {}),
                timestamp=event.timestamp,
            )
            for event in span.events[:64]
        ),
        links=tuple(
            Link(clean_context(link.context), attributes=redact_fields(link.attributes or {}))
            for link in span.links[:32]
        ),
        kind=span.kind,
        start_time=span.start_time,
        end_time=span.end_time,
        # Status descriptions and exception messages/stacktraces are arbitrary
        # content, so only the code and allowlisted event attributes survive.
        status=Status(span.status.status_code),
        instrumentation_scope=InstrumentationScope(safe_identifier(scope.name)) if scope else None,
    )


class RedactingSpanExporter:
    """Wrap every configured exporter, including the local console exporter."""

    def __init__(self, exporter: Any) -> None:
        self.exporter = exporter

    def export(self, spans: Sequence[Any]) -> Any:
        return self.exporter.export(tuple(sanitized_span(span) for span in spans))

    def shutdown(self) -> None:
        self.exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return bool(self.exporter.force_flush(timeout_millis=timeout_millis))
