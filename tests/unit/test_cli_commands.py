import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from agent_kernel_cli import main as cli_main
from click import ClickException
from typer.testing import CliRunner


def test_agent_create_cli_prints_api_response(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        calls.append((method, path, json_payload))
        assert api_url == "http://testserver"
        return {"id": "agent-1", "name": "research-agent"}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "agent",
            "create",
            "--name",
            "research-agent",
            "--api-url",
            "http://testserver",
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        ("POST", "/v1/agents", {"name": "research-agent", "description": ""}),
    ]
    assert '"name": "research-agent"' in result.output


def test_run_create_cli_sends_input_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> dict[str, str]:
        calls.append((method, path, json_payload))
        return {"id": "run-1", "status": "created"}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "run",
            "create",
            "00000000-0000-0000-0000-000000000001",
            "--input",
            '{"task":"summarize"}',
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        (
            "POST",
            "/v1/agents/00000000-0000-0000-0000-000000000001/runs",
            {"input": {"task": "summarize"}},
        ),
    ]
    assert '"status": "created"' in result.output


def test_run_create_cli_accepts_json_file_input(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []
    input_path = tmp_path / "run-input.json"
    input_path.write_text('{"task":"summarize","model":"mock:echo"}', encoding="utf-8")

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> dict[str, str]:
        calls.append((method, path, json_payload))
        return {"id": "run-1", "status": "created"}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "run",
            "create",
            "00000000-0000-0000-0000-000000000001",
            "--input",
            f"@{input_path}",
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        (
            "POST",
            "/v1/agents/00000000-0000-0000-0000-000000000001/runs",
            {"input": {"task": "summarize", "model": "mock:echo"}},
        ),
    ]


def test_run_inspect_and_events_cli_use_read_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path))
        return []

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    runner = CliRunner()
    run_id = "00000000-0000-0000-0000-000000000002"

    inspect_result = runner.invoke(cli_main.app, ["run", "inspect", run_id])
    events_result = runner.invoke(cli_main.app, ["run", "events", run_id])

    assert inspect_result.exit_code == 0
    assert events_result.exit_code == 0
    assert calls == [
        ("GET", f"/v1/runs/{run_id}"),
        ("GET", f"/v1/runs/{run_id}/events"),
    ]


def test_run_queue_and_cancel_cli_use_transition_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path))
        return {"id": path.split("/")[3], "status": "queued"}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    runner = CliRunner()
    run_id = "00000000-0000-0000-0000-000000000003"

    queue_result = runner.invoke(cli_main.app, ["run", "queue", run_id])
    cancel_result = runner.invoke(cli_main.app, ["run", "cancel", run_id])

    assert queue_result.exit_code == 0
    assert cancel_result.exit_code == 0
    assert calls == [
        ("POST", f"/v1/runs/{run_id}/queue"),
        ("POST", f"/v1/runs/{run_id}/cancel"),
    ]


def test_run_resume_cli_uses_resume_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path, json_payload))
        return {"id": path.split("/")[3], "status": "succeeded"}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    run_id = "00000000-0000-0000-0000-000000000005"
    approval_id = "00000000-0000-0000-0000-000000000006"

    result = CliRunner().invoke(
        cli_main.app,
        ["run", "resume", run_id, "--approval-id", approval_id],
    )

    assert result.exit_code == 0
    assert calls == [
        ("POST", f"/v1/runs/{run_id}/resume", {"approval_id": approval_id}),
    ]
    assert '"status": "succeeded"' in result.output


