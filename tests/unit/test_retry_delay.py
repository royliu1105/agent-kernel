import math
import sys
from dataclasses import FrozenInstanceError
from typing import cast

import pytest
from kernel_runtime.retry import RetryDelayPolicy


@pytest.mark.parametrize("field", ["base_seconds", "max_seconds"])
def test_retry_delay_defaults_are_frozen(field: str) -> None:
    policy = RetryDelayPolicy()
    assert policy.base_seconds == 0.25
    assert policy.max_seconds == 30.0
    with pytest.raises(FrozenInstanceError):
        setattr(policy, field, 1.0)


@pytest.mark.parametrize(
    ("attempt", "window"),
    [
        (1, 0.25),
        (2, 0.5),
        (3, 1.0),
        (7, 16.0),
        (8, 30.0),
        (1000, 30.0),
        pytest.param(10**1000, 30.0, id="enormous-attempt"),
    ],
)
@pytest.mark.parametrize("random_value", [0.0, 0.25, 0.5, 1.0])
def test_retry_delay_is_full_jitter_after_capping(
    attempt: int, window: float, random_value: float
) -> None:
    assert RetryDelayPolicy().delay(attempt, random_value=random_value) == window * random_value


def test_retry_delay_uses_default_random_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("kernel_runtime.retry.random.random", lambda: 0.75)
    assert RetryDelayPolicy().delay(2) == 0.375


@pytest.mark.parametrize(
    ("hint", "expected"),
    [(0.0, 0.125), (0.05, 0.125), (0.5, 0.5), (30.0, 30.0), (30.01, None), (1e308, None)],
)
def test_retry_delay_respects_hint_floor_or_refuses(hint: float, expected: float | None) -> None:
    assert RetryDelayPolicy().delay(1, retry_after_seconds=hint, random_value=0.5) == expected


def test_retry_delay_refusal_does_not_consume_randomness(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_random() -> float:
        pytest.fail("A refused retry must not need a jitter sample.")

    monkeypatch.setattr("kernel_runtime.retry.random.random", unexpected_random)
    assert RetryDelayPolicy().delay(1, retry_after_seconds=31) is None


@pytest.mark.parametrize(
    "value",
    [
        None,
        -1.0,
        float("nan"),
        float("inf"),
        -float("inf"),
        True,
        False,
        "10",
        [],
        pytest.param(10**1000, id="unrepresentable-integer"),
    ],
)
def test_retry_delay_ignores_invalid_hints(value: object) -> None:
    assert RetryDelayPolicy().delay(1, cast(float, value), 0.5) == 0.125


@pytest.mark.parametrize("field", ["base_seconds", "max_seconds"])
@pytest.mark.parametrize(
    "value",
    [
        None,
        -0.01,
        float("nan"),
        float("inf"),
        -float("inf"),
        True,
        False,
        "1",
        [],
        pytest.param(10**1000, id="unrepresentable-integer"),
    ],
)
def test_retry_delay_rejects_invalid_configuration(field: str, value: object) -> None:
    with pytest.raises(ValueError, match=field):
        RetryDelayPolicy(**{field: cast(float, value)})


def test_retry_delay_rejects_base_above_cap() -> None:
    with pytest.raises(ValueError, match="base_seconds must not exceed max_seconds"):
        RetryDelayPolicy(base_seconds=1, max_seconds=0.5)


@pytest.mark.parametrize("attempt", [0, -1, 1.5, float("nan"), float("inf"), True, "1", None])
def test_retry_delay_rejects_invalid_attempt(attempt: object) -> None:
    with pytest.raises(ValueError, match="attempt"):
        RetryDelayPolicy().delay(cast(int, attempt), random_value=0.5)


@pytest.mark.parametrize(
    "value",
    [
        -0.01,
        1.01,
        float("nan"),
        float("inf"),
        -float("inf"),
        True,
        False,
        "0.5",
        [],
        pytest.param(10**1000, id="unrepresentable-integer"),
    ],
)
def test_retry_delay_rejects_invalid_jitter(value: object) -> None:
    with pytest.raises(ValueError, match="random_value"):
        RetryDelayPolicy().delay(1, random_value=cast(float, value))


def test_retry_delay_zero_base_still_honors_server_hint() -> None:
    policy = RetryDelayPolicy(base_seconds=0)
    assert policy.delay(10**1000, random_value=1) == 0.0
    assert policy.delay(1, retry_after_seconds=2, random_value=0) == 2.0
    policy = RetryDelayPolicy(base_seconds=0, max_seconds=0)
    assert policy.delay(1, retry_after_seconds=0, random_value=1) == 0.0
    assert policy.delay(1, retry_after_seconds=0.01, random_value=0) is None


def test_retry_delay_handles_extreme_finite_bounds_without_overflow() -> None:
    smallest = math.ulp(0.0)
    largest = sys.float_info.max
    policy = RetryDelayPolicy(base_seconds=smallest, max_seconds=largest)
    assert policy.delay(1, random_value=1) == smallest
    assert policy.delay(1075, random_value=1) == 1.0
    assert policy.delay(2098, random_value=1) == math.ldexp(1.0, 1023)
    assert policy.delay(2099, random_value=1) == largest
    assert policy.delay(10**1000, random_value=0.5) == largest * 0.5
    assert RetryDelayPolicy(largest, largest).delay(2, random_value=1) == largest
    assert RetryDelayPolicy(smallest, smallest * 2).delay(3, random_value=1) == smallest * 2


def test_retry_delay_preserves_fractional_custom_cap() -> None:
    policy = RetryDelayPolicy(base_seconds=0.3, max_seconds=0.7)
    assert policy.delay(1, random_value=1) == 0.3
    assert policy.delay(2, random_value=1) == 0.6
    assert policy.delay(3, random_value=1) == 0.7
