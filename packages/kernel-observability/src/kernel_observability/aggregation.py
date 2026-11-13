"""Bounded process-local metric aggregation; no per-observation storage."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from math import isfinite
from threading import Lock
from typing import Literal

from kernel_observability.metrics import (
    MetricKey,
    MetricLabels,
    _format_number,
    _prometheus_labels,
    normalize_labels,
)

PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"
LATENCY_BUCKETS_MS = (
    5.0,
    10.0,
    25.0,
    50.0,
    100.0,
    250.0,
    500.0,
    1000.0,
    2500.0,
    5000.0,
    10000.0,
    30000.0,
    60000.0,
)
RESULT_COUNT_BUCKETS = (0.0, 1.0, 3.0, 5.0, 10.0, 20.0, 50.0, 100.0)


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    kind: Literal["counter", "histogram"]
    help: str
    labels: tuple[str, ...]
    buckets: tuple[float, ...] = ()
    export_name: str | None = None
    scale: float = 1.0


_MODEL_LABELS = ("provider", "model", "status", "error_type")
_TOOL_LABELS = ("tool_name", "status", "error_type")
_RAG_LABELS = ("model", "status", "error_type")
METRIC_DEFINITIONS = (
    MetricDefinition(
        "run_queue_errors_total", "counter", "Redis queue operation failures.", ("operation",)
    ),
    MetricDefinition(
        "llm_model_calls_total", "counter", "Completed model call attempts.", _MODEL_LABELS
    ),
    MetricDefinition(
        "llm_model_call_latency_ms",
        "histogram",
        "Model attempt duration in seconds.",
        _MODEL_LABELS,
        LATENCY_BUCKETS_MS,
        "llm_model_call_duration_seconds",
        0.001,
    ),
    MetricDefinition(
        "llm_tokens_input_total", "counter", "Reported input tokens.", ("provider", "model")
    ),
    MetricDefinition(
        "llm_tokens_output_total", "counter", "Reported output tokens.", ("provider", "model")
    ),
    MetricDefinition(
        "llm_tokens_total", "counter", "Reported input plus output tokens.", ("provider", "model")
    ),
    MetricDefinition(
        "llm_estimated_cost_total", "counter", "Estimated model cost in USD.", ("provider", "model")
    ),
    MetricDefinition("tool_calls_total", "counter", "Completed tool calls.", _TOOL_LABELS),
    MetricDefinition("tool_call_failure_total", "counter", "Failed tool calls.", _TOOL_LABELS),
    MetricDefinition(
        "tool_call_latency_ms",
        "histogram",
        "Tool call duration in seconds.",
        _TOOL_LABELS,
        LATENCY_BUCKETS_MS,
        "tool_call_duration_seconds",
        0.001,
    ),
    MetricDefinition("rag_retrievals_total", "counter", "Completed retrievals.", _RAG_LABELS),
    MetricDefinition("rag_retrieval_failure_total", "counter", "Failed retrievals.", _RAG_LABELS),
    MetricDefinition(
        "rag_retrieval_latency_ms",
        "histogram",
        "Retrieval duration in seconds.",
        _RAG_LABELS,
        LATENCY_BUCKETS_MS,
        "rag_retrieval_duration_seconds",
        0.001,
    ),
    MetricDefinition(
        "rag_retrieval_result_count",
        "histogram",
        "Retrieved result count.",
        _RAG_LABELS,
        RESULT_COUNT_BUCKETS,
    ),
)
_DEFINITIONS = {definition.name: definition for definition in METRIC_DEFINITIONS}
_LABEL_VALUE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:/-]{0,95}\Z", re.ASCII)
_SECRET = re.compile(r"(?i)(?:sk-|gh[pousr]_|github_pat_|AKIA|ASIA|bearer|://.*@)")
_DROP_REASONS = ("invalid_metric", "invalid_value", "invalid_labels", "capacity")


@dataclass
class _Aggregate:
    value: float = 0.0
    count: int = 0
    buckets: list[int] = field(default_factory=list)


class AggregatingMetricsRecorder:
    """Thread-safe counters/histograms with a fixed registry and admission limits.

    Invalid observations are dropped, never raised into the application. The
    fixed diagnostic counter reports the reason without echoing rejected input.
    A series means one metric/label combination, not each histogram bucket.
    """

    def __init__(self, *, max_series: int = 1024, max_label_values: int = 32) -> None:
        if not 1 <= max_series <= 10000 or not 1 <= max_label_values <= 256:
            raise ValueError("Metric limits must be within 1..10000 series and 1..256 values.")
        self._max_series = max_series
        self._max_label_values = max_label_values
        self._series: dict[MetricKey, _Aggregate] = {}
        self._values: dict[str, set[str]] = {}
        self._dropped = dict.fromkeys(_DROP_REASONS, 0)
        self._lock = Lock()

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        labels: MetricLabels | None = None,
    ) -> None:
        self._record(name, value, labels, kind="counter")

    def observe(self, name: str, value: float, *, labels: MetricLabels | None = None) -> None:
        self._record(name, value, labels, kind="histogram")

    def _record(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None,
        *,
        kind: Literal["counter", "histogram"],
    ) -> None:
        with self._lock:
            definition = _DEFINITIONS.get(name)
            if definition is None or definition.kind != kind:
                self._dropped["invalid_metric"] += 1
                return
            if (
                not isinstance(value, (int, float))
                or (isinstance(value, int) and value.bit_length() > 1023)
                or not isfinite(value)
                or value < 0
            ):
                self._dropped["invalid_value"] += 1
                return
            labels = labels or {}
            if (
                not labels.keys() <= set(definition.labels)
                or any(
                    not isinstance(v, str) or not _LABEL_VALUE.fullmatch(v) or _SECRET.search(v)
                    for v in labels.values()
                )
                or labels.get("status", "succeeded") not in {"succeeded", "failed"}
                or ("operation" in labels and labels["operation"] not in {"enqueue", "dequeue"})
            ):
                self._dropped["invalid_labels"] += 1
                return
            normalized = normalize_labels(
                {key: labels.get(key, "none") for key in definition.labels}
            )
            key = (name, normalized)
            aggregate = self._series.get(key)
            if aggregate is None:
                if len(self._series) >= self._max_series or any(
                    v not in self._values.get(k, set())
                    and len(self._values.get(k, set())) >= self._max_label_values
                    for k, v in normalized
                ):
                    self._dropped["capacity"] += 1
                    return
                aggregate = _Aggregate(buckets=[0] * len(definition.buckets))
                self._series[key] = aggregate
                for k, v in normalized:
                    self._values.setdefault(k, set()).add(v)
            if not isfinite(aggregate.value + value):
                self._dropped["invalid_value"] += 1
                return
            aggregate.value += value
            if kind == "histogram":
                aggregate.count += 1
                for index, boundary in enumerate(definition.buckets):
                    if value <= boundary:
                        aggregate.buckets[index] += 1

    @property
    def series_count(self) -> int:
        with self._lock:
            return len(self._series)

    def prometheus_text(self) -> str:
        """Return a consistent snapshot; formatting happens outside the writer lock."""
        with self._lock:
            snapshot = tuple(
                (name, labels, value.value, value.count, tuple(value.buckets))
                for (name, labels), value in sorted(self._series.items())
            )
            dropped = tuple(sorted(self._dropped.items()))
        lines: list[str] = []
        emitted: set[str] = set()
        for name, labels, value, count, buckets in snapshot:
            definition = _DEFINITIONS[name]
            name = definition.export_name or name
            value *= definition.scale
            if name not in emitted:
                lines.extend(
                    (f"# HELP {name} {definition.help}", f"# TYPE {name} {definition.kind}")
                )
                emitted.add(name)
            if definition.kind == "counter":
                lines.append(f"{name}{_prometheus_labels(labels)} {_format_number(value)}")
                continue
            for boundary, bucket_count in zip(definition.buckets, buckets, strict=True):
                bucket_labels = (*labels, ("le", _format_number(boundary * definition.scale)))
                lines.append(f"{name}_bucket{_prometheus_labels(bucket_labels)} {bucket_count}")
            lines.append(f"{name}_bucket{_prometheus_labels((*labels, ('le', '+Inf')))} {count}")
            lines.append(f"{name}_count{_prometheus_labels(labels)} {count}")
            lines.append(f"{name}_sum{_prometheus_labels(labels)} {_format_number(value)}")
        diagnostic = "agent_kernel_metrics_dropped_total"
        lines.extend(
            (f"# HELP {diagnostic} Rejected metric updates.", f"# TYPE {diagnostic} counter")
        )
        lines.extend(f'{diagnostic}{{reason="{reason}"}} {count}' for reason, count in dropped)
        lines.extend(
            (
                "# HELP agent_kernel_metrics_series Active metric label combinations.",
                "# TYPE agent_kernel_metrics_series gauge",
                f"agent_kernel_metrics_series {len(snapshot)}",
            )
        )
        return "\n".join(lines) + "\n"
