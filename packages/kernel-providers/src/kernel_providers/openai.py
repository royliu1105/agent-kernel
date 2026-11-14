"""OpenAI Responses API provider adapter."""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from time import time
from typing import Any

import httpx
from pydantic import ValidationError

from kernel_providers.base import (
    LLMFinishReason,
    LLMMessage,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMToolDefinition,
    LLMUsage,
    MessageRole,
)

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"

_HTTP_DAY = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
_HTTP_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
_HTTP_TIME = r"[0-9]{2}:[0-9]{2}:[0-9]{2}"
_HTTP_DATE = re.compile(
    rf"(?:{_HTTP_DAY}, [0-9]{{2}} {_HTTP_MONTH} (?P<year>[0-9]{{4}}) {_HTTP_TIME} GMT"
    rf"|(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
    rf"[0-9]{{2}}-{_HTTP_MONTH}-[0-9]{{2}} {_HTTP_TIME} GMT"
    rf"|{_HTTP_DAY} {_HTTP_MONTH} (?:[0-9]{{2}}| [0-9]) {_HTTP_TIME} "
    rf"(?P<asctime_year>[0-9]{{4}}))"
)


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
        provider_name: str = "openai",
    ) -> None:
        self._api_key = api_key if api_key is not None else get_openai_api_key()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport
        self._provider_name = provider_name
        self._display_name = "OpenAI" if provider_name == "openai" else "DeepSeek"

    @property
    def name(self) -> str:
        return self._provider_name

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self._api_key:
            raise LLMProviderError(
                f"{self.name.upper()}_API_KEY is not configured.",
                error_type="missing_api_key",
            )

        payload = _request_payload(request, provider_name=self.name)
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
                f"{self._display_name} API returned {error.response.status_code}.",
                error_type=(
                    f"{self.name}_quota_exhausted"
                    if error.response.status_code == 402
                    else _status_error_type(error.response).replace("openai_", f"{self.name}_")
                ),
                retry_after_seconds=_retry_after_seconds(error.response),
            ) from error
        except httpx.TimeoutException as error:
            raise LLMProviderError(
                f"{self._display_name} API request timed out.",
                error_type="provider_timeout",
            ) from error
        except (httpx.NetworkError, httpx.RemoteProtocolError) as error:
            raise LLMProviderError(
                f"{self._display_name} API is unavailable.",
                error_type="provider_unavailable",
            ) from error
        except httpx.RequestError as error:
            raise LLMProviderError(
                f"{self._display_name} API request failed.",
                error_type=f"{self.name}_request_error",
            ) from error

        try:
            data = response.json()
        except ValueError as error:
            raise LLMProviderError(
                f"{self._display_name} API returned invalid JSON.",
                error_type=f"{self.name}_invalid_response",
            ) from error
        if not isinstance(data, dict):
            raise LLMProviderError(
                f"{self._display_name} API response must be an object.",
                error_type=f"{self.name}_invalid_response",
            )
        tool_calls = _extract_tool_calls(data)
        if tool_calls:
            # Validate replayable native history before runtime can execute a tool.
            _native_output_payload(data.get("output"), tool_calls)
        return LLMResponse(
            provider=self.name,
            model=str(data.get("model", request.model)),
            text=_extract_text(data),
            usage=_extract_usage(data),
            finish_reason=_extract_finish_reason(data),
            tool_calls=tool_calls,
            raw=data,
        )


def _request_payload(request: LLMRequest, *, provider_name: str = "openai") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": request.model,
        "input": _input_payload(request.messages, provider_name=provider_name),
    }
    if request.temperature != 0.0:
        payload["temperature"] = request.temperature
    if request.max_output_tokens is not None:
        payload["max_output_tokens"] = request.max_output_tokens
    if request.tools:
        payload["tools"] = [_tool_payload(tool) for tool in request.tools]
    if request.tool_choice is not None:
        payload["tool_choice"] = request.tool_choice.value
    return payload