def test_eval_report_cli_runs_local_json_dataset(tmp_path: Path) -> None:
    dataset_path = tmp_path / "rag-eval.json"
    dataset_path.write_text(
        json.dumps(
            {
                "name": "rag-smoke",
                "cases": [
                    {
                        "name": "deployment",
                        "query": "alpha deployment rollback checklist",
                        "top_k": 1,
                        "top_result_must_contain": ["deployment", "rollback"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli_main.app, ["eval", "report", str(dataset_path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["name"] == "rag-smoke"
    assert payload["passed"] is True
    assert payload["passed_count"] == 1
    assert payload["cases"][0]["name"] == "deployment"


def test_eval_report_cli_exits_nonzero_for_failing_dataset(tmp_path: Path) -> None:
    dataset_path = tmp_path / "rag-eval.json"
    dataset_path.write_text(
        json.dumps(
            {
                "name": "rag-failing",
                "cases": [
                    {
                        "name": "deployment",
                        "query": "alpha deployment rollback checklist",
                        "top_k": 1,
                        "min_results": 2,
                        "top_result_must_contain": ["deployment"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli_main.app, ["eval", "report", str(dataset_path)])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["passed"] is False
    assert payload["failed_count"] == 1


def test_eval_report_cli_can_publish_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "rag-eval.json"
    dataset_path.write_text(
        json.dumps(
            {
                "name": "rag-smoke",
                "cases": [
                    {
                        "name": "deployment",
                        "query": "alpha deployment rollback checklist",
                        "top_k": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        assert api_url == "http://api.test"
        calls.append((method, path, json_payload))
        return {"id": "eval-run-1", "name": "rag-smoke", "passed": True}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "eval",
            "report",
            str(dataset_path),
            "--publish",
            "--api-url",
            "http://api.test",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {"id": "eval-run-1", "name": "rag-smoke", "passed": True}
    assert calls[0][0] == "POST"
    assert calls[0][1] == "/v1/evals/runs"
    assert calls[0][2] is not None
    assert calls[0][2]["name"] == "rag-smoke"
    assert calls[0][2]["suite_type"] == "rag"
    assert calls[0][2]["metadata"] == {"dataset_path": str(dataset_path)}


def test_approval_cli_uses_approval_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path, json_payload))
        return {"id": "approval-1", "status": "requested"}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    runner = CliRunner()
    approval_id = "00000000-0000-0000-0000-000000000004"

    list_result = runner.invoke(cli_main.app, ["approval", "list"])
    inspect_result = runner.invoke(cli_main.app, ["approval", "inspect", approval_id])
    approve_result = runner.invoke(
        cli_main.app,
        ["approval", "approve", approval_id, "--note", "Looks safe."],
    )
    reject_result = runner.invoke(
        cli_main.app,
        ["approval", "reject", approval_id, "--reason", "Too risky."],
    )

    assert list_result.exit_code == 0
    assert inspect_result.exit_code == 0
    assert approve_result.exit_code == 0
    assert reject_result.exit_code == 0
    assert calls == [
        ("GET", "/v1/approvals", None),
        ("GET", f"/v1/approvals/{approval_id}", None),
        (
            "POST",
            f"/v1/approvals/{approval_id}/approve",
            {"decision_note": "Looks safe."},
        ),
        ("POST", f"/v1/approvals/{approval_id}/reject", {"reason": "Too risky."}),
    ]


def test_knowledge_base_cli_uses_kb_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path, json_payload))
        return {"id": "kb-1", "name": "engineering-handbook"}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    runner = CliRunner()
    kb_id = "00000000-0000-0000-0000-000000000007"

    create_result = runner.invoke(
        cli_main.app,
        [
            "kb",
            "create",
            "--name",
            "engineering-handbook",
            "--description",
            "Engineering docs",
            "--metadata",
            '{"owner":"platform"}',
        ],
    )
    list_result = runner.invoke(cli_main.app, ["kb", "list"])
    inspect_result = runner.invoke(cli_main.app, ["kb", "inspect", kb_id])

    assert create_result.exit_code == 0
    assert list_result.exit_code == 0
    assert inspect_result.exit_code == 0
    assert calls == [
        (
            "POST",
            "/v1/knowledge-bases",
            {
                "name": "engineering-handbook",
                "description": "Engineering docs",
                "metadata": {"owner": "platform"},
            },
        ),
        ("GET", "/v1/knowledge-bases", None),
        ("GET", f"/v1/knowledge-bases/{kb_id}", None),
    ]


def test_knowledge_base_search_cli_uses_retrieval_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path, json_payload))
        assert api_url == "http://testserver"
        return {"results": [{"content": "alpha"}]}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    kb_id = "00000000-0000-0000-0000-000000000010"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "kb",
            "search",
            kb_id,
            "--query",
            "alpha",
            "--top-k",
            "3",
            "--api-url",
            "http://testserver",
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        (
            "POST",
            f"/v1/knowledge-bases/{kb_id}/retrieve",
            {"query": "alpha", "top_k": 3},
        )
    ]
    assert '"content": "alpha"' in result.output


def test_document_cli_uses_document_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path, json_payload))
        return {"id": "doc-1", "status": "registered"}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    runner = CliRunner()
    kb_id = "00000000-0000-0000-0000-000000000008"
    document_id = "00000000-0000-0000-0000-000000000009"

    register_result = runner.invoke(
        cli_main.app,
        [
            "document",
            "register",
            kb_id,
            "--title",
            "Deployment Guide",
            "--source-uri",
            "object://local/docs/deployment.md",
            "--mime-type",
            "text/markdown",
            "--checksum",
            "sha256:abc",
            "--size-bytes",
            "1234",
            "--metadata",
            '{"source":"manual"}',
        ],
    )
    list_result = runner.invoke(cli_main.app, ["document", "list", kb_id])
    inspect_result = runner.invoke(cli_main.app, ["document", "inspect", document_id])

    assert register_result.exit_code == 0
    assert list_result.exit_code == 0
    assert inspect_result.exit_code == 0
    assert calls == [
        (
            "POST",
            f"/v1/knowledge-bases/{kb_id}/documents",
            {
                "title": "Deployment Guide",
                "source_uri": "object://local/docs/deployment.md",
                "mime_type": "text/markdown",
                "checksum": "sha256:abc",
                "size_bytes": 1234,
                "metadata": {"source": "manual"},
            },
        ),
        ("GET", f"/v1/knowledge-bases/{kb_id}/documents", None),
        ("GET", f"/v1/documents/{document_id}", None),
    ]


def test_document_upload_cli_uses_upload_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, str, Path, dict[str, str]]] = []

    def fake_request_file_json(
        method: str,
        path: str,
        *,
        api_url: str,
        file_path: Path,
        data: dict[str, str],
    ) -> object:
        calls.append((method, path, file_path, data))
        assert api_url == "http://testserver"
        return {"id": "doc-1", "status": "uploaded"}

    monkeypatch.setattr(cli_main, "_request_file_json", fake_request_file_json)
    kb_id = "00000000-0000-0000-0000-000000000011"
    document_path = tmp_path / "deploy.md"
    document_path.write_text("# Deploy\n")

    result = CliRunner().invoke(
        cli_main.app,
        [
            "document",
            "upload",
            kb_id,
            str(document_path),
            "--title",
            "Deploy Guide",
            "--metadata",
            '{"source":"manual"}',
            "--api-url",
            "http://testserver",
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        (
            "POST",
            f"/v1/knowledge-bases/{kb_id}/documents/upload",
            document_path,
            {"metadata": '{"source":"manual"}', "title": "Deploy Guide"},
        )
    ]
    assert '"status": "uploaded"' in result.output


def test_document_upload_cli_accepts_metadata_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, str, Path, dict[str, str]]] = []

    def fake_request_file_json(
        method: str,
        path: str,
        *,
        api_url: str,
        file_path: Path,
        data: dict[str, str],
    ) -> object:
        calls.append((method, path, file_path, data))
        return {"id": "doc-1", "status": "uploaded"}

    monkeypatch.setattr(cli_main, "_request_file_json", fake_request_file_json)
    kb_id = "00000000-0000-0000-0000-000000000011"
    document_path = tmp_path / "deploy.md"
    metadata_path = tmp_path / "metadata.json"
    document_path.write_text("# Deploy\n", encoding="utf-8")
    metadata_path.write_text('{"source":"example"}', encoding="utf-8")

    result = CliRunner().invoke(
        cli_main.app,
        [
            "document",
            "upload",
            kb_id,
            str(document_path),
            "--metadata",
            f"@{metadata_path}",
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        (
            "POST",
            f"/v1/knowledge-bases/{kb_id}/documents/upload",
            document_path,
            {"metadata": '{"source":"example"}'},
        )
    ]


def test_document_ingest_cli_uses_ingest_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path, json_payload))
        return {"id": "job-1", "status": "parsed"}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    document_id = "00000000-0000-0000-0000-000000000013"

    result = CliRunner().invoke(cli_main.app, ["document", "ingest", document_id])

    assert result.exit_code == 0
    assert calls == [("POST", f"/v1/documents/{document_id}/ingest", None)]
    assert '"status": "parsed"' in result.output


def test_ingestion_cli_uses_ingestion_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path, json_payload))
        return {"id": "job-1", "status": "parsed"}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    runner = CliRunner()
    document_id = "00000000-0000-0000-0000-000000000014"
    job_id = "00000000-0000-0000-0000-000000000015"

    list_result = runner.invoke(cli_main.app, ["ingestion", "list", document_id])
    inspect_result = runner.invoke(cli_main.app, ["ingestion", "inspect", job_id])

    assert list_result.exit_code == 0
    assert inspect_result.exit_code == 0
    assert calls == [
        ("GET", f"/v1/documents/{document_id}/ingestion-jobs", None),
        ("GET", f"/v1/ingestion-jobs/{job_id}", None),
    ]


def test_document_chunk_cli_uses_chunk_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path, json_payload))
        return [{"id": "chunk-1", "index": 0}]

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    document_id = "00000000-0000-0000-0000-000000000016"

    result = CliRunner().invoke(cli_main.app, ["document", "chunk", document_id])

    assert result.exit_code == 0
    assert calls == [("POST", f"/v1/documents/{document_id}/chunk", None)]
    assert '"index": 0' in result.output


def test_chunk_cli_uses_chunk_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path, json_payload))
        return [{"id": "chunk-1", "index": 0}]

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    runner = CliRunner()
    document_id = "00000000-0000-0000-0000-000000000017"
    chunk_id = "00000000-0000-0000-0000-000000000018"

    list_result = runner.invoke(cli_main.app, ["chunk", "list", document_id])
    inspect_result = runner.invoke(cli_main.app, ["chunk", "inspect", chunk_id])

    assert list_result.exit_code == 0
    assert inspect_result.exit_code == 0
    assert calls == [
        ("GET", f"/v1/documents/{document_id}/chunks", None),
        ("GET", f"/v1/document-chunks/{chunk_id}", None),
    ]


