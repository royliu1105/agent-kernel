"""Small metrics recorder abstractions."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
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


def normalize_labels(labels: MetricLabels | None = None) -> MetricLabelKey:
    """Return labels as a stable sorted tuple."""

    if labels is None:
        return ()
    return tuple(sorted(labels.items()))
