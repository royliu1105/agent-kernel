"""OpenAI Responses API provider adapter."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import httpx

from kernel_providers.base import LLMMessage, LLMProviderError, LLMRequest, LLMResponse, LLMUsage

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


def get_openai_api_key(env: Mapping[str, str] | None = None) -> str | None:
    """Read the OpenAI API key from an environment mapping."""

    values = env or os.environ
    value = values.get(OPENAI_API_KEY_ENV)
    if value is None or value.strip() == "":
        return None
    return value


class OpenAIProvider:
    """Minimal OpenAI Responses API provider.

    The adapter uses httpx so tests can mock transport without network access.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = DEFAULT_OPENAI_BASE_URL,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else get_openai_api_key()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    @property
    def name(self) -> str:
        return "openai"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if self._api_key is None:
            raise LLMProviderError(
                f"{OPENAI_API_KEY_ENV} is not configured.",
                error_type="missing_api_key",
            )

        payload = _request_payload(request)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                timeout=self._timeout,
            ) as client:
                response = await client.post(
                    f"{self._base_url}/responses",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise LLMProviderError(
                f"OpenAI API returned {error.response.status_code}.",
                error_type="openai_status_error",
            ) from error
        except httpx.RequestError as error:
            raise LLMProviderError(
                f"OpenAI API request failed: {error}",
                error_type="openai_request_error",
            ) from error

        data = response.json()
        return LLMResponse(
            provider=self.name,
            model=str(data.get("model", request.model)),
            text=_extract_text(data),
            usage=_extract_usage(data),
            raw=data,
        )


def _request_payload(request: LLMRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": request.model,
        "input": [_message_payload(message) for message in request.messages],
    }
    if request.temperature != 0.0:
        payload["temperature"] = request.temperature
    if request.max_output_tokens is not None:
        payload["max_output_tokens"] = request.max_output_tokens
    return payload


def _message_payload(message: LLMMessage) -> dict[str, object]:
    return {
        "role": message.role.value,
        "content": [{"type": "input_text", "text": message.content}],
    }


def _extract_text(data: dict[str, Any]) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str):
        return output_text

    parts: list[str] = []
    output = data.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, dict):
                    continue
                text = content_item.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "".join(parts)


def _extract_usage(data: dict[str, Any]) -> LLMUsage:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return LLMUsage()
    return LLMUsage(
        input_tokens=_int_from_mapping(usage, "input_tokens"),
        output_tokens=_int_from_mapping(usage, "output_tokens"),
        estimated_cost=0.0,
    )


def _int_from_mapping(values: dict[str, Any], key: str) -> int:
    value = values.get(key, 0)
    if isinstance(value, int):
        return value
    return 0
