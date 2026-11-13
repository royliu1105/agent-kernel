"""Bounded HTTP restricted to an operator-approved origin and path prefix."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import AsyncIterator, Iterable
from urllib.parse import unquote

import httpcore
import httpx

from kernel_tools.external.config import HttpEndpoint
from kernel_tools.external.security import ExternalConfigurationError, ExternalToolError


def approved_url(endpoint: HttpEndpoint) -> httpx.URL:
    url = httpx.URL(endpoint.url)
    if (
        url.scheme not in {"https", "http"}
        or not url.host
        or url.userinfo
        or url.query
        or url.fragment
        or (url.scheme == "http" and not endpoint.allow_private_network)
    ):
        raise ExternalConfigurationError("External endpoint must be an approved HTTPS URL.")
    validate_path(url.path)
    return url


def validate_path(path: str) -> None:
    decoded = unquote(path)
    if (
        not decoded.startswith("/")
        or decoded.startswith("//")
        or "\\" in decoded
        or "%" in decoded
        or any(part in {".", ".."} for part in decoded.split("/"))
        or any(ord(char) < 32 for char in decoded)
    ):
        raise ExternalConfigurationError("Unsafe external endpoint path.")


SocketOption = (
    tuple[int, int, int] | tuple[int, int, bytes | bytearray] | tuple[int, int, None, int]
)


async def _resolve_addresses(host: str, port: int) -> list[str]:
    try:
        return [str(ipaddress.ip_address(host))]
    except ValueError:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            host, port, type=socket.SOCK_STREAM
        )
        return list(dict.fromkeys(str(address[4][0]) for address in addresses))


class _PinnedNetworkBackend(httpcore.AsyncNetworkBackend):
    """Resolve once per connection and hand only validated IPs to the socket layer."""

    def __init__(self, *, allow_private: bool) -> None:
        self._allow_private = allow_private
        self._backend = httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[SocketOption] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        try:
            async with asyncio.timeout(timeout):
                addresses = await _resolve_addresses(host, port)
                if not addresses or (
                    not self._allow_private
                    and any(not ipaddress.ip_address(address).is_global for address in addresses)
                ):
                    raise ExternalToolError("External endpoint resolves to a disallowed network.")
                # No hostname is passed below: DNS cannot change the vetted TCP target.
                return await self._backend.connect_tcp(
                    addresses[0],
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
        except TimeoutError:
            raise httpcore.ConnectTimeout("External connection timed out.") from None

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class _LimitedStream(httpx.AsyncByteStream):
    def __init__(self, source: httpcore.Response, limit: int) -> None:
        self._source = source
        self._limit = limit

    async def __aiter__(self) -> AsyncIterator[bytes]:
        size = 0
        try:
            async for chunk in self._source.aiter_stream():
                size += len(chunk)
                if size > self._limit:
                    raise ExternalToolError("External HTTP response exceeds the configured limit.")
                yield chunk
        except httpcore.TimeoutException:
            raise httpx.TimeoutException("External HTTP response timed out.") from None

    async def aclose(self) -> None:
        await self._source.aclose()


class _GuardedTransport(httpx.AsyncBaseTransport):
    def __init__(self, endpoint: HttpEndpoint) -> None:
        self._endpoint = endpoint
        self._url = approved_url(endpoint)
        self._pool = httpcore.AsyncConnectionPool(
            network_backend=_PinnedNetworkBackend(allow_private=endpoint.allow_private_network),
            retries=0,
            max_connections=10,
            max_keepalive_connections=5,
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url = request.url
        if (url.scheme, url.host, url.port) != (self._url.scheme, self._url.host, self._url.port):
            raise ExternalToolError("External request origin is not approved.")
        validate_path(url.path)
        base_path = self._url.path.rstrip("/")
        if url.path != base_path and not url.path.startswith(base_path + "/"):
            raise ExternalToolError("External request path is not approved.")
        assert isinstance(request.stream, httpx.AsyncByteStream)
        core_request = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=url.raw_scheme,
                host=url.raw_host,
                port=url.port,
                target=url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions={"timeout": request.extensions.get("timeout", {})},
        )
        try:
            core_response = await self._pool.handle_async_request(core_request)
        except httpcore.TimeoutException:
            raise httpx.TimeoutException("External HTTP request timed out.") from None
        response = httpx.Response(
            status_code=core_response.status,
            headers=core_response.headers,
            stream=_LimitedStream(core_response, self._endpoint.max_response_bytes),
            extensions=core_response.extensions,
        )
        try:
            # The MCP SDK follows 307/308 itself, regardless of HTTPX's setting.
            # Reject at the transport boundary before the SDK can resend a write.
            if 300 <= response.status_code < 400:
                raise ExternalToolError("External HTTP redirects are not accepted.")
            length = int(response.headers.get("content-length", "0"))
            if length < 0 or length > self._endpoint.max_response_bytes:
                raise ExternalToolError("External HTTP response exceeds the configured limit.")
            # Compression is disabled on requests and rejected here to bound decoded data too.
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise ExternalToolError("Compressed external HTTP responses are not accepted.")
            return response
        except BaseException:
            await response.aclose()
            raise

    async def aclose(self) -> None:
        await self._pool.aclose()


def create_http_client(endpoint: HttpEndpoint) -> httpx.AsyncClient:
    headers = {key: value.get_secret_value() for key, value in endpoint.headers.items()}
    forbidden = {"host", "content-length", "transfer-encoding", "connection", "accept-encoding"}
    if any(key.lower() in forbidden for key in headers):
        raise ExternalConfigurationError("Unsafe operator HTTP header.")
    headers["Accept-Encoding"] = "identity"
    return httpx.AsyncClient(
        transport=_GuardedTransport(endpoint),
        headers=headers,
        timeout=httpx.Timeout(endpoint.timeout_ms / 1_000),
        follow_redirects=False,
        trust_env=False,
    )
