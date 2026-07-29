"""Latency measurement helpers."""

from __future__ import annotations

from time import monotonic


class LatencyTimer:
    """Measure elapsed wall-clock time with a monotonic clock."""

    def __init__(self) -> None:
        self._started_at = monotonic()

    @classmethod
    def start(cls) -> LatencyTimer:
        """Start a new latency timer."""

        return cls()

    def elapsed_ms(self) -> int:
        """Return elapsed time in integer milliseconds."""

        return max(0, round((monotonic() - self._started_at) * 1000))
