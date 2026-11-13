"""Small private metrics listener for worker processes without an API server."""

from __future__ import annotations

import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from kernel_observability.aggregation import PROMETHEUS_CONTENT_TYPE
from kernel_observability.metrics import ExposableMetricsRecorder


class MetricsHttpServer:
    """One bounded request thread, explicit lifecycle, no request/access logging."""

    def __init__(
        self,
        recorder: ExposableMetricsRecorder,
        *,
        host: str = "127.0.0.1",
        port: int = 9001,
        token: str | None = None,
    ) -> None:
        if host not in {"127.0.0.1", "localhost", "::1"} and not token:
            raise ValueError("A monitoring token is required on non-loopback metrics listeners.")
        if token is not None and (len(token) < 32 or not token.isascii() or token.isspace()):
            raise ValueError("Monitoring tokens must contain at least 32 ASCII characters.")

        class Handler(BaseHTTPRequestHandler):
            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(2)

            def do_GET(self) -> None:
                if self.path != "/metrics":
                    self.send_error(404)
                    return
                authorization = self.headers.get("Authorization", "")
                if token and not hmac.compare_digest(
                    authorization.encode("utf-8"), f"Bearer {token}".encode("ascii")
                ):
                    self.send_response(401)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                body = recorder.prometheus_text().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", PROMETHEUS_CONTENT_TYPE)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                pass

        self._server = HTTPServer((host, port), Handler)
        self._thread = Thread(target=self._server.serve_forever, name="metrics-http", daemon=True)
        self._started = False

    @property
    def port(self) -> int:
        return int(self._server.server_port)

    def start(self) -> None:
        if not self._started:
            self._thread.start()
            self._started = True

    def close(self) -> None:
        if self._started:
            self._server.shutdown()
            self._thread.join(timeout=3)
            self._started = False
        self._server.server_close()
