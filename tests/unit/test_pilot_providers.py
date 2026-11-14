"""No external I/O: named pilot providers must keep configuration isolated."""

import json
from typing import Any

import httpx
import pytest
from kernel_providers import (
    DeepSeekProvider,
    LLMFinishReason,
    LLMMessage,
    LLMProviderError,
    LLMRequest,
    MessageRole,
    OpenAIProvider,
)
from kernel_rag import (
    DashScopeEmbeddingProvider,
    MockEmbeddingProvider,
    OpenAIEmbeddingError,
    OpenAIEmbeddingProvider,
    create_embedding_provider,
)
from kernel_runtime import create_default_model_router


def embedding_env(**overrides: str) -> dict[str, str]:
    return {
        "AGENT_KERNEL_EMBEDDING_PROVIDER": "dashscope",
        "DASHSCOPE_API_KEY": "synthetic-embedding-key",
        "DASHSCOPE_EMBEDDING_DIMENSIONS": "64",
        **overrides,
    }


@pytest.mark.asyncio
async def test_deepseek_missing_key_never_borrows_openai_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "wrong-service-key")

    def forbidden(_: httpx.Request) -> httpx.Response:
        raise AssertionError("No request without the dedicated key")

    with pytest.raises(LLMProviderError) as error:
        await DeepSeekProvider(transport=httpx.MockTransport(forbidden)).complete(
            LLMRequest(model="deepseek-chat", messages=())
        )
    assert error.value.error_type == "missing_api_key"


@pytest.mark.asyncio
async def test_default_routes_separate_keys_hosts_and_provider_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-deepseek-key")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-openai-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/")
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((str(request.url), request.headers["authorization"]))
        assert json.loads(request.content)["model"] == "deepseek-chat"
        return httpx.Response(
            200,
            json={
                "model": "returned-model-id",
                "output_text": "fixture answer",
                "usage": {"input_tokens": 7, "output_tokens": 3},
            },
        )

    original = OpenAIProvider.__init__

    def fixture_init(self: OpenAIProvider, **kwargs: Any) -> None:
        kwargs["transport"] = httpx.MockTransport(handler)
        original(self, **kwargs)

    monkeypatch.setattr(OpenAIProvider, "__init__", fixture_init)
    router = create_default_model_router()
    for prefix in ("deepseek", "openai"):
        route = router.route(f"{prefix}:deepseek-chat")
        response = await route.provider.complete(LLMRequest(model=route.model, messages=()))
        assert response.provider == prefix and response.model == "returned-model-id"
        assert response.usage.input_tokens == 7 and response.usage.output_tokens == 3
    assert seen == [
        ("https://api.deepseek.com/v1/responses", "Bearer synthetic-deepseek-key"),
        ("https://api.openai.com/v1/responses", "Bearer synthetic-openai-key"),
    ]


@pytest.mark.parametrize(
    "url",
    [
        "http://api.deepseek.com",
        "https://api.deepseek.com.evil.test",
        "https://secret@api.deepseek.com",
        "https://api.deepseek.com?key=secret",
        "https://api.deepseek.com#secret",
        "https://127.0.0.1/v1",
        "https://api.deepseek.com:443",
        "https://api.deepseek.com/other",
        " https://api.deepseek.com",
        "https://api.deepseek.com\n",
    ],
)
def test_deepseek_rejects_unsafe_endpoint_without_echoing_it(url: str) -> None:
    with pytest.raises(ValueError) as error:
        DeepSeekProvider(api_key="fixture", base_url=url)
    assert "secret" not in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "kind"),
    [
        (401, "deepseek_status_error"),
        (402, "deepseek_quota_exhausted"),
        (429, "rate_limit"),
        (503, "provider_unavailable"),
        (504, "provider_timeout"),
    ],
)
async def test_deepseek_sanitizes_status_errors_and_preserves_retry_hint(
    status: int, kind: str
) -> None:
    provider = DeepSeekProvider(
        api_key="fixture-secret",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                status, headers={"retry-after": "3"}, json={"secret": "private"}
            )
        ),
    )
    with pytest.raises(LLMProviderError) as error:
        await provider.complete(LLMRequest(model="deepseek-chat", messages=()))
    assert error.value.error_type == kind
    assert error.value.retry_after_seconds == 3
    assert "private" not in str(error.value) and "secret" not in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
