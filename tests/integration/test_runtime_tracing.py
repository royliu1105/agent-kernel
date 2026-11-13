"""Real SDK spans from runtime execution, not manually constructed trace fixtures."""

from functools import partial

import pytest
from kernel_observability.operations import create_persisted_trace_id_generator, trace_operation
from kernel_observability.span_export import RedactingSpanExporter
from kernel_runtime import execution
from test_timeline_regression import harness

TracerProvider = pytest.importorskip("opentelemetry.sdk.trace").TracerProvider
SimpleSpanProcessor = pytest.importorskip("opentelemetry.sdk.trace.export").SimpleSpanProcessor
InMemorySpanExporter = pytest.importorskip(
    "opentelemetry.sdk.trace.export.in_memory_span_exporter"
).InMemorySpanExporter


@pytest.mark.asyncio
async def test_native_runtime_exports_correlated_run_model_and_tool_spans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider(id_generator=create_persisted_trace_id_generator())
    provider.add_span_processor(SimpleSpanProcessor(RedactingSpanExporter(exporter)))
    monkeypatch.setattr(
        execution,
        "trace_operation",
        partial(trace_operation, tracer=provider.get_tracer("test")),
    )
    try:
        result = await harness.execute_scenario("native-tool")
        assert result.status == "succeeded"
        spans = exporter.get_finished_spans()
        root = next(span for span in spans if span.name == "agent.run")
        assert root.parent is None
        assert len(spans) == 4
        assert [span.name for span in spans].count("llm.model_call") == 2
        assert [span.name for span in spans].count("tool.call") == 1
        for span in spans:
            assert span.context.trace_id == root.context.trace_id
            if span is not root:
                assert span.parent.span_id == root.context.span_id
            assert "prompt" not in span.attributes
            assert "arguments" not in span.attributes
    finally:
        provider.shutdown()
