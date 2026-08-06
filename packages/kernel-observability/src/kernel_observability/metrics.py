"""Small metrics recorder abstractions."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Protocol

MetricLabels = Mapping[str, str]
MetricLabelKey = tuple[tuple[str, str], ...]
MetricKey = tuple[str, MetricLabelKey]


class MetricsRecorder(Protocol):
    """Interface for low-cardinality counters and observations."""

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        labels: MetricLabels | None = None,
    ) -> None:
        """Increment a counter metric."""

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: MetricLabels | None = None,
    ) -> None:
        """Record an observed numeric value."""


@dataclass(frozen=True)
class MetricPoint:
    """One metric value and its normalized label set."""

    name: str
    value: float
    labels: MetricLabelKey


class NoOpMetricsRecorder:
    """Metrics recorder that intentionally drops all data."""

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        labels: MetricLabels | None = None,
    ) -> None:
        _ = (name, value, labels)

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: MetricLabels | None = None,
    ) -> None:
        _ = (name, value, labels)


class InMemoryMetricsRecorder:
    """Test-friendly in-process metrics recorder."""

    def __init__(self) -> None:
        self._counters: defaultdict[MetricKey, float] = defaultdict(float)
        self._observations: defaultdict[MetricKey, list[float]] = defaultdict(list)

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        labels: MetricLabels | None = None,
    ) -> None:
        self._counters[(name, normalize_labels(labels))] += value

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: MetricLabels | None = None,
    ) -> None:
        self._observations[(name, normalize_labels(labels))].append(value)

    def counter_value(self, name: str, *, labels: MetricLabels | None = None) -> float:
        """Return one counter value."""

        return self._counters[(name, normalize_labels(labels))]

    def observations(self, name: str, *, labels: MetricLabels | None = None) -> tuple[float, ...]:
        """Return observations for one metric and label set."""

        return tuple(self._observations[(name, normalize_labels(labels))])

    def counter_points(self) -> tuple[MetricPoint, ...]:
        """Return all counter metric points."""

        return tuple(
            MetricPoint(name=name, labels=labels, value=value)
            for (name, labels), value in sorted(self._counters.items())
        )

    def observation_points(self) -> tuple[MetricPoint, ...]:
        """Return all observed metric points."""

        return tuple(
            MetricPoint(name=name, labels=labels, value=value)
            for (name, labels), values in sorted(self._observations.items())
            for value in values
        )

    def prometheus_text(self) -> str:
        """Return metrics in Prometheus text exposition format."""

        return prometheus_text_from_points(
            counter_points=self.counter_points(),
            observation_points=self.observation_points(),
        )


def normalize_labels(labels: MetricLabels | None = None) -> MetricLabelKey:
    """Return labels as a stable sorted tuple."""

    if labels is None:
        return ()
    return tuple(sorted(labels.items()))


def prometheus_text_from_points(
    *,
    counter_points: tuple[MetricPoint, ...],
    observation_points: tuple[MetricPoint, ...],
) -> str:
    """Render counters and observations as Prometheus text exposition."""

    lines: list[str] = []
    for point in counter_points:
        metric_name = _prometheus_metric_name(point.name)
        lines.append(f"# TYPE {metric_name} counter")
        lines.append(
            f"{metric_name}{_prometheus_labels(point.labels)} {_format_number(point.value)}"
        )

    grouped_observations: defaultdict[tuple[str, MetricLabelKey], list[float]] = defaultdict(list)
    for point in observation_points:
        grouped_observations[(point.name, point.labels)].append(point.value)

    for (name, labels), values in sorted(grouped_observations.items()):
        metric_name = _prometheus_metric_name(name)
        label_text = _prometheus_labels(labels)
        finite_values = [value for value in values if isfinite(value)]
        lines.append(f"# TYPE {metric_name} summary")
        lines.append(f"{metric_name}_count{label_text} {len(finite_values)}")
        lines.append(f"{metric_name}_sum{label_text} {_format_number(sum(finite_values))}")

    return "\n".join(lines) + "\n"


def _prometheus_metric_name(name: str) -> str:
    sanitized = "".join(
        character if character.isalnum() or character in "_:" else "_" for character in name
    )
    if sanitized == "":
        return "agent_kernel_metric"
    if sanitized[0].isdigit():
        return f"_{sanitized}"
    return sanitized


def _prometheus_labels(labels: MetricLabelKey) -> str:
    if not labels:
        return ""
    values = ",".join(
        f'{_prometheus_label_name(key)}="{_escape_label_value(value)}"'
        for key, value in labels
    )
    return f"{{{values}}}"


def _prometheus_label_name(name: str) -> str:
    sanitized = "".join(
        character if character.isalnum() or character == "_" else "_" for character in name
    )
    if sanitized == "":
        return "label"
    if sanitized[0].isdigit():
        return f"_{sanitized}"
    return sanitized


def _escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_number(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return repr(value)
