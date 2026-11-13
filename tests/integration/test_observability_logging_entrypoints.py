"""Subprocess checks preserve the test runner's own logging configuration."""

import os
import subprocess
import sys
import textwrap

import pytest


def _run(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        env={**os.environ, "DATABASE_URL": "sqlite://", "AGENT_KERNEL_OTEL_ENABLED": "false"},
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_default_uvicorn_entrypoint_redacts_actual_database_exception() -> None:
    result = _run("""
        import asyncio, logging
        from unittest.mock import Mock
        import h11
        import uvicorn
        from sqlalchemy import create_engine, text
        from uvicorn.protocols.http.h11_impl import RequestResponseCycle
        from uvicorn.protocols.http.flow_control import FlowControl
        from agent_kernel_api import main

        def run(app, **kwargs):
            uvicorn.Config(app, **kwargs)
            async def failing(scope, receive, send):
                with create_engine("sqlite://").connect() as connection:
                    connection.execute(text("INSERT INTO missing VALUES (:prompt, :secret)"),
                        {"prompt": "PRIVATE_PROMPT_SENTINEL", "secret": "SQL_SECRET_SENTINEL"})
            async def exercise():
                transport = Mock()
                conn = h11.Connection(h11.SERVER)
                conn.receive_data(b"GET /?token=URL_SECRET_SENTINEL HTTP/1.1\\r\\n"
                                  b"Host: localhost\\r\\n\\r\\n")
                conn.next_event()
                cycle = RequestResponseCycle(
                    scope={"type": "http", "method": "GET", "path": "/", "root_path": "",
                        "query_string": b"token=URL_SECRET_SENTINEL", "http_version": "1.1",
                        "client": ("127.0.0.1", 123), "headers": []},
                    conn=conn, transport=transport,
                    flow=FlowControl(transport), logger=logging.getLogger("uvicorn.error"),
                    access_logger=logging.getLogger("uvicorn.access"), access_log=True,
                    default_headers=[], message_event=asyncio.Event(), on_response=lambda: None)
                await cycle.run_asgi(failing)
                assert cycle.response_complete
            asyncio.run(exercise())
        main.uvicorn.run = run
        main.main()
    """)
    assert result.returncode == 0, result.stderr
    assert "OperationalError" in result.stderr
    assert "PRIVATE_PROMPT_SENTINEL" not in result.stderr
    assert "SQL_SECRET_SENTINEL" not in result.stderr
    assert "URL_SECRET_SENTINEL" not in result.stderr
    assert "INSERT INTO" not in result.stderr


def test_worker_entrypoint_does_not_print_raw_top_level_exception() -> None:
    result = _run("""
        import logging
        from agent_kernel_worker import main
        def failing():
            logging.getLogger("httpx").warning("token=SDK_SECRET_SENTINEL")
            raise RuntimeError("prompt=WORKER_PROMPT_SENTINEL")
        main.app = failing
        main.main()
    """)
    assert result.returncode == 1
    assert "RuntimeError" in result.stderr
    assert "SDK_SECRET_SENTINEL" not in result.stderr
    assert "WORKER_PROMPT_SENTINEL" not in result.stderr
    assert "Traceback" not in result.stderr


def test_default_api_import_failure_does_not_bypass_safe_entrypoint() -> None:
    result = _run("""
        import kernel_observability
        def fail():
            raise RuntimeError("STARTUP_SECRET_SENTINEL")
        kernel_observability.configure_opentelemetry = fail
        from agent_kernel_api import main
    """)
    assert result.returncode == 1
    assert "RuntimeError" in result.stderr
    assert "STARTUP_SECRET_SENTINEL" not in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("entrypoint", ["api", "worker"])
def test_default_entrypoints_redact_malformed_mcp_notifications(entrypoint: str) -> None:
    setup = (
        "from agent_kernel_api.main import create_app; create_app()"
        if entrypoint == "api"
        else "from agent_kernel_worker import main; main.app = lambda: None; main.main()"
    )
    result = _run(
        setup
        + "\n"
        + textwrap.dedent("""
        import asyncio, logging
        import anyio
        import mcp.types as types
        from mcp import ClientSession
        from mcp.shared.message import SessionMessage

        async def exercise():
            inbound, read = anyio.create_memory_object_stream(1)
            write, outbound = anyio.create_memory_object_stream(1)
            async with inbound, outbound, ClientSession(read, write):
                await inbound.send(SessionMessage(types.JSONRPCMessage(
                    types.JSONRPCNotification(jsonrpc="2.0", method="notifications/message",
                        params={"data": "MCP_METADATA_SENTINEL", "level": "invalid"}))))
                await asyncio.sleep(0.05)
        asyncio.run(exercise())
        logging.getLogger("httpx").warning("GET https://host/?key=SDK_URL_SENTINEL")
    """)
    )
    assert result.returncode == 0, result.stderr
    assert '"level":"warning"' in result.stderr
    assert "MCP_METADATA_SENTINEL" not in result.stderr
    assert "SDK_URL_SENTINEL" not in result.stderr
