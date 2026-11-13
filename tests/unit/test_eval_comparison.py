from __future__ import annotations

import pytest
from kernel_evals.comparison import Measurement, compare_measurements
from pydantic import ValidationError


def measurement(**changes: object) -> Measurement:
    values: dict[str, object] = {
        "case_id": "case-v1",
        "request_fingerprint": "request-v1",
        "sample_kind": "fixture",
        "provider": "fake",
        "requested_model": "small",
        "resolved_model": "small-2026",
        "input_tokens": 10,
        "output_tokens": 2,
        "input_usd_per_million": 1.0,
        "output_usd_per_million": 2.0,
        "estimated_cost_usd": 0.000014,
        "latency_ms": 10.0,
    }
    return Measurement.model_validate({**values, **changes})


def test_comparison_reports_nonblocking_increases_and_zero_baselines() -> None:
    report = compare_measurements(
        measurement(latency_ms=0), measurement(latency_ms=20, estimated_cost_usd=0.000028)
    )
    assert report.comparable
    assert not report.blocking
    costs, latency, *_ = report.metrics
    assert costs.percent_delta == pytest.approx(100)
    assert costs.increased
    assert latency.absolute_delta == 20
    assert latency.percent_delta is None
    assert "not a statistical" in report.interpretation


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("case_id", "other-case"),
        ("request_fingerprint", "changed-tokens"),
        ("sample_kind", "live"),
        ("provider", "other"),
        ("requested_model", "large"),
        ("resolved_model", "small-new-snapshot"),
        ("input_usd_per_million", 9),
        ("output_usd_per_million", 9),
    ],
)
def test_mismatched_samples_are_not_compared(field: str, value: object) -> None:
    report = compare_measurements(measurement(), measurement(**{field: value}))
    assert not report.comparable
    assert not report.metrics
    assert field in report.reasons[0]
    assert not report.blocking


@pytest.mark.parametrize(
    "changes", [{"latency_ms": float("nan")}, {"estimated_cost_usd": -1}, {"input_tokens": True}]
)
def test_invalid_measurements_fail_validation(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        measurement(**changes)