def _input_payload(
    messages: tuple[LLMMessage, ...], *, provider_name: str = "openai"
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    pending: set[str] = set()
    seen: set[str] = set()
    for message in messages:
        if message.role is MessageRole.TOOL:
            call_id = message.metadata.get("provider_tool_call_id")
            if not isinstance(call_id, str) or call_id not in pending:
                raise LLMProviderError(
                    "OpenAI tool result requires a matching pending provider call ID.",
                    error_type="openai_invalid_tool_history",
                )
            items.append(
                {"type": "function_call_output", "call_id": call_id, "output": message.content}
            )
            pending.remove(call_id)
            continue

        raw_calls = message.metadata.get("tool_calls", [])
        if not isinstance(raw_calls, list) or (
            raw_calls and message.role is not MessageRole.ASSISTANT
        ):
            raise LLMProviderError(
                "OpenAI function call history must be an assistant tool_calls list.",
                error_type="openai_invalid_tool_history",
            )
        if pending:
            raise LLMProviderError(
                "OpenAI function calls require results before the next message.",
                error_type="openai_invalid_tool_history",
            )
        calls: list[LLMToolCall] = []
        for raw_call in raw_calls:
            try:
                call = LLMToolCall.model_validate(raw_call)
            except ValidationError as error:
                raise LLMProviderError(
                    "OpenAI function call history is invalid.",
                    error_type="openai_invalid_tool_history",
                ) from error
            if not call.id.strip() or not call.name.strip() or call.id in seen:
                raise LLMProviderError(
                    "OpenAI function call history requires unique non-empty IDs and names.",
                    error_type="openai_invalid_tool_history",
                )
            calls.append(call)
            pending.add(call.id)
            seen.add(call.id)
        native_output = message.metadata.get("provider_response_output")
        if native_output is not None:
            if (
                message.role is not MessageRole.ASSISTANT
                or message.metadata.get("provider_name") != provider_name
            ):
                raise LLMProviderError(
                    "Native history must come from the selected provider's assistant response.",
                    error_type="openai_invalid_tool_history",
                )
            items.extend(_native_output_payload(native_output, tuple(calls)))
            continue
        # An empty assistant message is only a carrier for normalized tool metadata.
        if message.content or not calls:
            items.append(
                {
                    "role": message.role.value,
                    "content": [{"type": "input_text", "text": message.content}],
                }
            )
        items.extend(
            {
                "type": "function_call",
                "call_id": call.id,
                "name": call.name,
                "arguments": json.dumps(call.arguments, sort_keys=True),
            }
            for call in calls
        )
    if pending:
        raise LLMProviderError(
            "OpenAI function call history is missing tool results.",
            error_type="openai_invalid_tool_history",
        )
    return items


def _native_output_payload(output: object, calls: tuple[LLMToolCall, ...]) -> list[dict[str, Any]]:
    """Replay provider-native items in order, without synthesizing reasoning."""
    invalid = LLMProviderError(
        "OpenAI native output cannot be safely replayed as tool-call history.",
        error_type="openai_invalid_tool_history",
    )
    if not isinstance(output, list) or not output:
        raise invalid
    replay: list[dict[str, Any]] = []
    native_calls: list[LLMToolCall] = []
    for item in output:
        if not isinstance(item, dict) or item.get("status", "completed") != "completed":
            raise invalid
        kind = item.get("type")
        if kind == "function_call":
            if not isinstance(item.get("arguments"), str):
                raise invalid
            native_calls.append(_tool_call_from_output_item(item))
        elif kind == "reasoning":
            if _string_value(item, "id") is None or not _valid_text_parts(
                item.get("summary"), {"summary_text": "text"}
            ):
                raise invalid
            if "content" in item and not _valid_text_parts(
                item["content"], {"reasoning_text": "text"}
            ):
                raise invalid
            if item.get("encrypted_content") is not None and not isinstance(
                item["encrypted_content"], str
            ):
                raise invalid
        elif kind == "message":
            if item.get("role") != "assistant" or not _valid_text_parts(
                item.get("content"), {"output_text": "text", "refusal": "refusal"}
            ):
                raise invalid
        else:
            # Built-in/custom output types need their own validated continuation.
            raise invalid
        replay.append(deepcopy(item))
    if [(c.id, c.name, c.arguments) for c in native_calls] != [
        (c.id, c.name, c.arguments) for c in calls
    ]:
        raise invalid
    return replay


def _valid_text_parts(value: object, fields: dict[str, str]) -> bool:
    if not isinstance(value, list):
        return False
    return all(
        isinstance(part, dict)
        and isinstance(part.get("type"), str)
        and part["type"] in fields
        and isinstance(part.get(fields[part["type"]]), str)
        for part in value
    )


def _retry_after_seconds(response: httpx.Response) -> float | None:
    values = response.headers.get_list("retry-after")
    if len(values) != 1:
        return None
    value = values[0].strip(" \t")
    if value.isascii() and value.isdecimal():
        seconds = float(value)
        return seconds if math.isfinite(seconds) else None
    # The email parser alone also accepts non-HTTP dates and trailing garbage.
    match = _HTTP_DATE.fullmatch(value)
    if match is None:
        return None
    try:
        now = datetime.fromtimestamp(time(), UTC)
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            date = date.replace(tzinfo=UTC)
        year = match.group("year") or match.group("asctime_year")
        if year is not None:
            # email.utils applies its two-digit pivot even to years like 0000.
            date = date.replace(year=int(year))
        else:
            # HTTP's obsolete two-digit years use a rolling 50-year future limit.
            limit = now.year + 50
            target_year = limit - (limit - date.year % 100) % 100
            if target_year == limit and date.timetuple()[1:6] > now.timetuple()[1:6]:
                target_year -= 100
            date = date.replace(year=target_year)
        return max(0.0, (date - now).total_seconds())
    except (OverflowError, OSError, TypeError, ValueError):
        return None


def _status_error_type(response: httpx.Response) -> str:
    if response.status_code == 429:
        # Billing exhaustion is not transient throttling; retrying spends attempts
        # without a chance of recovery and must not silently select a fallback.
        try:
            data = response.json()
        except ValueError:
            data = None
        error = data.get("error") if isinstance(data, dict) else None
        permanent = {"insufficient_quota", "credit_balance_exhausted", "billing_hard_limit_reached"}
        if isinstance(error, dict) and any(
            isinstance(error.get(key), str) and error[key] in permanent for key in ("code", "type")
        ):
            return "openai_quota_exhausted"
        return "rate_limit"
    if response.status_code in (408, 504):
        return "provider_timeout"
    if response.status_code == 409 or 500 <= response.status_code < 600:
        return "provider_unavailable"
    return "openai_status_error"


def _tool_payload(tool: LLMToolDefinition) -> dict[str, object]:
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.input_schema,
    }


