from datetime import UTC, datetime
from typing import cast

import httpx
import pytest
from kernel_providers import LLMProviderError, LLMRequest, OpenAIProvider


async def _status_error(
    headers: dict[str, str] | list[tuple[str, str]],
    *,
    status_code: int = 429,
    error_code: str = "rate_limit_exceeded",
) -> LLMProviderError:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.headers["authorization"] == "Bearer secret-test-api-key"
        return httpx.Response(
            status_code,
            headers=headers,
            json={"error": {"code": error_code, "message": "secret-response-body"}},
        )

    provider = OpenAIProvider(
        api_key="secret-test-api-key",
        base_url="https://api.test",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(LLMProviderError) as raised:
        await provider.complete(LLMRequest(model="fixture", messages=()))
    assert calls == 1
    assert str(raised.value) == f"OpenAI API returned {status_code}."
    assert "secret" not in repr(raised.value)
    return raised.value


@pytest.mark.parametrize(
    ("hint", "expected"),
    [(None, None), (0.0, 0.0), (-0.0, 0.0), (0.25, 0.25), (2, 2.0), (1e308, 1e308)],
)
def test_provider_error_retains_only_sanitized_hint(
    hint: float | None, expected: float | None
) -> None:
    error = LLMProviderError("safe message", error_type="rate_limit", retry_after_seconds=hint)
    assert error.retry_after_seconds == expected
    assert error.error_type == "rate_limit"
    assert error.args == ("safe message",)
    if expected is not None:
        assert isinstance(error.retry_after_seconds, float)


@pytest.mark.parametrize(
    "hint",
    [
        -0.5,
        float("nan"),
        float("inf"),
        -float("inf"),
        True,
        False,
        "secret-header-value",
        [],
        pytest.param(10**1000, id="unrepresentable-integer"),
    ],
)
def test_provider_error_discards_invalid_hint(hint: object) -> None:
    error = LLMProviderError("safe message", retry_after_seconds=cast(float, hint))
    assert error.retry_after_seconds is None
    assert error.args == ("safe message",)
    assert error.error_type == "provider_error"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("0", 0.0),
        ("2", 2.0),
        ("0002", 2.0),
        (" \t12\t ", 12.0),
        ("31", 31.0),
        pytest.param("1" + "0" * 308, 1e308, id="large-finite-hint"),
    ],
)
async def test_openai_retry_after_delta_seconds(header: str, expected: float) -> None:
    error = await _status_error({"rEtRy-AfTeR": header})
    assert error.retry_after_seconds == expected
    assert error.error_type == "rate_limit"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("Tue, 01 Jan 2030 00:00:10 GMT", 10.0),
        ("Tuesday, 01-Jan-30 00:00:10 GMT", 10.0),
        ("Tue Jan  1 00:00:10 2030", 10.0),
        ("Tue, 01 Jan 2030 00:00:00 GMT", 0.0),
        ("Mon, 31 Dec 2029 23:59:59 GMT", 0.0),
        ("Tue, 01 Jan 2030 00:01:00 GMT", 60.0),
    ],
)
async def test_openai_retry_after_http_date(
    header: str, expected: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2030, 1, 1, tzinfo=UTC).timestamp()
    monkeypatch.setattr("kernel_providers.openai.time", lambda: now)
    error = await _status_error({"Retry-After": header}, status_code=503)
    assert error.retry_after_seconds == expected
    assert error.error_type == "provider_unavailable"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("header", "target_year"),
    [
        ("Tuesday, 01-Jan-69 00:00:00 GMT", 2069),
        ("Tuesday, 01-Jan-80 00:00:00 GMT", 2080),
        ("Tuesday, 01-Jan-81 00:00:00 GMT", 1981),
        ("Tue, 01 Jan 0069 00:00:00 GMT", 69),
    ],
)
async def test_openai_http_date_years_are_not_email_years(
    header: str, target_year: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2030, 1, 1, tzinfo=UTC)
    monkeypatch.setattr("kernel_providers.openai.time", lambda: now.timestamp())
    error = await _status_error({"Retry-After": header})
    target = datetime(target_year, 1, 1, tzinfo=UTC)
    assert error.retry_after_seconds == max(0.0, (target - now).total_seconds())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current_year", "header"),
    [
        (2030, "Thursday, 29-Feb-80 00:00:00 GMT"),
        (2050, "Tuesday, 29-Feb-00 00:00:00 GMT"),
    ],
)
async def test_openai_legacy_date_pivot_handles_leap_day(
    current_year: int, header: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(current_year, 1, 1, tzinfo=UTC).timestamp()
    monkeypatch.setattr("kernel_providers.openai.time", lambda: now)
    error = await _status_error({"Retry-After": header})
    assert error.retry_after_seconds == 0.0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "header",
    [
        "",
        " \t",
        "secret-header-value",
        "-1",
        "-0",
        "+1",
        "0.5",
        "1e2",
        "1_000",
        "nan",
        "NaN",
        "inf",
        "Infinity",
        "2, 3",
        "Tue, 01 Jan 2030 00:00:10 GMT, 5",
        "Tue, 01 Jan 2030 00:00:10 GMT secret-header-value",
        "Tue, 01 Jan 2030 00:00:10",
        "Tue, 01 Jan 2030 00:00:10 PST",
        "Tue, 01 Jan 2030 00:00:10 +0000",
        "Tue, 99 Jan 2030 00:00:10 GMT",
        "Tue, 01 Jan 2030 99:00:10 GMT",
        "Tue, 01 Jan 0000 00:00:10 GMT",
        "Tue, 01 Jan 10000 00:00:10 GMT",
        "Tue, 01 Jan 2030 00:00:10 GMT\r\nsecret-header-value",
        pytest.param("9" * 5000, id="numeric-overflow"),
    ],
)
async def test_openai_ignores_malformed_retry_after(header: str) -> None:
    error = await _status_error({"Retry-After": header})
    assert error.retry_after_seconds is None


@pytest.mark.asyncio
async def test_openai_ignores_missing_and_duplicate_retry_after() -> None:
    cases: list[dict[str, str] | list[tuple[str, str]]] = [
        {},
        [("Retry-After", "1"), ("Retry-After", "20")],
    ]
    for headers in cases:
        error = await _status_error(headers)
        assert error.retry_after_seconds is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (408, "provider_timeout"),
        (409, "provider_unavailable"),
        (429, "rate_limit"),
        (500, "provider_unavailable"),
        (503, "provider_unavailable"),
        (504, "provider_timeout"),
        (400, "openai_status_error"),
        (401, "openai_status_error"),
    ],
)
async def test_openai_hint_does_not_change_status_classification(
    status_code: int, error_type: str
) -> None:
    error = await _status_error({"Retry-After": "2"}, status_code=status_code)
    assert error.retry_after_seconds == 2.0
    assert error.error_type == error_type


@pytest.mark.asyncio
async def test_openai_quota_error_remains_permanent_with_retry_after() -> None:
    error = await _status_error({"Retry-After": "2"}, error_code="insufficient_quota")
    assert error.retry_after_seconds == 2.0
    assert error.error_type == "openai_quota_exhausted"


@pytest.mark.asyncio
async def test_openai_transport_error_has_no_retry_hint() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret-transport-message")

    provider = OpenAIProvider(api_key="test", transport=httpx.MockTransport(handler))
    with pytest.raises(LLMProviderError) as raised:
        await provider.complete(LLMRequest(model="fixture", messages=()))
    assert raised.value.retry_after_seconds is None
    assert raised.value.error_type == "provider_timeout"
    assert str(raised.value) == "OpenAI API request timed out."
