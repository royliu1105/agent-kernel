import json

import httpx
import pytest
from kernel_providers import (
    LLMFinishReason,
    LLMMessage,
    LLMProviderError,
    LLMRequest,
    LLMToolCall,
    LLMToolChoice,
    LLMToolDefinition,
    MessageRole,
    OpenAIProvider,
    get_openai_api_key,
)


@pytest.mark.asyncio
async def test_openai_provider_converts_request_and_response() -> None:
    captured_payload: dict[str, object] = {}
    captured_auth = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload, captured_auth
        captured_payload = json.loads(request.content)
        captured_auth = request.headers["authorization"]
        return httpx.Response(
            200,
            json={
                "model": "gpt-4.1-mini",
                "output_text": "hello from openai",
                "usage": {
                    "input_tokens": 3,
                    "output_tokens": 4,
                },
            },
        )

    provider = OpenAIProvider(
        api_key="test-key",
        base_url="https://api.test",
        transport=httpx.MockTransport(handler),
    )
    response = await provider.complete(
        LLMRequest(
            model="gpt-4.1-mini",
            messages=(LLMMessage(role=MessageRole.USER, content="hello"),),
            max_output_tokens=128,
        )
    )

    assert captured_auth == "Bearer test-key"
    assert captured_payload == {
        "model": "gpt-4.1-mini",
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": "hello"}],
            }
        ],
        "max_output_tokens": 128,
    }
    assert response.provider == "openai"
    assert response.model == "gpt-4.1-mini"
    assert response.text == "hello from openai"
    assert response.usage.input_tokens == 3
    assert response.usage.output_tokens == 4


@pytest.mark.asyncio
async def test_openai_provider_serializes_native_tool_definitions() -> None:
    captured_payload: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "gpt-4.1-mini",
                "output_text": "",
                "usage": {
                    "input_tokens": 3,
                    "output_tokens": 0,
                },
            },
        )

    provider = OpenAIProvider(
        api_key="test-key",
        base_url="https://api.test",
        transport=httpx.MockTransport(handler),
    )
    await provider.complete(
        LLMRequest(
            model="gpt-4.1-mini",
            messages=(LLMMessage(role=MessageRole.USER, content="search"),),
            tools=(
                LLMToolDefinition(
                    name="kb_search",
                    description="Search the knowledge base.",
                    input_schema={
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                ),
            ),
            tool_choice=LLMToolChoice.AUTO,
        )
    )

    assert captured_payload["tools"] == [
        {
            "type": "function",
            "name": "kb_search",
            "description": "Search the knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        }
    ]
    assert captured_payload["tool_choice"] == "auto"


@pytest.mark.asyncio
async def test_openai_provider_parses_native_function_calls() -> None:
    raw_function_call = {
        "type": "function_call",
        "id": "fc_001",
        "call_id": "call_001",
        "name": "kb_search",
        "arguments": '{"query":"deployment rollback","top_k":3}',
        "status": "completed",
    }

    provider = OpenAIProvider(
        api_key="test-key",
        base_url="https://api.test",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "model": "gpt-4.1-mini",
                    "output": [raw_function_call],
                    "usage": {
                        "input_tokens": 12,
                        "output_tokens": 0,
                    },
                },
            )
        ),
    )

    response = await provider.complete(
        LLMRequest(
            model="gpt-4.1-mini",
            messages=(LLMMessage(role=MessageRole.USER, content="search docs"),),
        )
    )

    assert response.finish_reason is LLMFinishReason.TOOL_CALLS
    assert response.tool_calls[0].id == "call_001"
    assert response.tool_calls[0].name == "kb_search"
    assert response.tool_calls[0].arguments == {
        "query": "deployment rollback",
        "top_k": 3,
    }
    assert response.tool_calls[0].raw == raw_function_call


@pytest.mark.asyncio
async def test_openai_provider_rejects_invalid_function_call_arguments() -> None:
    provider = OpenAIProvider(
        api_key="test-key",
        base_url="https://api.test",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "model": "gpt-4.1-mini",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_001",
                            "name": "kb_search",
                            "arguments": "{not-json",
                        }
                    ],
                },
            )
        ),
    )

    with pytest.raises(LLMProviderError) as error:
        await provider.complete(
            LLMRequest(
                model="gpt-4.1-mini",
                messages=(LLMMessage(role=MessageRole.USER, content="search docs"),),
            )
        )

    assert error.value.error_type == "openai_invalid_tool_arguments"