def _extract_text(data: dict[str, Any]) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str):
        return output_text

    parts: list[str] = []
    output = data.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, dict) or content_item.get("type") != "output_text":
                    continue
                text = content_item.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "".join(parts)


def _extract_finish_reason(data: dict[str, Any]) -> LLMFinishReason:
    if _has_tool_calls(data):
        return LLMFinishReason.TOOL_CALLS

    status = data.get("status")
    if status == "incomplete":
        incomplete_details = data.get("incomplete_details")
        if isinstance(incomplete_details, dict) and incomplete_details.get("reason") == (
            "max_output_tokens"
        ):
            return LLMFinishReason.LENGTH
        return LLMFinishReason.UNKNOWN
    if status == "failed":
        return LLMFinishReason.ERROR
    return LLMFinishReason.STOP


def _extract_tool_calls(data: dict[str, Any]) -> tuple[LLMToolCall, ...]:
    calls: list[LLMToolCall] = []
    output = data.get("output")
    if not isinstance(output, list):
        return ()

    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "function_call":
            calls.append(_tool_call_from_output_item(item))
            continue

        content = item.get("content")
        if not isinstance(content, list):
            continue
        for content_item in content:
            if isinstance(content_item, dict) and content_item.get("type") == "function_call":
                calls.append(_tool_call_from_output_item(content_item))

    return tuple(calls)


def _has_tool_calls(data: dict[str, Any]) -> bool:
    output = data.get("output")
    if not isinstance(output, list):
        return False
    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "function_call":
            return True
        content = item.get("content")
        if not isinstance(content, list):
            continue
        if any(
            isinstance(value, dict) and value.get("type") == "function_call" for value in content
        ):
            return True
    return False


def _tool_call_from_output_item(item: dict[str, Any]) -> LLMToolCall:
    call_id = _string_value(item, "call_id")
    name = _string_value(item, "name")
    if call_id is None or name is None:
        raise LLMProviderError(
            "OpenAI function call output is missing call_id or name.",
            error_type="openai_invalid_tool_call",
        )

    return LLMToolCall(
        id=call_id,
        name=name,
        arguments=_tool_arguments_from_output_item(item),
        raw=item,
    )


def _tool_arguments_from_output_item(item: dict[str, Any]) -> dict[str, Any]:
    raw_arguments = item.get("arguments", {})
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if isinstance(raw_arguments, str):
        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError as error:
            raise LLMProviderError(
                "OpenAI function call arguments are not valid JSON.",
                error_type="openai_invalid_tool_arguments",
            ) from error
        if not isinstance(parsed, dict):
            raise LLMProviderError(
                "OpenAI function call arguments must decode to a JSON object.",
                error_type="openai_invalid_tool_arguments",
            )
        return parsed
    raise LLMProviderError(
        "OpenAI function call arguments must be a JSON object or JSON string.",
        error_type="openai_invalid_tool_arguments",
    )


def _string_value(values: dict[str, Any], key: str) -> str | None:
    value = values.get(key)
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


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
