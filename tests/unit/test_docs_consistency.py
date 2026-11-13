from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
LOCAL_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ENV_ASSIGNMENT_PATTERN = re.compile(r"^([A-Z][A-Z0-9_]+)=")
CURRENT_GUIDES = ("production-config.md", "security-hardening.md", "auth-rbac.md")
STATUS_GUIDES = (
    "README.md",
    "ROADMAP.md",
    "docs/README.md",
    "docs/development-plan.md",
    "docs/milestones.md",
    "docs/post-v0.1-plan.md",
    "docs/public-alpha.md",
    "docs/releases/public-alpha.md",
    "docs/releases/v1.0.0.md",
    "docs/v1-release-checklist.md",
    "docs/daily/day-90.md",
    "docs/hardening-verification.md",
    "docs/capability-hardening-plan.md",
)


def _local_markdown_links(path: Path) -> list[str]:
    links: list[str] = []
    for match in LOCAL_LINK_PATTERN.finditer(path.read_text(encoding="utf-8")):
        link = match.group(1).strip()
        if not link or link.startswith(("http://", "https://", "mailto:", "#")):
            continue
        links.append(link)
    return links


def _resolve_markdown_link(source: Path, link: str) -> Path:
    target = link.split("#", 1)[0]
    return (source.parent / target).resolve()


def _normalized(text: str) -> str:
    return " ".join(text.replace("`", "").split()).casefold()


