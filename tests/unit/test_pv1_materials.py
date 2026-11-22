"""Offline snapshot integrity; later content acceptance does not approve a pilot."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "docs/pilots/pv1-materials"


def test_pv1_accepted_prompt_is_pinned_separately_from_corpus() -> None:
    version = "pv1-runbook-assistant-v1"
    prompt = ROOT / f"docs/pilots/prompts/{version}.txt"
    raw = prompt.read_bytes()
    expected_hash = "bf6c5329a3e3bfa8587947b53a904fe4c3193444ad1f24a947305f163b1b091b"
    assert hashlib.sha256(raw).hexdigest() == expected_hash
    assert not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert re.findall(r"^([1-6])\. ", raw.decode("utf-8"), re.MULTILINE) == list("123456")
    contract = (ROOT / "docs/pilots/pv1-2026-11-15-runbook-assistant.md").read_text()
    assert expected_hash in contract and f"prompts/{version}.txt" in contract
    manifest = json.loads((PACK / "manifest.json").read_text())
    assert all(
        (PACK / item["path"]).resolve() != prompt.resolve()
        for item in manifest["corpus"] + manifest["artifacts"]
    )


def test_pv1_prompt_v2_cross_workspace_refuse_is_pinned() -> None:
    version = "pv1-runbook-assistant-v2"
    prompt = ROOT / f"docs/pilots/prompts/{version}.txt"
    raw = prompt.read_bytes()
    expected_hash = "f3946b22fc4bbafc7274602ced1342a19e30073e647847ad26872f2b0f7cb783"
    assert hashlib.sha256(raw).hexdigest() == expected_hash
    assert not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    text = raw.decode("utf-8")
    assert re.findall(r"^([1-8])\. ", text, re.MULTILINE) == list("12345678")
    assert "其他工作区" in text and "不得用当前知识库内容顶替" in text
    assert "完整终答文本" in text
    note = (ROOT / f"docs/pilots/prompts/{version}.md").read_text()
    assert expected_hash in note and f"{version}.txt" in note


def test_pv1_prompt_v3_multi_constraint_completeness_is_pinned() -> None:
    version = "pv1-runbook-assistant-v3"
    prompt = ROOT / f"docs/pilots/prompts/{version}.txt"
    raw = prompt.read_bytes()
    expected_hash = "70fbf3e26ce99243991e4063a078d5d0b5d6f4312eea45cf1a2154be3bf70e02"
    assert hashlib.sha256(raw).hexdigest() == expected_hash
    assert not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    text = raw.decode("utf-8")
    assert re.findall(r"^([1-9]|10)\. ", text, re.MULTILINE) == list("123456789")
    assert "多约束运维题必须按检索到的材料把要点答全" in text
    assert "默认本地捕获" in text and "另行配置、授权与收件验证" in text
    note = (ROOT / f"docs/pilots/prompts/{version}.md").read_text()
    assert expected_hash in note and "Agent task prompt" in note


def test_pv1_frozen_content_manifest_is_unchanged() -> None:
    # Preserve preparation labels/bytes; the contract records the later acceptance.
    frozen_hash = "0225553e4f626982fa4d7d71720d2d73f55d32bd40aab62385435b191bb605b2"
    assert hashlib.sha256((PACK / "manifest.json").read_bytes()).hexdigest() == frozen_hash
    contract = (ROOT / "docs/pilots/pv1-2026-11-15-runbook-assistant.md").read_text()
    assert frozen_hash in contract
    assert "20b8dc8a41bc3ada5386566fcc346392fd599324" in contract


def test_pv1_offline_inventory_is_file_size_not_billed_tokens() -> None:
    manifest = json.loads((PACK / "manifest.json").read_text())
    raw = [(PACK / item["path"]).read_bytes() for item in manifest["corpus"]]
    assert len(raw) == 12
    assert sum(len(value) for value in raw) == 14574
    assert sum(len(value.decode("utf-8")) for value in raw) == 6818
    questions = json.loads((PACK / "questions.json").read_text())
    assert sum(len(case["question"]) for case in questions["cases"]) == 603
    contract = (ROOT / "docs/pilots/pv1-2026-11-15-runbook-assistant.md").read_text()
    assert "12 files, 14574 bytes, 6818 Unicode code points" in contract
    assert "30 question strings contain 603 Unicode code points" in contract
    assert "not provider tokens" in contract


def test_pv1_manifest_integrity_and_source_ranges() -> None:
    manifest = json.loads((PACK / "manifest.json").read_text())
    assert manifest["status"] == "prepared_not_approved"
    assert manifest["preparation_authorized"] is True
    for key in ("corpus_approved", "transmission_authorized", "pv1_complete"):
        assert manifest[key] is False
    assert manifest["spending_authorized_usd"] == 0
    assert manifest["budget_ceiling_usd"] == 10
    assert {"accounts_and_region", "participants_and_dates", "real_read_only_tool_target"} <= set(
        manifest["pending"]
    )
    assert [d["id"] for d in manifest["corpus"]] == [f"D{i:02}" for i in range(1, 13)]
    corpus_paths = {d["path"] for d in manifest["corpus"]}
    assert corpus_paths == {str(p.relative_to(PACK)) for p in (PACK / "corpus").glob("*.md")}
    for doc in manifest["corpus"]:
        source = ROOT / doc["source_path"]
        assert source.resolve().is_relative_to(ROOT / "docs")
        assert hashlib.sha256(source.read_bytes()).hexdigest() == doc["source_sha256"]
        lines = source.read_text().splitlines()
        for start, end in doc["source_line_ranges"]:
            assert 1 <= start <= end <= len(lines)
        assert doc["human_review"] == "pending"
        for extra in doc.get("supporting_sources", []):
            extra_path = ROOT / extra["path"]
            assert extra_path.resolve().is_relative_to(ROOT / "docs")
            assert hashlib.sha256(extra_path.read_bytes()).hexdigest() == extra["sha256"]
            for start, end in extra["line_ranges"]:
                assert 1 <= start <= end <= len(extra_path.read_text().splitlines())
        body = (PACK / doc["path"]).read_text()
        assert re.findall(r"^## (D\d{2}-S\d+):", body, re.MULTILINE) == doc["sections"]
    for item in manifest["corpus"] + manifest["artifacts"]:
        path = PACK / item["path"]
        assert path.resolve().is_relative_to(PACK)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    assert not corpus_paths & {a["path"] for a in manifest["artifacts"]}


def test_pv1_answer_inventory_and_evidence() -> None:
    manifest = json.loads((PACK / "manifest.json").read_text())
    answers = json.loads((PACK / "reviewer/answer-key.json").read_text())
    questions = json.loads((PACK / "questions.json").read_text())
    readable = (PACK / "reviewer/expected-answers.md").read_text()
    assert answers["model_outputs_seen"] is False
    assert answers["version"] == questions["version"] == manifest["version"]
    assert answers["status"] == questions["status"] == "prepared_not_approved"
    expected = [
        f"{p}{i:02}" for p, n in (("A", 18), ("U", 6), ("I", 3), ("X", 3)) for i in range(1, n + 1)
    ]
    assert [c["id"] for c in answers["cases"]] == expected
    assert questions["cases"] == [
        {k: c[k] for k in ("id", "cohort", "question")} for c in answers["cases"]
    ]
    sections = {s for d in manifest["corpus"] for s in d["sections"]}
    for case in answers["cases"]:
        assert case["cohort"] == case["id"][0]
        assert case["result"] == "not_run" and case["review_status"] == "pending"
        assert case["expected_facts"] and case["fail_if"] and case["required_observations"]
        assert case["evidence"] and set(case["evidence"]) <= sections
        heading = f"## {case['id']}: {case['question']}\n"
        assert readable.count(heading) == 1
        section = readable.split(heading, 1)[1].split("\n## ", 1)[0]
        assert all(fact in section for fact in case["expected_facts"])
        assert all(condition in section for condition in case["fail_if"])
        assert all(observation in section for observation in case["required_observations"])
        if case["cohort"] in {"I", "X"}:
            assert case["fixture"]["setup"] and case["fixture"]["observe"]
            assert json.dumps(case["fixture"], ensure_ascii=False, separators=(",", ":")) in section


def test_pv1_corpus_excludes_answers_and_obvious_private_material() -> None:
    for path in (PACK / "corpus").glob("*.md"):
        body = path.read_text()
        for forbidden in (
            "/Users/",
            "/var/folders/",
            "resource/",
            "PV1_B_PRIVATE_SENTINEL",
            "PV1_SYNTHETIC_SECRET",
            "collector.example.test",
            "expected_facts",
            "BEGIN PRIVATE KEY",
            "uv run agent-kernel-api",
            "npm run web:dev",
        ):
            assert forbidden not in body, path
        assert not re.search(r"(?:sk-|ghp_)[A-Za-z0-9_-]{20,}", body)
        assert not re.search(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", body)
    for path in PACK.rglob("*.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text()):
            assert not target.startswith(("http:", "https:"))
            assert (path.parent / target.split("#", 1)[0]).is_file()
