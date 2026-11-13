from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
from kernel_providers import (
    LLMFinishReason,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    OpenAIProvider,
)

SPEC = importlib.util.spec_from_file_location(
    "live_provider_smoke", Path(__file__).parents[2] / "scripts/live_provider_smoke.py"
)
assert SPEC is not None and SPEC.loader is not None
smoke = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = smoke
SPEC.loader.exec_module(smoke)


class FakeProvider:
    name = "fixture"

    def __init__(self, *, delay: float = 0, error: bool = False, **changes: Any) -> None:
        self.calls: list[LLMRequest] = []
        self.delay = delay
        self.error = error
        self.response = LLMResponse(
            provider=self.name,
            model="small-snapshot",
            text="OK",
            usage=LLMUsage(input_tokens=10, output_tokens=2),
        ).model_copy(update=changes)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        await asyncio.sleep(self.delay)
        if self.error:
            raise RuntimeError("secret-key-do-not-print")
        return self.response


def enabled_env(**changes: str) -> dict[str, str]:
    return {
        smoke.ENABLE_ENV: "1",
        "OPENAI_API_KEY": "fixture-not-a-real-key",
        "AGENT_KERNEL_LIVE_MODEL": "small",
        "AGENT_KERNEL_LIVE_INPUT_USD_PER_MILLION": "1",
        "AGENT_KERNEL_LIVE_OUTPUT_USD_PER_MILLION": "2",
        **changes,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", ["", "true", "0"])
async def test_disabled_smoke_never_constructs_or_calls_provider(
    enabled: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(**_kwargs: object) -> None:
        raise AssertionError("Network provider must not be constructed.")

    monkeypatch.setattr(smoke, "OpenAIProvider", forbidden)
    report = await smoke.run_smoke(enabled_env(**{smoke.ENABLE_ENV: enabled}))
    assert report["status"] == "skipped"
    assert "measurement" not in report


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"OPENAI_API_KEY": ""}, "missing_api_key"),
        ({"AGENT_KERNEL_LIVE_MODEL": ""}, "invalid_config"),
        ({"AGENT_KERNEL_LIVE_OUTPUT_USD_PER_MILLION": ""}, "invalid_config"),
        ({"AGENT_KERNEL_LIVE_MAX_OUTPUT_TOKENS": "999"}, "invalid_config"),
        ({"AGENT_KERNEL_LIVE_TIMEOUT_SECONDS": "999"}, "invalid_config"),
        ({"AGENT_KERNEL_LIVE_INPUT_USD_PER_MILLION": "nan"}, "invalid_config"),
        ({"AGENT_KERNEL_LIVE_MAX_COST_USD": "1"}, "invalid_config"),
        ({"AGENT_KERNEL_LIVE_MAX_COST_USD": "0.000001"}, "budget_reservation_exceeded"),
    ],
)
async def test_invalid_or_overbudget_smoke_makes_no_requests(
    changes: dict[str, str],
    reason: str,
) -> None:
    provider = FakeProvider()
    report = await smoke.run_smoke(enabled_env(**changes), provider=provider)
    assert report["status"] == "invalid"
    assert report["reason"] == reason
    assert not provider.calls


@pytest.mark.asyncio
async def test_fake_smoke_records_actual_usage_not_default_zero_cost() -> None:
    provider = FakeProvider()
    report = await smoke.run_smoke(enabled_env(), provider=provider)
    assert report["status"] == "passed"
    assert len(provider.calls) == 1
    request = provider.calls[0]
    assert request.max_output_tokens == 32
    assert not request.tools
    assert request.messages[0].content == smoke.FIXED_PROMPT
    measured = report["measurement"]
    assert measured["sample_kind"] == "fixture"
    assert measured["estimated_cost_usd"] == pytest.approx(0.000014)
    assert measured["latency_ms"] >= 0
    assert "fixture-not-a-real-key" not in json.dumps(report)
    assert "text" not in measured


@pytest.mark.asyncio
async def test_real_adapter_with_fake_transport_respects_request_cap() -> None:
    requests = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "small-snapshot",
                "status": "completed",
                "output_text": "OK",
                "usage": {"input_tokens": 12, "output_tokens": 1},
            },
        )

    provider = OpenAIProvider(api_key="test-only", transport=httpx.MockTransport(respond))
    report = await smoke.run_smoke(enabled_env(), provider=provider)
    assert report["status"] == "passed"
    assert report["measurement"]["sample_kind"] == "fixture"
    assert len(requests) == 1
    assert requests[0]["max_output_tokens"] == 32


@pytest.mark.asyncio
async def test_timeout_does_not_retry() -> None:
    provider = FakeProvider(delay=1)
    report = await smoke.run_smoke(
        enabled_env(AGENT_KERNEL_LIVE_TIMEOUT_SECONDS="0.1"), provider=provider
    )
    assert report["reason"] == "timeout"
    assert len(provider.calls) == 1
    assert "measurement" not in report


@pytest.mark.asyncio
async def test_provider_error_does_not_leak_secrets() -> None:
    provider = FakeProvider(error=True)
    report = await smoke.run_smoke(enabled_env(), provider=provider)
    assert report["status"] == "failed"
    assert report["reason"] == "provider_error"
    assert "secret-key" not in json.dumps(report)
    assert len(provider.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"text": "unexpected private response"}, "output_mismatch"),
        ({"finish_reason": LLMFinishReason.LENGTH}, "incomplete_response"),
        ({"usage": LLMUsage()}, "missing_usage"),
        ({"usage": LLMUsage(input_tokens=2048, output_tokens=2)}, "budget_bound_exceeded"),
        ({"usage": LLMUsage(input_tokens=10, output_tokens=100)}, "budget_bound_exceeded"),
    ],
)
async def test_output_and_usage_failures_are_explicit(changes: dict[str, Any], reason: str) -> None:
    report = await smoke.run_smoke(enabled_env(), provider=FakeProvider(**changes))
    assert report["status"] == "failed"
    assert report["reason"] == reason
    assert "private response" not in json.dumps(report)


def test_cli_skip_and_offline_nonblocking_comparison(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv(smoke.ENABLE_ENV, raising=False)
    assert smoke.main([]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "skipped"
    report = asyncio.run(smoke.run_smoke(enabled_env(), provider=FakeProvider()))
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(json.dumps(report))
    report["measurement"]["latency_ms"] += 100
    current.write_text(json.dumps(report))
    assert smoke.main(["--compare", str(baseline), str(current)]) == 0
    trend = json.loads(capsys.readouterr().out)
    assert trend["comparable"]
    assert not trend["blocking"]
    assert trend["metrics"][1]["increased"]


def test_cli_rejects_failed_report_as_trend_baseline(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "skipped.json"
    path.write_text('{"schema_version": 1, "status": "skipped"}')
    assert smoke.main(["--compare", str(path), str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "invalid_report"
