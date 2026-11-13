import math
from concurrent.futures import ThreadPoolExecutor

import pytest
from kernel_observability import AggregatingMetricsRecorder, InMemoryMetricsRecorder


def test_aggregate_histogram_is_cumulative_and_does_not_retain_samples() -> None:
    recorder = AggregatingMetricsRecorder()
    for number in (0, 10, 11, 100_000):
        recorder.observe("tool_call_latency_ms", number, labels={"tool_name": "echo"})
    output = recorder.prometheus_text()
    base = 'error_type="none",status="none",tool_name="echo"'
    assert f'tool_call_duration_seconds_bucket{{{base},le="0.01"}} 2' in output
    assert f'tool_call_duration_seconds_bucket{{{base},le="0.025"}} 3' in output
    assert f'tool_call_duration_seconds_bucket{{{base},le="+Inf"}} 4' in output
    assert f"tool_call_duration_seconds_count{{{base}}} 4" in output
    assert f"tool_call_duration_seconds_sum{{{base}}} 100.021" in output
    assert recorder.series_count == 1


def test_aggregate_is_thread_safe_during_updates_and_scrapes() -> None:
    recorder = AggregatingMetricsRecorder()

    def record() -> None:
        for _ in range(1000):
            recorder.increment("tool_calls_total", labels={"status": "succeeded"})
            recorder.observe("tool_call_latency_ms", 5, labels={"status": "succeeded"})
        assert "# TYPE tool_calls_total counter" in recorder.prometheus_text()

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: record(), range(8)))
    assert 'tool_calls_total{error_type="none",status="succeeded",tool_name="none"} 8000' in (
        recorder.prometheus_text()
    )
    assert (
        'tool_call_duration_seconds_sum{error_type="none",status="succeeded",tool_name="none"}'
        " 40" in recorder.prometheus_text()
    )
    assert recorder.series_count == 2


def test_cardinality_and_name_limits_drop_without_leaking_values() -> None:
    recorder = AggregatingMetricsRecorder(max_series=3, max_label_values=2)
    for name in ("first", "second", "third"):
        recorder.increment("tool_calls_total", labels={"tool_name": name})
    recorder.increment("unknown_patient_record_123")
    recorder.increment("tool_calls_total", labels={"workspace_id": "private-tenant"})
    recorder.increment("tool_calls_total", labels={"tool_name": "sk-secrettoken"})
    recorder.increment("tool_calls_total", labels={"tool_name": "x" * 1000})
    text = recorder.prometheus_text()
    assert recorder.series_count == 2
    assert 'agent_kernel_metrics_dropped_total{reason="capacity"} 1' in text
    assert 'agent_kernel_metrics_dropped_total{reason="invalid_labels"} 3' in text
    assert "third" not in text and "private-tenant" not in text and "patient" not in text
    assert "secrettoken" not in text


def test_global_series_cap_is_independent_of_per_label_cap() -> None:
    recorder = AggregatingMetricsRecorder(max_series=1)
    recorder.increment("tool_calls_total")
    recorder.observe("tool_call_latency_ms", 1)
    assert recorder.series_count == 1
    assert 'agent_kernel_metrics_dropped_total{reason="capacity"} 1' in (recorder.prometheus_text())


def test_invalid_values_and_wrong_metric_types_do_not_break_execution() -> None:
    recorder = AggregatingMetricsRecorder()
    for value in (math.nan, math.inf, -1):
        recorder.increment("llm_tokens_total", value=value)
        recorder.observe("tool_call_latency_ms", value)
    recorder.observe("llm_tokens_total", 2)
    recorder.increment("tool_call_latency_ms")
    recorder.increment("llm_estimated_cost_total", value=1e308)
    recorder.increment("llm_estimated_cost_total", value=1e308)
    text = recorder.prometheus_text()
    assert 'agent_kernel_metrics_dropped_total{reason="invalid_value"} 7' in text
    assert 'agent_kernel_metrics_dropped_total{reason="invalid_metric"} 2' in text
    assert "nan" not in text.lower()


def test_type_lines_are_once_per_family_in_both_recorders() -> None:
    for recorder in (InMemoryMetricsRecorder(), AggregatingMetricsRecorder()):
        for name in ("echo", "kb_search"):
            recorder.increment("tool_calls_total", labels={"tool_name": name})
            recorder.observe("tool_call_latency_ms", 5, labels={"tool_name": name})
        output = recorder.prometheus_text()
        assert output.count("# TYPE tool_calls_total counter") == 1
        name = (
            "tool_call_latency_ms"
            if isinstance(recorder, InMemoryMetricsRecorder)
            else ("tool_call_duration_seconds")
        )
        assert output.count(f"# TYPE {name} ") == 1


@pytest.mark.parametrize("options", [{"max_series": 0}, {"max_label_values": 1000}])
def test_invalid_capacity_fails_configuration(options: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        AggregatingMetricsRecorder(**options)
