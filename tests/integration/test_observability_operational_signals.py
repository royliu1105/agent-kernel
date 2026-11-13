import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from agent_kernel_api.main import create_app
from agent_kernel_worker.main import _create_worker
from fastapi.testclient import TestClient
from kernel_core import RiskLevel
from kernel_observability import AggregatingMetricsRecorder
from kernel_observability.metrics import MetricLabels
from kernel_rag import MockEmbeddingProvider, Retriever, create_rag_tool_registry
from kernel_storage import ApprovalRepository, KnowledgeBaseRepository, ToolCallRepository
from kernel_storage.models import ApprovalRecord, RunEventRecord
from kernel_tools import ToolExecutionFailedError, ToolExecutor, ToolRegistry, ToolRequest
from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker


def _sample(text: str, metric: str) -> float:
    return next(
        float(line.split()[-1]) for line in text.splitlines() if line.startswith(metric + " ")
    )


def test_api_queue_worker_eval_and_approval_signals_are_real_and_recover(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    api_metrics = AggregatingMetricsRecorder()
    worker_metrics = AggregatingMetricsRecorder()
    with TestClient(
        create_app(session_factory=sqlite_session_factory, metrics_recorder=api_metrics)
    ) as client:
        agent = client.post("/v1/agents", json={"name": "PRIVATE_AGENT_SENTINEL"}).json()
        run = client.post(
            f"/v1/agents/{agent['id']}/runs", json={"input": {"prompt": "PRIVATE_PROMPT_SENTINEL"}}
        ).json()
        assert client.post(f"/v1/runs/{run['id']}/queue").status_code == 200
        with sqlite_session_factory() as session:
            session.execute(
                update(RunEventRecord)
                .where(RunEventRecord.type == "run_queued")
                .values(created_at=datetime.now(UTC) - timedelta(seconds=150))
            )
            session.commit()
        before = client.get("/metrics").text
        assert _sample(before, "agent_kernel_queue_backlog") == 1
        assert 149 <= _sample(before, "agent_kernel_queue_oldest_wait_seconds") < 160
        worker = _create_worker(session_factory=sqlite_session_factory, metrics=worker_metrics)
        assert asyncio.run(worker.run_once()).succeeded_count == 1
        after = client.get("/metrics").text
        assert _sample(after, "agent_kernel_queue_backlog") == 0
        assert _sample(after, "agent_kernel_queue_oldest_wait_seconds") == 0
        assert 'agent_kernel_runs{state="succeeded"} 1' in after
        assert 'agent_kernel_run_events{state="run_completed"} 1' in after
        assert (
            'agent_run_segments_total{execution_mode="execute",outcome="succeeded"} 1'
            in worker_metrics.prometheus_text()
        )
        assert "agent_run_segment_duration_seconds_count" in worker_metrics.prometheus_text()

        report = {
            "name": "PRIVATE_EVAL_SENTINEL",
            "case_count": 1,
            "passed_count": 0,
            "failed_count": 1,
            "passed": False,
            "cases": [],
        }
        assert (
            client.post(
                "/v1/evals/runs",
                json={"name": "PRIVATE_EVAL_SENTINEL", "suite_type": "custom", "report": report},
            ).status_code
            == 201
        )
        waiting = client.post(f"/v1/agents/{agent['id']}/runs", json={"input": {}}).json()
        with sqlite_session_factory() as session:
            tool = ToolCallRepository(session).create_requested(
                run_id=UUID(waiting["id"]),
                tool_name="echo",
                arguments={},
                risk_level=RiskLevel.NETWORK,
            )
            assert tool is not None
            approval = ApprovalRepository(session).create_requested(
                tool_call_id=tool.id, reason="PRIVATE_APPROVAL_SENTINEL"
            )
            assert approval is not None
            session.execute(
                update(ApprovalRecord)
                .where(ApprovalRecord.id == str(approval.id))
                .values(requested_at=datetime.now(UTC) - timedelta(seconds=4000))
            )
            session.commit()
        before = client.get("/metrics").text
        assert _sample(before, "agent_kernel_approval_oldest_wait_seconds") >= 4000
        assert 'agent_kernel_evals{state="failed"} 1' in before
        assert 'agent_kernel_approvals{state="requested"} 1' in before
        with sqlite_session_factory() as session:
            ApprovalRepository(session).approve(approval_id=approval.id)
        after = client.get("/metrics").text
        assert _sample(after, "agent_kernel_approval_oldest_wait_seconds") == 0
        for secret in (run["id"], agent["id"], "PRIVATE", "workspace_id", "principal_id"):
            assert secret not in after


def test_api_metrics_count_unmatched_auth_and_internal_errors_without_dynamic_labels(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    metrics = AggregatingMetricsRecorder()
    app = create_app(session_factory=sqlite_session_factory, metrics_recorder=metrics)

    @app.get("/fail")
    def fail() -> None:
        raise RuntimeError("PRIVATE_SENTINEL")

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/fail").status_code == 500
        for index in range(100):
            assert client.get(f"/PRIVATE_SENTINEL_{index}?key=SECRET").status_code == 404
        output = client.get("/metrics").text
        assert 'api_requests_total{method="GET",route_group="other",status_class="5xx"} 1' in output
        assert (
            'api_requests_total{method="GET",route_group="unmatched",status_class="4xx"} 100'
            in output
        )
        assert "PRIVATE" not in output and "SECRET" not in output
    secured = create_app(
        session_factory=sqlite_session_factory, metrics_recorder=metrics, api_key_auth_enabled=True
    )
    with TestClient(secured) as client:
        assert client.get("/v1/runs/00000000-0000-0000-0000-000000000000").status_code == 401
    assert 'status_class="4xx"} 101' in metrics.prometheus_text()


@pytest.mark.parametrize(
    "mode",
    ["AGENT_KERNEL_RATE_LIMIT_PRINCIPAL_REQUESTS", "AGENT_KERNEL_RATE_LIMIT_API_KEY_REQUESTS"],
)
def test_any_quota_requires_authentication(mode: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(mode, "2")
    with pytest.raises(ValueError, match="authentication"):
        create_app(api_key_auth_enabled=False)


def test_default_worker_kb_search_emits_retrieval_metrics(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    metrics = AggregatingMetricsRecorder()
    with sqlite_session_factory() as session:
        kb = KnowledgeBaseRepository(session).create(name="observed")
    with TestClient(create_app(session_factory=sqlite_session_factory)) as client:
        agent = client.post("/v1/agents", json={"name": "observed"}).json()
        run = client.post(
            f"/v1/agents/{agent['id']}/runs",
            json={
                "input": {
                    "tool": {
                        "name": "kb_search",
                        "arguments": {
                            "knowledge_base_id": str(kb.id),
                            "query": "PRIVATE_QUERY_SENTINEL",
                        },
                    }
                }
            },
        ).json()
        assert client.post(f"/v1/runs/{run['id']}/queue").status_code == 200
        worker = _create_worker(session_factory=sqlite_session_factory, metrics=metrics)
        assert asyncio.run(worker.run_once()).succeeded_count == 1
    output = metrics.prometheus_text()
    assert (
        'rag_retrievals_total{error_type="none",model="mock-embedding-v1",status="succeeded"} 1'
        in output
    )
    assert "rag_retrieval_duration_seconds_count" in output
    assert "PRIVATE_QUERY_SENTINEL" not in output


def test_api_registry_reuses_injected_retriever_and_recorder(
    sqlite_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agent_kernel_api import main

    class BrokenEmbedding(MockEmbeddingProvider):
        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("PRIVATE_UPSTREAM_SENTINEL")

    metrics = AggregatingMetricsRecorder()
    retriever = Retriever(embedding_provider=BrokenEmbedding(), metrics_recorder=metrics)
    with sqlite_session_factory() as session:
        kb = KnowledgeBaseRepository(session).create(name="observed")
    captured: list[ToolRegistry] = []
    factory = create_rag_tool_registry

    def capture(**kwargs: object) -> ToolRegistry:
        assert kwargs["retriever"] is retriever
        assert kwargs["metrics_recorder"] is metrics
        registry = factory(**kwargs)  # type: ignore[arg-type]
        captured.append(registry)
        return registry

    monkeypatch.setattr(main, "create_rag_tool_registry", capture)
    with (
        TestClient(
            create_app(
                session_factory=sqlite_session_factory,
                metrics_recorder=metrics,
                retriever=retriever,
            )
        ),
        pytest.raises(ToolExecutionFailedError),
    ):
        asyncio.run(
            ToolExecutor(registry=captured[0]).execute(
                ToolRequest(
                    tool_name="kb_search",
                    arguments={"knowledge_base_id": str(kb.id), "query": "secret"},
                )
            )
        )
    output = metrics.prometheus_text()
    assert "rag_retrieval_failure_total" in output
    assert 'status="failed"' in output
    assert "PRIVATE_UPSTREAM_SENTINEL" not in output


def test_segment_metric_sink_failure_does_not_interrupt_worker_cleanup(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    class FaultyRecorder(AggregatingMetricsRecorder):
        def increment(
            self, name: str, *, value: float = 1.0, labels: MetricLabels | None = None
        ) -> None:
            if name.startswith("agent_run_"):
                raise RuntimeError("Metric sink unavailable")
            super().increment(name, value=value, labels=labels)

    with TestClient(create_app(session_factory=sqlite_session_factory)) as client:
        agent = client.post("/v1/agents", json={"name": "observed"}).json()
        run = client.post(f"/v1/agents/{agent['id']}/runs", json={"input": {}}).json()
        client.post(f"/v1/runs/{run['id']}/queue")
        worker = _create_worker(session_factory=sqlite_session_factory, metrics=FaultyRecorder())
        assert asyncio.run(worker.run_once()).succeeded_count == 1
        assert client.get(f"/v1/runs/{run['id']}").json()["status"] == "succeeded"
