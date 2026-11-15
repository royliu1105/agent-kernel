"""In-memory request-shape checks, never pilot execution or model behavior evals."""

from __future__ import annotations

import hashlib
import json
import re
import socket
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from agent_kernel_api.schemas import (
    AgentCreateRequest,
    ApprovalApproveRequest,
    ApprovalRejectRequest,
    RunCreateRequest,
    RunResumeRequest,
)
from agent_kernel_cli import main as cli_main
from kernel_core import Run
from kernel_identity import Permission, WorkspaceRole
from kernel_identity.authorizer import ROLE_PERMISSIONS
from kernel_providers import DeepSeekProvider
from kernel_providers.openai import _request_payload
from kernel_rag.chunking import TextChunker
from kernel_rag.parsers import TextMarkdownParser
from kernel_runtime.execution import _model_refs_from_run, _request_from_run
from kernel_runtime.native_state import ExecutionLimits
from kernel_runtime.router import ModelRouter
from pydantic import ValidationError
from typer.testing import CliRunner

PILOTS = Path(__file__).resolve().parents[2] / "docs/pilots"
AGENT_ID = UUID("00000000-0000-4000-8000-000000000001")
KB_ID = UUID("00000000-0000-4000-8000-000000000002")
APPROVAL_ID = UUID("00000000-0000-4000-8000-000000000003")


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Offline preparation must not open network connections.")

    monkeypatch.setattr(socket.socket, "connect", fail)
    monkeypatch.setattr(socket.socket, "connect_ex", fail)
    monkeypatch.setattr(socket, "create_connection", fail)


def _template() -> dict[str, Any]:
    value: dict[str, Any] = json.loads((PILOTS / "pv1-offline-request-template.json").read_text())
    return value


def _finalized_profile() -> dict[str, Any]:
    document = (PILOTS / "pv1-2026-11-15-runbook-assistant.md").read_text()
    section = document.split("## Finalized Technical Profile\n", 1)[1].split("\n## ", 1)[0]
    blocks = re.findall(r"```json\n(.*?)\n```", section, re.DOTALL)
    assert len(blocks) == 1
    value: dict[str, Any] = json.loads(blocks[0])
    return value


