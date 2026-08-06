from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from kernel_observability import InMemoryMetricsRecorder


def test_healthz() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "agent-kernel-api"}


def test_metrics_endpoint_exports_prometheus_text() -> None:
    metrics_recorder = InMemoryMetricsRecorder()
    metrics_recorder.increment(
        "llm_model_calls_total",
        labels={"provider": "mock", "model": "mock-default", "status": "succeeded"},
    )
    metrics_recorder.observe(
        "llm_model_call_latency_ms",
        12,
        labels={"provider": "mock", "model": "mock-default", "status": "succeeded"},
    )
    client = TestClient(create_app(metrics_recorder=metrics_recorder))

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert '# TYPE llm_model_calls_total counter' in response.text
    assert (
        'llm_model_calls_total{model="mock-default",provider="mock",status="succeeded"} 1'
        in response.text
    )
    assert '# TYPE llm_model_call_latency_ms summary' in response.text
    assert (
        'llm_model_call_latency_ms_count{model="mock-default",provider="mock",'
        'status="succeeded"} 1'
    ) in response.text
    assert (
        'llm_model_call_latency_ms_sum{model="mock-default",provider="mock",'
        'status="succeeded"} 12'
    ) in response.text