def test_document_index_cli_uses_index_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path, json_payload))
        return {"document_id": path.split("/")[3], "embedding_count": 2}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    document_id = "00000000-0000-0000-0000-000000000019"

    result = CliRunner().invoke(cli_main.app, ["document", "index", document_id])

    assert result.exit_code == 0
    assert calls == [("POST", f"/v1/documents/{document_id}/index", None)]
    assert '"embedding_count": 2' in result.output


def test_embedding_cli_uses_embedding_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path, json_payload))
        return [{"id": "embedding-1", "model": "mock-embedding-v1"}]

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    document_id = "00000000-0000-0000-0000-000000000020"

    result = CliRunner().invoke(cli_main.app, ["embedding", "list", document_id])

    assert result.exit_code == 0
    assert calls == [("GET", f"/v1/documents/{document_id}/embeddings", None)]
    assert '"model": "mock-embedding-v1"' in result.output


def test_memory_cli_uses_memory_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path, json_payload))
        assert api_url == "http://testserver"
        return {"id": "memory-1", "type": "user_preference"}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)
    runner = CliRunner()
    memory_id = "00000000-0000-0000-0000-000000000021"

    create_result = runner.invoke(
        cli_main.app,
        [
            "memory",
            "create",
            "--type",
            "user_preference",
            "--scope",
            "user:roy",
            "--content",
            '{"language":"zh"}',
            "--confidence",
            "0.9",
            "--metadata",
            '{"source":"manual"}',
            "--api-url",
            "http://testserver",
        ],
    )
    list_result = runner.invoke(
        cli_main.app,
        [
            "memory",
            "list",
            "--scope",
            "user:roy",
            "--type",
            "user_preference",
            "--limit",
            "10",
            "--api-url",
            "http://testserver",
        ],
    )
    inspect_result = runner.invoke(
        cli_main.app,
        ["memory", "inspect", memory_id, "--api-url", "http://testserver"],
    )
    delete_result = runner.invoke(
        cli_main.app,
        ["memory", "delete", memory_id, "--api-url", "http://testserver"],
    )

    assert create_result.exit_code == 0
    assert list_result.exit_code == 0
    assert inspect_result.exit_code == 0
    assert delete_result.exit_code == 0
    assert calls == [
        (
            "POST",
            "/v1/memory",
            {
                "type": "user_preference",
                "scope": "user:roy",
                "content": {"language": "zh"},
                "source_run_id": None,
                "confidence": 0.9,
                "metadata": {"source": "manual"},
            },
        ),
        ("GET", "/v1/memory?scope=user%3Aroy&type=user_preference&limit=10", None),
        ("GET", f"/v1/memory/{memory_id}", None),
        ("DELETE", f"/v1/memory/{memory_id}", None),
    ]
    assert '"type": "user_preference"' in create_result.output