def test_finalized_profile_uses_existing_limits_and_request_serialization() -> None:
    profile = _finalized_profile()
    assert profile["version"] == "pv1-config-v1"
    assert profile["implementation_sha"] == "21c54217c426a6c6ef7384edf22e32a4ca8334b7"
    assert profile["model"] == "deepseek:deepseek-flash"
    assert profile["fallback_models"] == []
    assert profile["generation_base_url"] == "https://api.deepseek.com"
    assert profile["embedding_base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert profile["embedding_provider"] == "dashscope"
    assert (profile["embedding_model"], profile["embedding_dimensions"]) == (
        "text-embedding-v3",
        1024,
    )
    limits = ExecutionLimits.from_env(profile["first_batch_environment"])
    assert limits.max_model_calls == profile["budget"]["attempts_per_task"] == 2
    assert limits.max_tool_calls == 8
    assert limits.max_active_seconds == 120
    assert limits.max_total_tokens == 32000
    assert limits.max_output_tokens == profile["budget"]["output_tokens_per_attempt"] == 2048
    assert limits.max_history_bytes == 262144
    assert profile["compose_project"] == "agent-kernel-pv1"
    assert profile["api_bind"] == "127.0.0.1:18080:8000"
    assert profile["active_runs"] == 1
    assert (profile["github_run_id"], profile["github_run_attempt"]) == (43634747295, 1)
    assert profile["github_api_version"] == "2022-11-28"
    assert profile["github_timeout_ms"] == 10000
    assert profile["github_max_response_bytes"] == 32768
    assert profile["tool_max_result_bytes"] == 65536

    body = _body("How do I start the local stack?")
    body["input"]["model"] = profile["model"]
    body["input"]["fallback_models"] = profile["fallback_models"]
    parsed = RunCreateRequest.model_validate(body)
    run = Run(agent_id=AGENT_ID, input=parsed.input)
    assert _model_refs_from_run(run, default_model="mock:unused") == (profile["model"],)
    request = _request_from_run(run, default_model="mock:unused")
    router = ModelRouter(
        {"deepseek": DeepSeekProvider(api_key="", base_url=profile["generation_base_url"])}
    )
    route = router.route(request.model)
    assert route.provider_name == "deepseek"
    wire = _request_payload(
        request.model_copy(update={"model": route.model, "max_output_tokens": 2048}),
        provider_name=route.provider_name,
    )
    assert wire["model"] == "deepseek-flash"
    assert wire["max_output_tokens"] == 2048
    assert "reasoning" not in wire
    assert "store" not in wire


def test_first_batch_decimal_forecast_and_reservations_fit_without_discounts() -> None:
    budget = _finalized_profile()["budget"]
    tasks = budget["tasks"]
    attempts = tasks * budget["attempts_per_task"]
    assert tasks == 5 and attempts == 10
    input_tokens = attempts * budget["input_tokens_per_attempt_forecast"]
    output_tokens = attempts * budget["output_tokens_per_attempt"]
    million = Decimal(1000000)
    usd = (
        input_tokens * Decimal(budget["generation_input_usd_per_million"])
        + output_tokens * Decimal(budget["generation_output_usd_per_million"])
    ) / million
    cny = (
        input_tokens * Decimal(budget["generation_input_cny_per_million"])
        + output_tokens * Decimal(budget["generation_output_cny_per_million"])
    ) / million
    embedding_cny = (
        budget["embedding_tokens_forecast"] * Decimal(budget["embedding_cny_per_million"])
    ) / million
    stress = Decimal(budget["stress_reserve_usd_per_cny"])
    assert usd == Decimal("0.12288")
    assert cny == Decimal("0.81920")
    assert embedding_cny == Decimal("0.02500")
    total = max(usd, cny * stress) + embedding_cny * stress
    assert total == Decimal("0.84420")
    task_reserve = Decimal(budget["task_reserve_usd"])
    embedding_reserve = Decimal(budget["embedding_reserve_usd"])
    ceiling = Decimal(budget["batch_ceiling_usd"])
    assert max(usd, cny * stress) / tasks + embedding_cny * stress < task_reserve
    assert embedding_cny * stress < embedding_reserve
    assert total < tasks * task_reserve + embedding_reserve
    assert (
        tasks * task_reserve + embedding_reserve + Decimal(budget["locked_reserve_usd"]) == ceiling
    )
    assert ceiling == Decimal("2.00")


def test_frozen_corpus_chunk_inventory_matches_budget_basis() -> None:
    profile = _finalized_profile()
    root = PILOTS / "pv1-materials"
    manifest = json.loads((root / "manifest.json").read_text())
    parser = TextMarkdownParser()
    chunker = TextChunker(
        chunk_size_chars=profile["chunk_size"], chunk_overlap_chars=profile["chunk_overlap"]
    )
    chunks = [
        chunk
        for item in manifest["corpus"]
        for chunk in chunker.chunk(
            parser.parse(content=(root / item["path"]).read_bytes(), filename=item["path"]).text
        )
    ]
    assert len(manifest["corpus"]) == len(chunks) == 12
    assert sum(len(chunk.content.encode()) for chunk in chunks) == 14574
    assert max(len(chunk.content.encode()) for chunk in chunks) == 1654
    assert profile["top_k"] == 5


def _body(question: str) -> dict[str, Any]:
    template = _template()
    task = deepcopy(template["task_template"])
    task.update(question=question, knowledge_base_id=str(KB_ID))
    body: dict[str, Any] = deepcopy(template["run_create_body_template"])
    body["input"]["messages"][0]["content"] = (PILOTS / template["prompt"]["path"]).read_text()
    body["input"]["messages"][1]["content"] = json.dumps(task, ensure_ascii=False)
    return body


def test_artifact_keeps_authority_and_evidence_closed() -> None:
    template = _template()
    assert template["status"] == "prepared_not_executed"
    assert template["execution_authorized"] is template["transmission_authorized"] is False
    assert template["spending_authorized_usd"] == 0
    assert template["question_source"] == "pv1-materials/questions.json"
    assert template["example_case_id"] == "A01"
    assert len(template["evidence_cases"]) == 6
    assert {case["id"] for case in template["evidence_cases"]} == {
        "before_approval",
        "reject_then_resume",
        "approve_then_resume",
        "duplicate_concurrent_resume",
        "new_executor_resume",
        "observer_failure_or_timeout",
    }
    assert all(case["result"] == "not_run" for case in template["evidence_cases"])
    prompt = template["prompt"]
    assert prompt["version"] == "pv1-runbook-assistant-v1"
    assert prompt["sha256"] == hashlib.sha256((PILOTS / prompt["path"]).read_bytes()).hexdigest()


def test_all_question_shapes_preserve_prompt_without_calling_a_provider() -> None:
    template = _template()
    questions = json.loads((PILOTS / template["question_source"]).read_text())
    prompt = (PILOTS / template["prompt"]["path"]).read_text()
    assert len(questions["cases"]) == 30
    for case in questions["cases"]:
        body = _body(case["question"])
        parsed = RunCreateRequest.model_validate(body)
        assert set(parsed.input) == {"model", "fallback_models", "messages"}
        run = Run(agent_id=AGENT_ID, input=parsed.input)
        assert _model_refs_from_run(run, default_model="mock:unused") == ("mock:pv1-offline",)
        request = _request_from_run(run, default_model="mock:unused")
        wire = _request_payload(request)
        assert wire["input"][0]["role"] == "system"
        assert wire["input"][0]["content"][0]["text"] == prompt
        task = json.loads(wire["input"][1]["content"][0]["text"])
        assert task == {"question": case["question"], "knowledge_base_id": str(KB_ID), "top_k": 5}
        assert "{{" not in json.dumps(wire)
        assert request.tools == ()  # Assembly is not registry binding or retrieval.


def test_messages_take_precedence_over_task() -> None:
    payload = _body("Question")["input"]
    payload["task"] = "This task is ignored when messages is a list."
    request = _request_from_run(Run(agent_id=AGENT_ID, input=payload), default_model="mock:unused")
    assert len(request.messages) == 2
    assert all(message.content != payload["task"] for message in request.messages)


def test_agent_creation_does_not_accept_prompt_binding() -> None:
    with pytest.raises(ValidationError):
        AgentCreateRequest.model_validate({"name": "PV1", "prompt_id": str(AGENT_ID)})


def test_cli_wraps_inner_input_once_without_http(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []

    def capture(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        assert method == "POST" and path == f"/v1/agents/{AGENT_ID}/runs"
        assert kwargs["api_url"] == "http://pv1.invalid"
        captured.append(kwargs["json_payload"])
        return {"status": "created"}

    monkeypatch.setattr(cli_main, "_request_json", capture)
    body = _body("Offline shape check")
    result = CliRunner().invoke(
        cli_main.app,
        [
            "run",
            "create",
            str(AGENT_ID),
            "--input",
            json.dumps(body["input"]),
            "--api-url",
            "http://pv1.invalid",
        ],
    )
    assert result.exit_code == 0, result.output
    assert captured == [body]


def test_decision_bodies_are_schema_valid_not_executed() -> None:
    template = _template()
    assert ApprovalApproveRequest.model_validate(template["approve_body_template"]).decision_note
    assert ApprovalRejectRequest.model_validate(template["reject_body_template"]).reason
    with pytest.raises(ValidationError):
        RunResumeRequest.model_validate(template["resume_body_template"])
    assert (
        RunResumeRequest.model_validate({"approval_id": str(APPROVAL_ID)}).approval_id
        == APPROVAL_ID
    )


def test_identity_matrix_does_not_claim_separation_of_duties() -> None:
    operator = ROLE_PERMISSIONS[WorkspaceRole.OPERATOR]
    viewer = ROLE_PERMISSIONS[WorkspaceRole.VIEWER]
    assert {Permission.RUN_WRITE, Permission.APPROVAL_REVIEW} <= operator
    assert Permission.RUN_READ in viewer
    assert Permission.RUN_WRITE not in viewer
    assert Permission.APPROVAL_REVIEW not in viewer


def _evidence_template() -> dict[str, Any]:
    value: dict[str, Any] = json.loads((PILOTS / "pv1-evidence-template.json").read_text())
    return value


def test_evidence_form_has_no_authorization_or_observed_results() -> None:
    template = _evidence_template()
    assert template["version"] == "pv1-evidence-template-v1"
    assert template["status"] == "draft_not_executed"
    assert (PILOTS / template["specification"]).is_file()
    assert template["authority"] == {
        "harness_implementation_authorized": False,
        "environment_creation_authorized": False,
        "pilot_query_authorized": False,
        "provider_transmission_authorized": False,
        "spending_authorized_usd": 0,
        "deepseek_official_reply": "pending",
        "authorization_reference": None,
    }
    assert template["records"] == []
    record = template["record_shape"]
    assert record["behavior_verdict"] == record["case_verdict"] == "not_run"
    for key, value in record.items():
        if key not in {"behavior_verdict", "case_verdict"}:
            assert value is None or value == [], key
    for name in ("executor_shape", "journal_event_shape"):
        assert all(value is None for value in template[name].values())
    assert template["artifact_shape"] == {
        "reference": None,
        "sha256": None,
        "evidence_kind": None,
        "access": "private",
    }


def test_evidence_plan_covers_all_existing_groups_and_second_legitimate_call() -> None:
    template = _evidence_template()
    cases = template["case_plan"]
    expected = {
        "before_approval": 0,
        "reject_then_resume": 0,
        "approve_then_resume": 1,
        "duplicate_concurrent_resume": 1,
        "new_executor_resume": 1,
        "second_legitimate_approved_call": 1,
        "observer_failure_or_timeout": None,
    }
    assert len(cases) == len(expected)
    assert {case["id"]: case["expected_dispatches_per_tool_call"] for case in cases} == expected
    assert {case["id"] for case in _template()["evidence_cases"]} == (
        set(expected) - {"second_legitimate_approved_call"}
    )
    controls = template["fixture_control_plan"]
    control_ids = {
        "known_dispatch",
        "duplicate_dispatch",
        "missing_executor",
        "journal_before_send",
        "journal_after_send",
        "crash_after_start",
        "incomplete_response",
        "binding_and_guards",
    }
    assert len(controls) == len(control_ids)
    assert {control["id"] for control in controls} == control_ids
    assert all(item["result"] == "not_run" for item in cases + controls)
    spec = (PILOTS / template["specification"]).read_text()
    assert all(f"| {name} |" in spec for name in set(expected) | control_ids)


def test_evidence_form_retains_required_correlation_and_coverage_fields() -> None:
    template = _evidence_template()
    required = {
        "record_shape": {
            "case_id",
            "evidence_class",
            "run_id",
            "tool_call_id",
            "approval_id",
            "prior_case_references",
            "executor_manifest",
            "journal_artifacts",
            "window_start_utc",
            "window_end_utc",
            "coverage_complete",
            "in_flight_at_close",
            "observed_dispatch_starts",
            "observed_validated_responses",
            "response_identity",
            "persisted_state_artifacts",
            "initial_request_artifacts",
            "resumed_request_artifacts",
            "limits_and_counter_artifacts",
            "private_response_artifacts",
            "tool_outcome",
            "behavior_verdict",
            "case_verdict",
            "missing_evidence",
            "reviewer_reference",
        },
        "executor_shape": {
            "executor_id",
            "kind",
            "configuration_sha256",
            "hook_attestation_artifact",
            "window_start_utc",
            "window_end_utc",
            "last_sequence",
            "journal_record_count",
            "close_marker_present",
        },
        "journal_event_shape": {
            "event",
            "case_id",
            "run_id",
            "tool_call_id",
            "executor_id",
            "sequence",
            "attempt_id",
            "timestamp_utc",
            "method",
            "fixed_path",
            "http_status",
            "github_request_id",
            "body_complete",
            "validation_outcome",
            "error_code",
        },
    }
    for section, fields in required.items():
        assert fields <= template[section].keys(), section
    assert set(template["journal_event_shape"]) == required["journal_event_shape"]


def test_evidence_provenance_preserves_frozen_inputs_and_unknown_target_fields() -> None:
    template = _evidence_template()
    provenance = template["provenance"]
    assert provenance["prompt_version"] == _template()["prompt"]["version"]
    assert provenance["prompt_sha256"] == _template()["prompt"]["sha256"]
    manifest_bytes = (PILOTS / "pv1-materials/manifest.json").read_bytes()
    assert provenance["materials_manifest_sha256"] == hashlib.sha256(manifest_bytes).hexdigest()
    assert provenance["materials_version"] == json.loads(manifest_bytes)["version"]
    for key in (
        "candidate_sha",
        "lock_sha256",
        "sanitized_config_sha256",
        "harness_sha256",
        "operation_definition_sha256",
    ):
        assert provenance[key] is None
    assert provenance["image_digests"] == []
    assert template["target"] == {
        "repository": "royliu1105/agent-kernel",
        "run_id": 43634747295,
        "head_sha": "2bb3f4ab1d50afa1cc2686b42b1ebcaf5db1f726",
        "run_attempt": None,
        "api_version": None,
        "proposed_timeout_ms": 10000,
        "effective_timeout_ms": None,
        "exclude_pull_requests": True,
        "max_response_bytes": 32768,
        "max_result_bytes": 65536,
    }