async def test_deepseek_never_follows_redirects_with_credentials(status: int) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, headers={"location": "https://untrusted.invalid/collect"})

    provider = DeepSeekProvider(api_key="fixture", transport=httpx.MockTransport(handler))
    with pytest.raises(LLMProviderError) as error:
        await provider.complete(LLMRequest(model="deepseek-chat", messages=()))
    assert error.value.error_type == "deepseek_status_error"
    assert len(requests) == 1 and requests[0].url.host == "api.deepseek.com"


@pytest.mark.asyncio
async def test_deepseek_native_history_is_replayed_only_to_its_provider() -> None:
    native = {
        "type": "function_call",
        "id": "item-1",
        "call_id": "call-1",
        "name": "lookup",
        "arguments": '{"q":"a"}',
        "status": "completed",
    }
    requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"output": [native]})

    provider = DeepSeekProvider(api_key="fixture", transport=httpx.MockTransport(handler))
    first = await provider.complete(LLMRequest(model="deepseek-chat", messages=()))
    assert first.finish_reason is LLMFinishReason.TOOL_CALLS
    messages = (
        LLMMessage(
            role=MessageRole.ASSISTANT,
            content="",
            metadata={
                "provider_name": first.provider,
                "provider_response_output": first.raw["output"],
                "tool_calls": [first.tool_calls[0].model_dump(mode="json")],
            },
        ),
        LLMMessage(
            role=MessageRole.TOOL, content="result", metadata={"provider_tool_call_id": "call-1"}
        ),
    )
    await provider.complete(LLMRequest(model="deepseek-chat", messages=messages))
    assert requests[-1]["input"] == [
        native,
        {"type": "function_call_output", "call_id": "call-1", "output": "result"},
    ]
    with pytest.raises(LLMProviderError, match="selected provider"):
        await OpenAIProvider(api_key="fixture", transport=httpx.MockTransport(handler)).complete(
            LLMRequest(model="fixture", messages=messages)
        )
    assert len(requests) == 2


@pytest.mark.asyncio
async def test_deepseek_rejects_incomplete_tool_output_before_execution() -> None:
    provider = DeepSeekProvider(
        api_key="fixture",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "c",
                            "name": "lookup",
                            "arguments": "{}",
                            "status": "incomplete",
                        }
                    ]
                },
            )
        ),
    )
    with pytest.raises(LLMProviderError, match="safely replayed"):
        await provider.complete(LLMRequest(model="deepseek-chat", messages=()))


def test_dashscope_requires_explicit_selection_and_its_own_key() -> None:
    assert isinstance(
        create_embedding_provider({"DASHSCOPE_API_KEY": "fixture"}), MockEmbeddingProvider
    )
    with pytest.raises(ValueError, match="credentials"):
        create_embedding_provider(
            {
                "AGENT_KERNEL_EMBEDDING_PROVIDER": "dashscope",
                "OPENAI_API_KEY": "wrong",
                "EMBEDDING_API_KEY": "wrong",
            }
        )
    assert create_embedding_provider(embedding_env()).dimensions == 64
    assert (
        create_embedding_provider(
            {"AGENT_KERNEL_EMBEDDING_PROVIDER": "dashscope", "DASHSCOPE_API_KEY": "fixture"}
        ).dimensions
        == 1024
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://dashscope.aliyuncs.com/compatible-mode/v1",
        "https://dashscope.aliyuncs.com.evil.test/compatible-mode/v1",
        "https://secret@dashscope.aliyuncs.com/compatible-mode/v1",
        "https://dashscope.aliyuncs.com/compatible-mode/v1?key=secret",
        "https://dashscope.aliyuncs.com/compatible-mode/v1#secret",
        "https://api.openai.com/v1",
        "https://dashscope.aliyuncs.com/other",
    ],
)
def test_dashscope_rejects_unsafe_or_wrong_service_endpoint(url: str) -> None:
    with pytest.raises(ValueError) as error:
        create_embedding_provider(embedding_env(DASHSCOPE_BASE_URL=url))
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    "overrides",
    [
        {"DASHSCOPE_API_KEY": "bad\nkey"},
        {"DASHSCOPE_EMBEDDING_MODEL": "text-embedding-3-small"},
        {"DASHSCOPE_EMBEDDING_DIMENSIONS": "1536"},
        {"DASHSCOPE_EMBEDDING_DIMENSIONS": "invalid"},
        {"DASHSCOPE_EMBEDDING_DIMENSIONS": "0"},
    ],
)
def test_dashscope_rejects_invalid_credentials_model_and_dimensions(
    overrides: dict[str, str],
) -> None:
    with pytest.raises(ValueError):
        create_embedding_provider(embedding_env(**overrides))


