import json

import httpx
import pytest
from kernel_providers import (
    LLMFinishReason,
    LLMMessage,
    LLMProviderError,
    LLMRequest,
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