def _section(filename: str, heading: str) -> str:
    text = (DOCS_ROOT / filename).read_text(encoding="utf-8")
    match = re.search(
        rf"^#{{2,3}} {re.escape(heading)}\n(.*?)(?=^#{{2,3}} |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"{filename}: missing section {heading!r}"
    return _normalized(match.group(1))


def test_docs_index_links_point_to_existing_files() -> None:
    checked_indexes = [
        DOCS_ROOT / "README.md",
        DOCS_ROOT / "daily" / "README.md",
    ]

    missing_links: list[str] = []
    for index_path in checked_indexes:
        for link in _local_markdown_links(index_path):
            target = _resolve_markdown_link(index_path, link)
            if not target.exists():
                missing_links.append(f"{index_path.relative_to(REPO_ROOT)} -> {link}")

    assert missing_links == []


def test_env_example_variables_are_documented() -> None:
    env_example = REPO_ROOT / ".env.example"
    configuration = DOCS_ROOT / "configuration.md"

    env_vars = {
        match.group(1)
        for line in env_example.read_text(encoding="utf-8").splitlines()
        if (match := ENV_ASSIGNMENT_PATTERN.match(line.strip()))
    }
    documented = configuration.read_text(encoding="utf-8")

    missing_vars = sorted(env_var for env_var in env_vars if f"`{env_var}`" not in documented)

    assert missing_vars == []


@pytest.mark.parametrize("filename", CURRENT_GUIDES)
def test_current_guide_links_point_to_existing_files(filename: str) -> None:
    source = DOCS_ROOT / filename
    missing = [
        link
        for link in _local_markdown_links(source)
        if not _resolve_markdown_link(source, link).is_file()
    ]
    assert missing == [], f"{filename}: broken links {missing}"


@pytest.mark.parametrize(
    ("auth", "token", "access"),
    [
        ("Disabled", "Unset/empty", "No application authentication; trusted local use only."),
        ("Disabled", "Configured", "Matching monitoring token required; otherwise HTTP 401."),
        ("Enabled", "Unset/empty", "HTTP 401 for every scrape (fails closed)."),
        ("Enabled", "Configured", "Matching monitoring token required; otherwise HTTP 401."),
    ],
)
def test_production_guide_keeps_complete_api_metrics_auth_matrix(
    auth: str, token: str, access: str
) -> None:
    section = _section("production-config.md", "API")
    assert _normalized(f"| {auth} | {token} | {access} |") in section


@pytest.mark.parametrize(
    ("filename", "heading"),
    [
        ("production-config.md", "API"),
        ("security-hardening.md", "Implemented Security Controls"),
        ("auth-rbac.md", "Object Scope"),
    ],
)
def test_current_guides_distinguish_monitoring_credentials_from_workspace_keys(
    filename: str, heading: str
) -> None:
    section = _section(filename, heading)
    for anchor in (
        "AGENT_KERNEL_MONITORING_TOKEN",
        "Authorization: Bearer <monitoring-token>",
        "workspace",
        "HTTP 401",
        "/healthz",
        "/readyz",
    ):
        assert _normalized(anchor) in section, f"{filename}: missing {anchor}"


@pytest.mark.parametrize(
    "variable",
    [
        "AGENT_KERNEL_WORKER_METRICS_ENABLED",
        "AGENT_KERNEL_WORKER_METRICS_HOST",
        "AGENT_KERNEL_WORKER_METRICS_PORT",
        "AGENT_KERNEL_EMBEDDING_PROVIDER",
    ],
)
def test_production_guide_documents_current_opt_in_defaults(variable: str) -> None:
    defaults = dict(
        line.strip().split("=", 1)
        for line in (REPO_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
        if ENV_ASSIGNMENT_PATTERN.match(line.strip())
    )
    guide = (DOCS_ROOT / "production-config.md").read_text(encoding="utf-8")
    assert f"{variable}={defaults[variable]}" in guide


@pytest.mark.parametrize(
    ("filename", "heading"),
    [
        ("production-config.md", "Worker Metrics"),
        ("security-hardening.md", "Implemented Security Controls"),
    ],
)
def test_current_guides_document_worker_metrics_boundary(filename: str, heading: str) -> None:
    section = _section(filename, heading)
    for anchor in (
        "opt-in",
        "AGENT_KERNEL_WORKER_METRICS_ENABLED=true",
        "AGENT_KERNEL_WORKER_METRICS_HOST=127.0.0.1",
        "AGENT_KERNEL_WORKER_METRICS_PORT=9001",
        "non-loopback",
        "32 ASCII characters",
        "loopback",
        "without a token permits unauthenticated scraping",
        "API scrapes do not include Worker process counters",
        "observability-operations.md",
    ):
        assert _normalized(anchor) in section, f"{filename}: missing {anchor}"


@pytest.mark.parametrize(
    ("filename", "heading"),
    [
        ("production-config.md", "API Authentication"),
        ("security-hardening.md", "Implemented Security Controls"),
        ("auth-rbac.md", "Object Scope"),
    ],
)
def test_current_guides_keep_workspace_and_operator_scope_boundaries(
    filename: str, heading: str
) -> None:
    section = _section(filename, heading)
    for anchor in (
        "knowledge",
        "document",
        "chunk",
        "embedding",
        "ingestion",
        "kb_search",
        "memory",
        "eval",
        "tool call",
        "run event",
        "/v1/usage",
        "/v1/usage/breakdown",
        "run:read",
        "NULL-owned",
        "workspace_id=None",
        "trusted local/operator access",
        "404",
        "403",
    ):
        assert _normalized(anchor) in section, f"{filename}: missing {anchor}"


@pytest.mark.parametrize("filename", ("production-config.md", "security-hardening.md"))
def test_current_guides_require_explicit_paid_embedding_selection(filename: str) -> None:
    guide = _normalized((DOCS_ROOT / filename).read_text(encoding="utf-8"))
    for anchor in (
        "AGENT_KERNEL_EMBEDDING_PROVIDER=mock",
        "AGENT_KERNEL_EMBEDDING_PROVIDER=openai",
        "OPENAI_API_KEY alone never enables paid embeddings",
    ):
        assert _normalized(anchor) in guide, f"{filename}: missing {anchor}"


def test_production_guide_tracks_existing_release_eval_gates() -> None:
    section = _section("production-config.md", "Evals")
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    ci = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "release-eval: cheap-eval" in makefile
    assert "run: make release-eval" in ci
    assert "make release-eval" in section
    for command in (
        "uv run agent-kernel eval report evals/rag-smoke.json",
        "uv run agent-kernel eval report evals/release-rag-gate.json",
        "uv run pytest tests/unit/test_tool_call_evals.py",
        "uv run python scripts/timeline_regression.py",
    ):
        assert command in makefile
        assert command in section
    for anchor in (
        "tests/unit/test_openai_provider.py",
        "tests/integration/test_openai_runtime_contract.py",
        "tests/integration/test_timeline_regression.py",
    ):
        assert (REPO_ROOT / anchor).is_file()
        assert anchor in section
    assert "alone does not establish that those additional tests passed" in section
    assert "release-eval-gates.md" in section
    assert "behavior-regression.md" in section


@pytest.mark.parametrize("filename", ("security-hardening.md", "auth-rbac.md"))
def test_security_guides_keep_isolation_regression_anchors(filename: str) -> None:
    guide = (DOCS_ROOT / filename).read_text(encoding="utf-8")
    for anchor in (
        "tests/integration/test_knowledge_workspace_isolation.py",
        "tests/integration/test_memory_eval_isolation.py",
        "tests/integration/test_operational_scope.py",
    ):
        assert (REPO_ROOT / anchor).is_file()
        assert anchor in guide, f"{filename}: missing {anchor}"


@pytest.mark.parametrize("filename", CURRENT_GUIDES)
def test_current_guides_do_not_restore_stale_rc_limitations(filename: str) -> None:
    # Historical release notes deliberately remain outside this current-guide check.
    guide = _normalized((DOCS_ROOT / filename).read_text(encoding="utf-8"))
    for stale in (
        "Worker HTTP metrics exposure is not implemented yet",
        "/metrics has no built-in authentication",
        "/healthz and /metrics are public from the application perspective",
        "Additional object-level scoping for every secondary resource is v1.0 RC hardening work",
        "release blocking gates, and eval job queues are not enabled",
        "Final object-level scoping audit for memory, tool calls, evals and observability records",
        "Scope memory and eval records in P1.2",
        "Finish P1.1 verification before claiming knowledge isolation accepted",
    ):
        assert _normalized(stale) not in guide, f"{filename}: stale claim {stale!r}"


@pytest.mark.parametrize("filename", STATUS_GUIDES)
def test_release_and_status_links_point_to_existing_files(filename: str) -> None:
    source = REPO_ROOT / filename
    missing = [
        link
        for link in _local_markdown_links(source)
        if not _resolve_markdown_link(source, link).exists()
    ]
    assert missing == [], f"{filename}: broken links {missing}"


def test_readme_distinguishes_published_release_from_current_hardening() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "releases/tag/v1.0.0" in readme
    assert "docs/capability-hardening-plan.md" in readme
    assert "unreleased changes" in readme
    assert "post-v1.0 capability hardening" in readme
    assert "Current v0.1 shape" not in readme
    assert "is in Public Alpha hardening" not in readme


@pytest.mark.parametrize(
    "filename",
    ("releases/v1.0.0.md", "v1-release-checklist.md"),
)
def test_release_records_keep_verified_publication_identity(filename: str) -> None:
    record = (DOCS_ROOT / filename).read_text(encoding="utf-8")
    for anchor in (
        "46849314d9f7740729fa9b3535fe06e9554366b6",
        "2026-08-07T11:29:59Z",
        "releases/tag/v1.0.0",
        "actions/runs/31122498218",
        "capability-hardening-plan.md",
        "unreleased",
    ):
        assert anchor in record, f"{filename}: missing {anchor}"
    assert "publication pending release commit" not in record.casefold()


def test_release_reconciliation_preserves_historical_limits_and_evidence_gaps() -> None:
    notes = (DOCS_ROOT / "releases/v1.0.0.md").read_text(encoding="utf-8")
    checklist = (DOCS_ROOT / "v1-release-checklist.md").read_text(encoding="utf-8")
    assert "320 passed" in notes
    assert "3 known high severity audit findings" in notes
    assert "historical" in notes
    assert "e797623707c3e888989255c4b5f008fc8a7e1ac8" in checklist
    assert (
        "- [ ] Working tree was clean before tagging: historical evidence unavailable." in checklist
    )
    assert "- [ ] Release branch was up to date before tagging:" in checklist
    assert "- [ ] Visual release-page rendering" in checklist


@pytest.mark.parametrize(
    "filename",
    (
        "phase-1-summary.md",
        "phase-2-summary.md",
        "phase-3-summary.md",
        "phase-4-summary.md",
        "phase-5-summary.md",
        "phase-6-summary.md",
        "public-alpha-summary.md",
        "beta-summary.md",
    ),
)
def test_phase_summaries_are_explicitly_historical(filename: str) -> None:
    record = (DOCS_ROOT / filename).read_text(encoding="utf-8")
    introduction = record.split("## Status", 1)[0]
    assert "Historical phase snapshot" in introduction
    assert "capability-hardening-plan.md" in introduction


def test_delivery_plan_no_longer_points_to_alpha_as_next_work() -> None:
    plan = (DOCS_ROOT / "post-v0.1-plan.md").read_text(encoding="utf-8")
    assert "Current track: Post-v1.0 capability hardening (unreleased)" in plan
    assert "## Historical Kickoff" in plan
    assert "## Next Daily Work" not in plan
    stage = _section("development-plan.md", "Stage 9: Day 76-90 v1.0 Release Candidate")
    assert "published 2026-08-07" in stage
    assert "- [ ] clean-machine" not in stage