def test_memory_create_cli_accepts_json_file_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, str, dict[str, object] | None]] = []
    content_path = tmp_path / "memory.json"
    content_path.write_text('{"language":"en","answer_style":"concise"}', encoding="utf-8")

    def fake_request_json(
        method: str,
        path: str,
        *,
        api_url: str,
        json_payload: dict[str, object] | None = None,
    ) -> object:
        calls.append((method, path, json_payload))
        return {"id": "memory-1", "type": "user_preference"}

    monkeypatch.setattr(cli_main, "_request_json", fake_request_json)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "memory",
            "create",
            "--type",
            "user_preference",
            "--scope",
            "user:example",
            "--content",
            f"@{content_path}",
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        (
            "POST",
            "/v1/memory",
            {
                "type": "user_preference",
                "scope": "user:example",
                "content": {"language": "en", "answer_style": "concise"},
                "source_run_id": None,
                "confidence": 1.0,
                "metadata": {},
            },
        )
    ]


def test_request_json_reports_actionable_api_unreachable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request(
        self: httpx.Client,
        method: str,
        url: str,
        *,
        json: dict[str, object] | None = None,
    ) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.Client, "request", fake_request)

    with pytest.raises(ClickException) as error_info:
        cli_main._request_json("GET", "/healthz", api_url="http://127.0.0.1:8000")

    message = str(error_info.value)
    assert "Could not reach Agent Kernel API at http://127.0.0.1:8000/healthz" in message
    assert "uv run agent-kernel-api" in message
    assert "AGENT_KERNEL_API_URL" in message
    assert "connection refused" in message


def test_request_file_json_reports_actionable_api_unreachable_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    document_path = tmp_path / "deploy.md"
    document_path.write_text("# Deploy\n", encoding="utf-8")

    def fake_request(
        self: httpx.Client,
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.Client, "request", fake_request)

    with pytest.raises(ClickException) as error_info:
        cli_main._request_file_json(
            "POST",
            "/v1/upload",
            api_url="http://127.0.0.1:8000",
            file_path=document_path,
            data={},
        )

    message = str(error_info.value)
    assert "Could not reach Agent Kernel API at http://127.0.0.1:8000/v1/upload" in message
    assert "curl http://127.0.0.1:8000/healthz" in message
    assert "AGENT_KERNEL_API_URL" in message
