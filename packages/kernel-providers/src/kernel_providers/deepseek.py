"""Explicit DeepSeek route using the existing stateless Responses contract."""

from __future__ import annotations

import os
from urllib.parse import urlsplit

import httpx

from kernel_providers.openai import OpenAIProvider

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider(OpenAIProvider):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        key = os.environ.get("DEEPSEEK_API_KEY", "") if api_key is None else api_key
        if key and not all(33 <= ord(char) <= 126 for char in key):
            raise ValueError("DeepSeek credential is malformed.")
        url = (
            base_url
            if base_url is not None
            else (os.environ.get("DEEPSEEK_BASE_URL") or DEFAULT_DEEPSEEK_BASE_URL)
        )
        try:
            parsed = urlsplit(url)
            valid = (
                url.isascii()
                and not any(char.isspace() or ord(char) < 33 for char in url)
                and parsed.scheme == "https"
                and parsed.netloc == "api.deepseek.com"
                and parsed.path in {"", "/", "/v1", "/v1/"}
                and not parsed.query
                and not parsed.fragment
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("DeepSeek base URL must be the official HTTPS API endpoint.")
        super().__init__(
            api_key=key,
            base_url=url,
            timeout=timeout,
            transport=transport,
            provider_name="deepseek",
        )
