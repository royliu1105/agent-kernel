"""Opt-in real SDK contract; install the documented optional exporter packages."""

import asyncio
import json

import pytest
from kernel_observability import trace_operation
from kernel_observability.operations import create_persisted_trace_id_generator
from kernel_observability.span_export import RedactingSpanExporter

Resource = pytest.importorskip("opentelemetry.sdk.resources").Resource
TracerProvider = pytest.importorskip("opentelemetry.sdk.trace").TracerProvider
SimpleSpanProcessor = pytest.importorskip("opentelemetry.sdk.trace.export").SimpleSpanProcessor
InMemorySpanExporter = pytest.importorskip(
    "opentelemetry.sdk.trace.export.in_memory_span_exporter"
).InMemorySpanExporter
trace = pytest.importorskip("opentelemetry.trace")
Link, SpanContext, Status, StatusCode = (
    trace.Link,
    trace.SpanContext,
    trace.Status,
    trace.StatusCode,
)


def test_real_sdk_export_redacts_span_events_links_resource_and_status() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider(
        resource=Resource({"service.name": "agent-kernel", "secret": "sentinel"})
    )
    provider.add_span_processor(SimpleSpanProcessor(RedactingSpanExporter(exporter)))
    tracer = provider.get_tracer("agent_kernel")
    link = Link(
        SpanContext(
            trace_id=123,
            span_id=456,
            is_remote=True,
            trace_state=trace.TraceState([("vendor", "sentinel")]),
        ),
        {"prompt": "sentinel"},
    )
    with tracer.start_as_current_span("llm.model_call", links=[link]) as span:
        span.set_attribute("prompt", "sentinel")
        span.set_attribute("provider.name", "mock")
        span.set_attribute("tokens.total", 12)
        span.set_attribute("authorization", "Bearer sentinel")
        span.add_event("tool.call", {"arguments": "sentinel", "tool.name": "echo"})
        span.record_exception(ValueError("sentinel"))
        span.set_status(Status(StatusCode.ERROR, "sentinel"))
    provider.force_flush()
    result = exporter.get_finished_spans()[0]
    assert "sentinel" not in result.to_json()
    assert result.attributes["tokens.total"] == 12
    assert result.attributes["provider.name"] == "mock"
    assert result.status.status_code == StatusCode.ERROR
    assert result.context.trace_id > 0
    assert result.links[0].context.trace_id == 123
    assert json.loads(result.to_json())["name"] == "llm.model_call"
    provider.shutdown()


def test_operation_spans_have_persisted_trace_and_real_parent_relationships() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider(id_generator=create_persisted_trace_id_generator())
    provider.add_span_processor(SimpleSpanProcessor(RedactingSpanExporter(exporter)))
    tracer = provider.get_tracer("kernel_observability")
    with trace_operation("agent.run", trace_id="a" * 32, tracer=tracer):
        with trace_operation(
            "llm.model_call",
            tracer=tracer,
            attributes={"model.name": "mock-small", "prompt": "sentinel"},
        ):
            pass
        with (
            pytest.raises(ValueError, match="sentinel"),
            trace_operation("tool.call", tracer=tracer),
        ):
            raise ValueError("sentinel")
    spans = {span.name: span for span in exporter.get_finished_spans()}
    assert spans["agent.run"].parent is None
    assert spans["agent.run"].context.trace_id == int("a" * 32, 16)
    for name in ("llm.model_call", "tool.call"):
        assert spans[name].parent.span_id == spans["agent.run"].context.span_id
        assert spans[name].context.trace_id == int("a" * 32, 16)
        assert "sentinel" not in spans[name].to_json()
    assert spans["tool.call"].status.status_code == StatusCode.ERROR
    provider.shutdown()


@pytest.mark.asyncio
async def test_concurrent_run_trace_contexts_do_not_leak() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider(id_generator=create_persisted_trace_id_generator())
    provider.add_span_processor(SimpleSpanProcessor(RedactingSpanExporter(exporter)))
    tracer = provider.get_tracer("kernel_observability")

    async def run(trace_id: str) -> None:
        with trace_operation("agent.run", trace_id=trace_id, tracer=tracer):
            await asyncio.sleep(0)
            with trace_operation("tool.call", tracer=tracer):
                await asyncio.sleep(0)

    await asyncio.gather(run("a" * 32), run("b" * 32))
    spans = exporter.get_finished_spans()
    for trace_id in (int("a" * 32, 16), int("b" * 32, 16)):
        group = {span.name: span for span in spans if span.context.trace_id == trace_id}
        assert len(group) == 2
        assert group["tool.call"].parent.span_id == group["agent.run"].context.span_id
    provider.shutdown()