@pytest.mark.asyncio
async def test_openai_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIProvider(
        api_key=None,
        transport=httpx.MockTransport(lambda _: httpx.Response(200)),
    )

    with pytest.raises(LLMProviderError) as error:
        await provider.complete(
            LLMRequest(
                model="gpt-4.1-mini",
                messages=(LLMMessage(role=MessageRole.USER, content="hello"),),
            )
        )

    assert error.value.error_type == "missing_api_key"


def test_get_openai_api_key_reads_environment_mapping() -> None:
    assert get_openai_api_key({"OPENAI_API_KEY": "test-key"}) == "test-key"
    assert get_openai_api_key({"OPENAI_API_KEY": ""}) is None


def _tool_history() -> tuple[LLMMessage, ...]:
    return (
        LLMMessage(role=MessageRole.USER, content="search"),
        LLMMessage(
            role=MessageRole.ASSISTANT,
            content="Searching now.",
            metadata={
                "tool_calls": [
                    LLMToolCall(
                        id="call_001", name="kb_search", arguments={"query": "rollback"}
                    ).model_dump()
                ]
            },
        ),
        LLMMessage(
            role=MessageRole.TOOL,
            content='{"result": {"matches": 2}}',
            metadata={"provider_tool_call_id": "call_001", "tool_call_id": "internal-uuid"},
        ),
    )


@pytest.mark.asyncio
async def test_openai_provider_replays_function_call_and_correlated_output() -> None:
    captured: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"output_text": "Found two documents."})

    await OpenAIProvider(api_key="test", transport=httpx.MockTransport(handler)).complete(
        LLMRequest(model="fixture", messages=_tool_history())
    )
    assert captured[0]["input"] == [
        {"role": "user", "content": [{"type": "input_text", "text": "search"}]},
        {"role": "assistant", "content": [{"type": "input_text", "text": "Searching now."}]},
        {
            "type": "function_call",
            "call_id": "call_001",
            "name": "kb_search",
            "arguments": '{"query": "rollback"}',
        },
        {
            "type": "function_call_output",
            "call_id": "call_001",
            "output": '{"result": {"matches": 2}}',
        },
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutation",
    [
        "missing_result",
        "orphan_result",
        "wrong_id",
        "internal_id_only",
        "duplicate_result",
        "duplicate_call",
        "bad_metadata",
        "bad_call",
        "non_assistant_call",
        "empty_id",
    ],
)
async def test_openai_provider_rejects_invalid_history_before_http(mutation: str) -> None:
    messages = list(_tool_history())
    if mutation == "missing_result":
        messages.pop()
    elif mutation == "orphan_result":
        messages.pop(1)
    elif mutation == "duplicate_result":
        messages.append(messages[-1])
    elif mutation == "wrong_id":
        messages[-1] = messages[-1].model_copy(
            update={"metadata": {"provider_tool_call_id": "other"}}
        )
    elif mutation == "internal_id_only":
        messages[-1] = messages[-1].model_copy(update={"metadata": {"tool_call_id": "call_001"}})
    elif mutation == "non_assistant_call":
        messages[1] = messages[1].model_copy(update={"role": MessageRole.USER})
    else:
        calls = messages[1].metadata["tool_calls"]
        if mutation == "duplicate_call":
            metadata = {"tool_calls": calls * 2}
        elif mutation == "bad_metadata":
            metadata = {"tool_calls": "not-a-list"}
        elif mutation == "empty_id":
            metadata = {"tool_calls": [{**calls[0], "id": ""}]}
        else:
            metadata = {"tool_calls": [{"secret": "synthetic-private-value"}]}
        messages[1] = messages[1].model_copy(update={"metadata": metadata})
    requests = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, json={"output_text": "must not send"})

    with pytest.raises(LLMProviderError) as error:
        await OpenAIProvider(api_key="test", transport=httpx.MockTransport(handler)).complete(
            LLMRequest(model="fixture", messages=tuple(messages))
        )
    assert error.value.error_type == "openai_invalid_tool_history"
    assert "synthetic-private-value" not in str(error.value)
    assert requests == 0


