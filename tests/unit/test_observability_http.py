import http.client

import pytest
from kernel_observability import AggregatingMetricsRecorder, MetricsHttpServer


def test_worker_metrics_listener_authorization_and_lifecycle() -> None:
    recorder = AggregatingMetricsRecorder()
    recorder.increment("tool_calls_total", labels={"tool_name": "echo"})
    server = MetricsHttpServer(recorder, port=0, token="a" * 32)
    server.start()
    try:
        for token, expected in ((None, 401), ("b" * 32, 401), ("a" * 32, 200)):
            connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=3)
            try:
                connection.request(
                    "GET", "/metrics", headers={"Authorization": f"Bearer {token}"} if token else {}
                )
                response = connection.getresponse()
                assert response.status == expected
                body = response.read().decode()
                if expected == 200:
                    assert "tool_calls_total" in body
                    assert "version=0.0.4" in response.getheader("Content-Type", "")
                assert "a" * 32 not in body
            finally:
                connection.close()
    finally:
        server.close()


def test_worker_metrics_public_listener_requires_token() -> None:
    with pytest.raises(ValueError, match="token"):
        MetricsHttpServer(AggregatingMetricsRecorder(), host="0.0.0.0", port=0)
