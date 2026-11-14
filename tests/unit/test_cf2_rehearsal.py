"""Safety and evidence contracts for the opt-in disposable CF2 harness."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from scripts import cf2_rehearsal as harness

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def fixture() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "cf2_runtime", ROOT / "tests/fixtures/cf2_runtime.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "project", ["agent-kernel-local", "agent-kernel", "", "agent-kernel-cf2-x"]
)
def test_refuse_non_disposable_project(project: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        harness.compose_config(project, tmp_path, "synthetic-password")


def test_config_has_only_owned_isolated_resources(tmp_path: Path) -> None:
    project = "agent-kernel-cf2-0123456789abcdef"
    config = harness.compose_config(project, tmp_path, "synthetic-password")
    assert config["networks"] == {"default": {"internal": True}}
    assert all(value == {} for value in config["volumes"].values())
    assert set(config["services"]) == {"api", "worker", "bootstrap", "postgres", "redis"}
    for name, service in config["services"].items():
        assert not set(service).intersection(
            {"ports", "network_mode", "container_name", "privileged"}
        )
        assert "agent-kernel-local" not in json.dumps(service)
        if name in {"api", "worker", "bootstrap"}:
            assert service["image"] == project + ":candidate"
            assert service["environment"]["AGENT_KERNEL_API_KEY_AUTH_ENABLED"] == "true"
            assert service["environment"]["OPENAI_API_KEY"] == ""
            assert service["environment"]["AGENT_KERNEL_EMBEDDING_PROVIDER"] == "mock"
            assert service["volumes"] == [
                f"{ROOT / 'tests/fixtures'}:/fixture:ro",
                f"{tmp_path}:/evidence",
                "objects:/objects",
            ]
    assert "resource/" in (ROOT / ".dockerignore").read_text().splitlines()


def test_host_environment_is_allowlisted() -> None:
    environment = dict.fromkeys(
        [
            "OPENAI_API_KEY",
            "AWS_SECRET_ACCESS_KEY",
            "DATABASE_URL",
            "AGENT_KERNEL_API_KEY",
            "COMPOSE_FILE",
            "COMPOSE_PROJECT_NAME",
            "COMPOSE_PROFILES",
            "HTTPS_PROXY",
            "PYTHONPATH",
        ],
        "do-not-inherit",
    )
    environment.update({"PATH": "/bin", "DOCKER_CONTEXT": "desktop-linux"})
    assert harness.clean_environment(environment) == {
        "PATH": "/bin",
        "DOCKER_CONTEXT": "desktop-linux",
    }


def test_collision_never_runs_cleanup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    calls: list[list[str]] = []

    def fake_run(args: list[str], *_: Any, **__: Any) -> str:
        calls.append(args)
        return "existing-container"

    monkeypatch.setattr(harness, "run", fake_run)
    with pytest.raises(RuntimeError, match="Refusing to reuse"):
        harness.main()
    assert len(calls) == 1
    assert calls[0][:3] == ["docker", "ps", "-aq"]


def test_failed_build_only_cleans_its_owned_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "active_identity", lambda _: [])
    for name in (
        "scripts/cf2_rehearsal.py",
        "tests/fixtures/cf2_runtime.py",
        "tests/fixtures/cf2_scenario.py",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# synthetic source\n")
    calls: list[list[str]] = []

    def fake_run(args: list[str], *_: Any, **__: Any) -> str:
        calls.append(args)
        if "build" in args:
            raise subprocess.CalledProcessError(1, args, stderr="synthetic build failure")
        return ""

    monkeypatch.setattr(harness, "run", fake_run)
    with pytest.raises(RuntimeError, match="restricted failure.log"):
        harness.main()
    cleanup = [call for call in calls if "down" in call]
    assert len(cleanup) == 1
    project = cleanup[0][cleanup[0].index("-p") + 1]
    assert project.startswith("agent-kernel-cf2-")
    assert cleanup[0][-3:] == ["down", "--volumes", "--remove-orphans"]
    private = tmp_path / ".agent-kernel" / project
    assert json.loads((private / "cleanup.json").read_text())["active_unchanged"] is True
    assert not (private / "compose.json").exists()
    assert not (private / "result.json").exists()
    assert not (private / "manifest.json").exists()


@pytest.mark.parametrize("number", [float("nan"), float("inf"), float("-inf")])
def test_digest_refuses_non_finite(fixture: ModuleType, number: float) -> None:
    with pytest.raises(ValueError):
        fixture.digest({"value": number})


def test_digest_preserves_array_order_and_normalizes_object_order(fixture: ModuleType) -> None:
    assert fixture.digest({"a": 1, "b": 2}) == fixture.digest({"b": 2, "a": 1})
    assert fixture.digest([1, 2]) != fixture.digest([2, 1])
    assert fixture.canonical({"b": [2, 1], "a": 1}) == b'{"a":1,"b":[2,1]}'


def test_effect_ledger_persists_not_just_in_memory(
    fixture: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(fixture, "EVIDENCE", tmp_path)
    fixture.append("effects.jsonl", {"item_id": "one"})
    fixture.append("effects.jsonl", {"item_id": "two"})
    assert [json.loads(line) for line in (tmp_path / "effects.jsonl").read_text().splitlines()] == [
        {"item_id": "one"},
        {"item_id": "two"},
    ]
    assert (tmp_path / "effects.jsonl").stat().st_mode & 0o777 == 0o600


def payload(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "model": "cf2-offline",
        "input": [
            {"role": "user", "content": [{"text": '{"case":"approved","kb_id":"synthetic-kb"}'}]},
            *[{"type": "function_call_output", "output": json.dumps(result)} for result in results],
        ],
    }


def test_fixture_sequence_uses_actual_retrieval_result(fixture: ModuleType) -> None:
    first = fixture.fixture_response(payload([]))["output"][0]
    assert first["name"] == "kb_search"
    assert json.loads(first["arguments"])["knowledge_base_id"] == "synthetic-kb"
    result = {
        "tool_name": "kb_search",
        "result": {
            "results": [
                {"content": "runtime passage", "citation": {"document_id": "runtime-document"}}
            ]
        },
    }
    second = fixture.fixture_response(payload([result]))["output"][0]
    assert second["name"] == "inventory_lookup"
    answer = fixture.fixture_response(
        payload(
            [
                result,
                {"tool_name": "inventory_lookup", "result": {"availability": "synthetic-only"}},
            ]
        )
    )["output"][0]
    assert json.loads(answer["content"][0]["text"])["citation"]["document_id"] == "runtime-document"


def test_fixture_does_not_make_up_a_citation_for_empty_retrieval(fixture: ModuleType) -> None:
    with pytest.raises(IndexError):
        fixture.fixture_response(
            payload(
                [
                    {"tool_name": "kb_search", "result": {"results": []}},
                    {"tool_name": "inventory_lookup", "result": {}},
                ]
            )
        )


def test_manifest_rejects_source_drift(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    (tmp_path / "candidate.py").write_text("changed")
    with pytest.raises(RuntimeError, match="Source changed"):
        harness.seal_evidence(tmp_path, {"files": {"candidate.py": "old-hash"}}, [])
    assert not (tmp_path / "manifest.json").exists()


def test_manifest_excludes_credentials_and_hashes_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    harness.write_json(tmp_path / "configuration.json", {"auth": True})
    harness.write_json(tmp_path / "credentials.json", {"key": "synthetic-secret"})
    harness.seal_evidence(tmp_path, {"files": {}}, ["synthetic-secret"])
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["configuration_sha256"] == hashlib.sha256(b'{"auth":true}').hexdigest()
    assert set(manifest["file_bytes_sha256"]) == {"configuration.json"}
    assert "synthetic-secret" not in json.dumps(manifest)


def test_manifest_refuses_and_redacts_accidental_secret(tmp_path: Path) -> None:
    (tmp_path / "containers.log").write_text("value=synthetic-secret")
    with pytest.raises(RuntimeError, match="Credential appeared"):
        harness.seal_evidence(tmp_path, {"files": {}}, ["synthetic-secret"])
    assert (tmp_path / "containers.log").read_text() == "value=<redacted>"
    assert not (tmp_path / "manifest.json").exists()
