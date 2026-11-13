"""Non-blocking cost/latency comparisons with explicit sample identity."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Measurement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    schema_version: Literal[1] = 1
    case_id: str = Field(min_length=1)
    request_fingerprint: str = Field(min_length=1)
    sample_kind: Literal["live", "fixture"]
    provider: str = Field(min_length=1)
    requested_model: str = Field(min_length=1)
    resolved_model: str = Field(min_length=1)
    input_tokens: int = Field(ge=0, strict=True)
    output_tokens: int = Field(ge=0, strict=True)
    input_usd_per_million: float = Field(gt=0)
    output_usd_per_million: float = Field(gt=0)
    estimated_cost_usd: float = Field(ge=0)
    latency_ms: float = Field(ge=0)


class MetricChange(BaseModel):
    name: str
    baseline: float
    current: float
    absolute_delta: float
    percent_delta: float | None
    increased: bool


class ComparisonReport(BaseModel):
    schema_version: Literal[1] = 1
    blocking: Literal[False] = False
    comparable: bool
    reasons: tuple[str, ...]
    metrics: tuple[MetricChange, ...] = ()
    interpretation: str = (
        "Single observations are noisy, not a statistical performance guarantee. "
        "Review trends over repeated equivalent live runs; fixture timings are local only."
    )


def compare_measurements(baseline: Measurement, current: Measurement) -> ComparisonReport:
    identity_fields = (
        "case_id",
        "request_fingerprint",
        "sample_kind",
        "provider",
        "requested_model",
        "resolved_model",
        "input_usd_per_million",
        "output_usd_per_million",
    )
    mismatches = tuple(
        f"{field} differs; these samples cannot support a like-for-like trend."
        for field in identity_fields
        if getattr(baseline, field) != getattr(current, field)
    )
    if mismatches:
        return ComparisonReport(comparable=False, reasons=mismatches)
    metrics = []
    for name in ("estimated_cost_usd", "latency_ms", "input_tokens", "output_tokens"):
        before = float(getattr(baseline, name))
        after = float(getattr(current, name))
        metrics.append(
            MetricChange(
                name=name,
                baseline=before,
                current=after,
                absolute_delta=after - before,
                percent_delta=((after - before) / before * 100 if before > 0 else None),
                increased=after > before,
            )
        )
    return ComparisonReport(comparable=True, reasons=(), metrics=tuple(metrics))