def test_dashscope_batches_reorders_and_never_sends_other_credentials() -> None:
    counts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
        assert request.headers["authorization"] == "Bearer synthetic-embedding-key"
        body = json.loads(request.content)
        assert body["model"] == "text-embedding-v3" and body["dimensions"] == 64
        counts.append(len(body["input"]))
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": i, "embedding": [float(text)] + [0.0] * 63}
                    for i, text in reversed(list(enumerate(body["input"])))
                ]
            },
        )

    provider = DashScopeEmbeddingProvider(
        env=embedding_env(OPENAI_API_KEY="wrong-openai", DEEPSEEK_API_KEY="wrong-deepseek"),
        transport=httpx.MockTransport(handler),
    )
    assert provider.embed_texts([]) == [] and counts == []
    vectors = provider.embed_texts([str(i) for i in range(23)])
    assert counts == [10, 10, 3]
    assert [vector[0] for vector in vectors] == list(range(23))


def test_dashscope_batch_failure_never_returns_partial_vectors() -> None:
    count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        if count == 2:
            raise httpx.ConnectError("PRIVATE key=secret", request=request)
        return httpx.Response(
            200, json={"data": [{"index": i, "embedding": [1.0] * 64} for i in range(10)]}
        )

    provider = DashScopeEmbeddingProvider(
        env=embedding_env(), transport=httpx.MockTransport(handler)
    )
    with pytest.raises(OpenAIEmbeddingError) as error:
        provider.embed_texts(["text"] * 21)
    assert count == 2 and "PRIVATE" not in str(error.value) and "secret" not in str(error.value)


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_dashscope_never_follows_redirects_with_credentials(status: int) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, headers={"location": "https://untrusted.invalid/collect"})

    provider = DashScopeEmbeddingProvider(
        env=embedding_env(), transport=httpx.MockTransport(handler)
    )
    with pytest.raises(OpenAIEmbeddingError):
        provider.embed_texts(["fixture"])
    assert len(requests) == 1 and requests[0].url.host == "dashscope.aliyuncs.com"


@pytest.mark.parametrize("backend", ["openai", "dashscope"])
@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), -float("inf"), 10**400],
    ids=["nan", "inf", "-inf", "huge"],
)
def test_embedding_providers_reject_nonfinite_or_overflowing_vector_values(
    backend: str, value: float | int
) -> None:
    # Raw content also exercises JSON decoders accepting non-standard NaN/Infinity.
    body = json.dumps({"data": [{"index": 0, "embedding": [value] + [0.0] * 63}]})
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=body))
    provider = (
        DashScopeEmbeddingProvider(env=embedding_env(), transport=transport)
        if backend == "dashscope"
        else OpenAIEmbeddingProvider(api_key="fixture", dimensions=64, transport=transport)
    )
    with pytest.raises(OpenAIEmbeddingError) as error:
        provider.embed_texts(["fixture"])
    assert error.value.error_type == "openai_embedding_invalid_vector"
