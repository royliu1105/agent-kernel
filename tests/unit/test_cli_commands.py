from typing import Any

import pytest
from agent_kernel_cli import main as cli_main
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
