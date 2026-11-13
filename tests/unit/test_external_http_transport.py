import ssl
from collections.abc import Iterable

import httpcore
import pytest
from kernel_tools.external import ExternalToolError, HttpEndpoint
from kernel_tools.external import http as external_http


@pytest.mark.asyncio
async def test_external_http_pins_resolved_ip_and_preserves_host_and_tls_sni(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolutions = 0
    connections: list[str] = []
    sni: list[str | None] = []
    writes: list[bytes] = []

    async def rebinding_dns(host: str, port: int) -> list[str]:
        nonlocal resolutions
        assert host == "service.example" and port == 443
        resolutions += 1
        return ["93.184.216.34"] if resolutions == 1 else ["127.0.0.1"]

    class Stream(httpcore.AsyncMockStream):
        async def write(self, buffer: bytes, timeout: float | None = None) -> None:
            writes.append(buffer)
            await super().write(buffer, timeout=timeout)

        async def start_tls(
            self,
            ssl_context: ssl.SSLContext,
            server_hostname: str | None = None,
            timeout: float | None = None,
        ) -> httpcore.AsyncNetworkStream:
            assert ssl_context.verify_mode == ssl.CERT_REQUIRED
            assert ssl_context.check_hostname is True
            sni.append(server_hostname)
            return self

    async def connect(
        self: httpcore.AnyIOBackend,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[external_http.SocketOption] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        connections.append(host)
        assert host == "93.184.216.34"
        return Stream([b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}"])

    monkeypatch.setattr(external_http, "_resolve_addresses", rebinding_dns)
    monkeypatch.setattr(httpcore.AnyIOBackend, "connect_tcp", connect)
    async with external_http.create_http_client(
        HttpEndpoint(url="https://service.example/v1")
    ) as client:
        assert (await client.get("https://service.example/v1/items")).json() == {}
        with pytest.raises(ExternalToolError, match="disallowed network"):
            await client.get("https://service.example/v1/items")
    assert resolutions == 2
    assert connections == ["93.184.216.34"]
    assert sni == ["service.example"]
    assert b"Host: service.example\r\n" in b"".join(writes)


@pytest.mark.asyncio
async def test_external_http_rejects_mixed_public_private_dns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mixed_dns(host: str, port: int) -> list[str]:
        return ["93.184.216.34", "169.254.169.254"]

    monkeypatch.setattr(external_http, "_resolve_addresses", mixed_dns)
    async with external_http.create_http_client(
        HttpEndpoint(url="https://service.example")
    ) as client:
        with pytest.raises(ExternalToolError, match="disallowed network"):
            await client.get("https://service.example")


@pytest.mark.asyncio
async def test_external_http_bounds_stream_without_content_length() -> None:
    response = httpcore.Response(200, content=b"x" * 20)
    stream = external_http._LimitedStream(response, 10)
    with pytest.raises(ExternalToolError, match="exceeds"):
        async for _ in stream:
            pass
    await stream.aclose()
