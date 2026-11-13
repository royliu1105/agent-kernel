"""Opt-in, single-request live provider smoke and offline measurement comparison."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from time import perf_counter
from typing import Any

from kernel_evals.comparison import Measurement, compare_measurements
from kernel_providers import (
    LLMFinishReason,
    LLMMessage,
    LLMProvider,
    LLMRequest,
    MessageRole,
    OpenAIProvider,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError

ENABLE_ENV = "AGENT_KERNEL_LIVE_SMOKE"
CASE_ID = "single-turn-ok-v1"
INPUT_TOKEN_RESERVATION = 1024
FIXED_PROMPT = "Reply with exactly OK."


class SmokeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    model: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:-]+$")
    max_output_tokens: int = Field(default=32, ge=16, le=128)
    timeout_seconds: float = Field(default=20.0, ge=0.1, le=60)
    max_cost_usd: float = Field(default=0.01, gt=0, le=0.10)
    input_usd_per_million: float = Field(gt=0)
    output_usd_per_million: float = Field(gt=0)

    @property
    def reserved_cost_usd(self) -> float:
        return (
            INPUT_TOKEN_RESERVATION * self.input_usd_per_million
            + self.max_output_tokens * self.output_usd_per_million
        ) / 1_000_000

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> SmokeConfig:
        return cls.model_validate(
            {
                "model": env.get("AGENT_KERNEL_LIVE_MODEL", ""),
                "max_output_tokens": env.get("AGENT_KERNEL_LIVE_MAX_OUTPUT_TOKENS", "32"),
                "timeout_seconds": env.get("AGENT_KERNEL_LIVE_TIMEOUT_SECONDS", "20"),
                "max_cost_usd": env.get("AGENT_KERNEL_LIVE_MAX_COST_USD", "0.01"),
                "input_usd_per_million": env.get("AGENT_KERNEL_LIVE_INPUT_USD_PER_MILLION"),
                "output_usd_per_million": env.get("AGENT_KERNEL_LIVE_OUTPUT_USD_PER_MILLION"),
            }
        )


async def run_smoke(
    env: Mapping[str, str], *, provider: LLMProvider | None = None
) -> dict[str, Any]:
    """Injected providers are labeled fixtures and never constitute live evidence."""
    if env.get(ENABLE_ENV) != "1":
        return _report("skipped", "not_enabled", f"Set {ENABLE_ENV}=1 to opt in.")
    if not env.get("OPENAI_API_KEY", "").strip():
        return _report("invalid", "missing_api_key", "OPENAI_API_KEY is required.")
    try:
        config = SmokeConfig.from_env(env)
    except ValidationError:
        return _report(
            "invalid",
            "invalid_config",
            "Provide a model and positive current input/output USD-per-million rates; "
            "output tokens must be 16..128, timeout 0.1..60s and budget 0..0.10 USD.",
        )
    if config.reserved_cost_usd > config.max_cost_usd:
        return _report(
            "invalid",
            "budget_reservation_exceeded",
            "Input reservation plus capped output exceeds the budget at the supplied rates; "
            "no request was made.",
        )
    injected = provider is not None
    selected = provider or OpenAIProvider(
        api_key=env["OPENAI_API_KEY"], timeout=config.timeout_seconds
    )
    request = LLMRequest(
        model=config.model,
        messages=(LLMMessage(role=MessageRole.USER, content=FIXED_PROMPT),),
        max_output_tokens=config.max_output_tokens,
    )
    started = perf_counter()
    try:
        response = await asyncio.wait_for(
            selected.complete(request), timeout=config.timeout_seconds
        )
    except TimeoutError:
        return _report(
            "failed",
            "timeout",
            "One attempt timed out; no retry was made. Provider-side billing may still occur.",
        )
    except Exception as error:
        report = _report(
            "failed",
            "provider_error",
            "The single provider attempt failed; exception text and response body are omitted.",
        )
        report["exception_type"] = type(error).__name__
        return report
    latency_ms = (perf_counter() - started) * 1000
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    if input_tokens <= 0 or output_tokens <= 0:
        return _report(
            "failed",
            "missing_usage",
            "Positive input/output usage was not returned; unknown cost is not reported as zero.",
        )
    estimated_cost = (
        input_tokens * config.input_usd_per_million + output_tokens * config.output_usd_per_million
    ) / 1_000_000
    measurement = Measurement(
        case_id=CASE_ID,
        request_fingerprint=hashlib.sha256(
            json.dumps(request.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest(),
        sample_kind="fixture" if injected else "live",
        provider=selected.name,
        requested_model=config.model,
        resolved_model=response.model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_usd_per_million=config.input_usd_per_million,
        output_usd_per_million=config.output_usd_per_million,
        estimated_cost_usd=estimated_cost,
        latency_ms=latency_ms,
    )
    if (
        input_tokens > INPUT_TOKEN_RESERVATION
        or output_tokens > config.max_output_tokens
        or estimated_cost > config.max_cost_usd
    ):
        report = _report(
            "failed",
            "budget_bound_exceeded",
            "Provider usage exceeded the admitted bounds; stop and inspect billing. "
            "A client cannot undo cost already incurred.",
        )
    elif response.finish_reason is not LLMFinishReason.STOP or response.tool_calls:
        report = _report("failed", "incomplete_response", "Expected a completed text-only answer.")
    elif response.text.strip() != "OK":
        report = _report("failed", "output_mismatch", "Expected the fixed OK response.")
    else:
        report = _report("passed", "completed", "One bounded text-only completion succeeded.")
    report["measurement"] = measurement.model_dump(mode="json")
    report["limits"] = {
        "attempts": 1,
        "input_token_reservation": INPUT_TOKEN_RESERVATION,
        "max_output_tokens": config.max_output_tokens,
        "timeout_seconds": config.timeout_seconds,
        "reserved_cost_usd": config.reserved_cost_usd,
        "max_cost_usd": config.max_cost_usd,
        "pricing_source": "operator-supplied upper-bound rates; not a provider invoice",
    }
    return report


def _report(status: str, reason: str, message: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": status,
        "reason": reason,
        "message": message,
        "blocking_by_default": False,
    }


def load_measurement(path: Path) -> Measurement:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("status") != "passed":
        raise ValueError("Trend input must be a passed smoke report, not a skipped/failed sample.")
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported smoke report schema version.")
    return Measurement.model_validate(data.get("measurement"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--compare",
        nargs=2,
        type=Path,
        metavar=("BASELINE", "CURRENT"),
        help="Compare two reports offline, without enabling live requests.",
    )
    args = parser.parse_args(argv)
    if args.compare:
        try:
            baseline, current = (load_measurement(path) for path in args.compare)
            trend = compare_measurements(baseline, current)
        except (OSError, ValueError) as error:
            print(json.dumps(_report("invalid", "invalid_report", type(error).__name__)))
            return 2
        print(trend.model_dump_json(indent=2))
        return 0
    report = asyncio.run(run_smoke(os.environ))
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] == "invalid":
        return 2
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
