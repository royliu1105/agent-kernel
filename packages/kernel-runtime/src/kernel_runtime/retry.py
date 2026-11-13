"""Pure, bounded retry-delay calculation; callers own waiting and retry eligibility."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


def _finite_nonnegative(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return max(0.0, number) if math.isfinite(number) and number >= 0 else None


@dataclass(frozen=True)
class RetryDelayPolicy:
    """Full jitter with finite bounds satisfying 0 <= base_seconds <= max_seconds."""

    base_seconds: float = 0.25
    max_seconds: float = 30.0

    def __post_init__(self) -> None:
        for name in ("base_seconds", "max_seconds"):
            value = _finite_nonnegative(getattr(self, name))
            if value is None:
                raise ValueError(f"{name} must be a finite non-negative number.")
            object.__setattr__(self, name, value)
        if self.base_seconds > self.max_seconds:
            raise ValueError("base_seconds must not exceed max_seconds.")

    def delay(
        self,
        attempt: int,
        retry_after_seconds: float | None = None,
        random_value: float | None = None,
    ) -> float | None:
        """Delay after a one-based failed attempt, or None to refuse a server hint.

        Invalid hints are ignored. A valid hint above max_seconds refuses retry
        instead of truncating the server's minimum wait. Invalid attempts or
        jitter samples (outside [0, 1]) raise ValueError.
        """
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
            raise ValueError("attempt must be a positive integer.")
        hint = _finite_nonnegative(retry_after_seconds)
        if hint is not None and hint > self.max_seconds:
            return None
        jitter = _finite_nonnegative(random.random() if random_value is None else random_value)
        if jitter is None or jitter > 1:
            raise ValueError("random_value must be a finite number between 0 and 1.")

        window = self.base_seconds
        if window > 0:
            exponent = attempt - 1
            # Compare exponents before scaling, even for enormous attempt integers
            # or a subnormal base; never construct 2**attempt or overflow a float.
            max_exponent = math.frexp(self.max_seconds)[1] - math.frexp(window)[1]
            window = (
                self.max_seconds
                if exponent > max_exponent
                else min(self.max_seconds, math.ldexp(window, exponent))
            )
        return max(hint or 0.0, window * jitter)