@pytest.mark.asyncio
async def test_openai_provider_never_substitutes_item_id_for_call_id() -> None:
    provider = OpenAIProvider(
        api_key="test",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "output": [
                        {
                            "type": "function_call",
                            "id": "fc_item",
                            "name": "kb_search",
                            "arguments": "{}",
                        }
                    ]
                },
            )
        ),
    )
    with pytest.raises(LLMProviderError) as error:
        await provider.complete(LLMRequest(model="fixture", messages=()))
    assert error.value.error_type == "openai_invalid_tool_call"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "code", "expected"),
    [
        (429, "rate_limit_exceeded", "rate_limit"),
        (429, "slow_down", "rate_limit"),
        (429, "insufficient_quota", "openai_quota_exhausted"),
        (429, "credit_balance_exhausted", "openai_quota_exhausted"),
        (429, "billing_hard_limit_reached", "openai_quota_exhausted"),
        (408, "timeout", "provider_timeout"),
        (504, "timeout", "provider_timeout"),
        (409, "conflict", "provider_unavailable"),
        (500, "server_error", "provider_unavailable"),
        (503, "server_is_overloaded", "provider_unavailable"),
        (400, "bad_request", "openai_status_error"),
        (401, "invalid_api_key", "openai_status_error"),
        (403, "forbidden", "openai_status_error"),
        (422, "invalid_input", "openai_status_error"),
    ],
)
async def test_openai_status_errors_have_runtime_categories(
    status: int, code: str, expected: str
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, json={"error": {"code": code, "message": "private-body"}})

    with pytest.raises(LLMProviderError) as error:
        await OpenAIProvider(api_key="test", transport=httpx.MockTransport(handler)).complete(
            LLMRequest(model="fixture", messages=())
        )
    assert error.value.error_type == expected
    assert "private-body" not in str(error.value)
    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception_type", "expected"),
    [
        (httpx.ConnectTimeout, "provider_timeout"),
        (httpx.ReadTimeout, "provider_timeout"),
        (httpx.WriteTimeout, "provider_timeout"),
        (httpx.PoolTimeout, "provider_timeout"),
        (httpx.ConnectError, "provider_unavailable"),
        (httpx.ReadError, "provider_unavailable"),
        (httpx.RemoteProtocolError, "provider_unavailable"),
        (httpx.UnsupportedProtocol, "openai_request_error"),
    ],
)
async def test_openai_transport_errors_are_sanitized_and_classified(
    exception_type: type[httpx.RequestError], expected: str
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception_type("private-url-or-body", request=request)

    with pytest.raises(LLMProviderError) as error:
        await OpenAIProvider(api_key="test", transport=httpx.MockTransport(handler)).complete(
            LLMRequest(model="fixture", messages=())
        )
    assert error.value.error_type == expected
    assert "private-url-or-body" not in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [b"not-json-secret", b"[]", b"null"])
async def test_openai_invalid_response_is_typed_and_does_not_expose_body(body: bytes) -> None:
    with pytest.raises(LLMProviderError) as error:
        await OpenAIProvider(
            api_key="test",
            transport=httpx.MockTransport(lambda _: httpx.Response(200, content=body)),
        ).complete(LLMRequest(model="fixture", messages=()))
    assert error.value.error_type == "openai_invalid_response"
    assert "not-json-secret" not in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["call_id", "arguments", "provider", "missing_call"])
async def test_native_history_must_match_normalized_calls(mutation: str) -> None:
    messages = list(_tool_history())
    native_call: dict[str, object] = {
        "type": "function_call",
        "call_id": "call_001",
        "name": "kb_search",
        "arguments": '{"query":"rollback"}',
    }
    if mutation == "call_id":
        native_call["call_id"] = "other"
    if mutation == "arguments":
        native_call["arguments"] = '{"query":"other"}'
    native_output: list[dict[str, object]] = [{"type": "reasoning", "id": "rs_001", "summary": []}]
    if mutation != "missing_call":
        native_output.append(native_call)
    messages[1] = messages[1].model_copy(
        update={
            "metadata": {
                **messages[1].metadata,
                "provider_name": "foreign" if mutation == "provider" else "openai",
                "provider_response_output": native_output,
            }
        }
    )
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"output_text": "should not send"})

    with pytest.raises(LLMProviderError) as error:
        await OpenAIProvider(api_key="test", transport=httpx.MockTransport(handler)).complete(
            LLMRequest(model="fixture", messages=tuple(messages))
        )
    assert error.value.error_type == "openai_invalid_tool_history"
    assert calls == 0


@pytest.mark.asyncio
async def test_reasoning_is_not_extracted_as_assistant_answer() -> None:
    provider = OpenAIProvider(
        api_key="test",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "output": [
                        {
                            "type": "reasoning",
                            "id": "rs_fixture",
                            "summary": [],
                            "content": [
                                {"type": "reasoning_text", "text": "private-native-reasoning"}
                            ],
                        },
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": "Public answer."}],
                        },
                    ]
                },
            )
        ),
    )
    response = await provider.complete(LLMRequest(model="fixture", messages=()))
    assert response.text == "Public answer."
