from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker


def test_eval_run_api_persists_and_lists_reports(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    report = {
        "name": "rag-smoke",
        "passed": True,
        "passed_count": 2,
        "failed_count": 0,
        "case_count": 2,
        "cases": [
            {
                "name": "deployment",
                "passed": True,
                "error_type": None,
                "error_message": None,
                "assertions": [
                    {
                        "name": "min_results",
                        "passed": True,
                        "message": "Retrieved enough results.",
                    }
                ],
            }
        ],
    }

    create_response = client.post(
        "/v1/evals/runs",
        json={
            "name": "rag-smoke",
            "suite_type": "rag",
            "report": report,
            "metadata": {"dataset": "evals/rag-smoke.json"},
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "rag-smoke"
    assert created["suite_type"] == "rag"
    assert created["status"] == "succeeded"
    assert created["passed"] is True
    assert created["case_count"] == 2
    assert created["passed_count"] == 2
    assert created["failed_count"] == 0
    assert created["report"] == report
    assert created["metadata"] == {"dataset": "evals/rag-smoke.json"}
    assert created["trace_id"] is not None

    list_response = client.get("/v1/evals/runs")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [created["id"]]

    get_response = client.get(f"/v1/evals/runs/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


def test_eval_run_api_records_failed_reports(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))

    response = client.post(
        "/v1/evals/runs",
        json={
            "name": "tool-regression",
            "suite_type": "tool_calls",
            "report": {
                "name": "tool-regression",
                "passed": False,
                "passed_count": 1,
                "failed_count": 1,
                "case_count": 2,
                "cases": [],
            },
            "error_type": "assertion_failed",
            "error_message": "One case failed.",
        },
    )

    assert response.status_code == 201
    eval_run = response.json()
    assert eval_run["status"] == "failed"
    assert eval_run["passed"] is False
    assert eval_run["failed_count"] == 1
    assert eval_run["error_type"] == "assertion_failed"


def test_eval_run_api_rejects_invalid_report_counts(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))

    response = client.post(
        "/v1/evals/runs",
        json={
            "name": "bad-report",
            "suite_type": "rag",
            "report": {
                "name": "bad-report",
                "passed": True,
                "passed_count": 1,
                "failed_count": 0,
                "cases": [],
            },
        },
    )

    assert response.status_code == 422
    assert "case_count" in response.json()["detail"]


def test_eval_run_api_returns_404_for_missing_run(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    client = TestClient(create_app(session_factory=sqlite_session_factory))
    missing_id = "00000000-0000-0000-0000-000000000000"

    response = client.get(f"/v1/evals/runs/{missing_id}")

    assert response.status_code == 404
