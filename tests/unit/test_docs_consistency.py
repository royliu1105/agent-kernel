from __future__ import annotations

import re
from pathlib import Path

import pytest
from kernel_runtime.native_state import ExecutionLimits

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
    "docs/archive/public-alpha.md",
    "docs/releases/public-alpha.md",
    "docs/releases/v1.0.0.md",
    "docs/v1-release-checklist.md",
    "docs/archive/daily/day-90.md",
    "docs/hardening-verification.md",
    "docs/capability-hardening-plan.md",
    "docs/real-scenario-pilot-plan.md",
    "docs/pilot-learning-guide.md",
    "docs/pilots/pv1-2026-11-15-runbook-assistant.md",
    "docs/pilots/pv1-offline-rehearsal.md",
    "docs/pilots/pv1-harness-spec.md",
    "docs/pilots/pv1-authorization-2026-11-15.md",
    "docs/reference-follow-up-plan.md",
    "docs/observability-completion-plan.md",
    "docs/reviews/2026-11-14-cf2-workflow-inventory.md",
    "docs/provider-compatibility.md",
    "docs/specs/pilot-provider-compatibility.md",
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
        DOCS_ROOT / "project-overview.md",
        DOCS_ROOT / "local-paid-experience.md",
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


def test_postgresql_only_contract_is_documented() -> None:
    guide = (DOCS_ROOT / "postgresql-only.md").read_text()
    for term in (
        "DATABASE_URL",
        "AGENT_KERNEL_TEST_POSTGRES_URL",
        "make test-db-up",
        "make test-db-down",
        "No new schema revision",
        "unreleased compatibility change",
    ):
        assert term in guide
    for relative in ("README.md", "CONTRIBUTING.md", "docs/development-environment.md"):
        content = (REPO_ROOT / relative).read_text()
        assert "make test-db-up" in content
        assert "postgresql-only.md" in content
    for relative in ("examples/README.md", "examples/public-alpha-walkthrough.md"):
        content = (REPO_ROOT / relative).read_text()
        assert "make docker-up" in content
        assert "unset DATABASE_URL" not in content
        assert "npm run web:dev" not in content
    ci = (REPO_ROOT / ".github/workflows/ci.yml").read_text()
    assert "AGENT_KERNEL_TEST_POSTGRES_URL" in ci
    assert "POSTGRES_DB: agent_kernel_test" in ci
    assert "sqlite" not in ci.lower()
    for link in _local_markdown_links(DOCS_ROOT / "postgresql-only.md"):
        assert _resolve_markdown_link(DOCS_ROOT / "postgresql-only.md", link).is_file()


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
    assert "docs/real-scenario-pilot-plan.md" in readme
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
        "archive/phase-1-summary.md",
        "archive/phase-2-summary.md",
        "archive/phase-3-summary.md",
        "archive/phase-4-summary.md",
        "archive/phase-5-summary.md",
        "archive/phase-6-summary.md",
        "archive/public-alpha-summary.md",
        "archive/beta-summary.md",
    ),
)
def test_phase_summaries_are_explicitly_historical(filename: str) -> None:
    record = (DOCS_ROOT / filename).read_text(encoding="utf-8")
    introduction = record.split("## Status", 1)[0]
    assert "Historical phase snapshot" in introduction
    assert "capability-hardening-plan.md" in introduction


def test_delivery_plan_no_longer_points_to_alpha_as_next_work() -> None:
    plan = (DOCS_ROOT / "post-v0.1-plan.md").read_text(encoding="utf-8")
    assert (
        "Current track: Real-scenario acceptance and controlled pilot (see PV1-PV6 ledger)" in plan
    )
    assert "Current branch enhancements: Unreleased" in plan
    assert "## Historical Kickoff" in plan
    assert "## Next Daily Work" not in plan
    stage = _section("development-plan.md", "Stage 9: Day 76-90 v1.0 Release Candidate")
    assert "published 2026-08-07" in stage
    assert "- [ ] clean-machine" not in stage


def test_project_overview_links_evidence_without_a_second_pilot_ledger() -> None:
    overview = (DOCS_ROOT / "project-overview.md").read_text(encoding="utf-8")
    for evidence in (
        "real-scenario-pilot-plan.md",
        "reference-follow-up-plan.md",
        "local-paid-experience.md",
        "pilots/pv2-closure.md",
        "pilots/pv2-web-acceptance.md",
        "reviews/cf1-risk-disposition.md",
        "pilot-learning-guide.md",
    ):
        assert evidence in overview
    assert not re.findall(r"^\| (PV[1-6]) \|", overview, flags=re.MULTILINE)
    assert "external_response_review_required" in overview
    for entry in (REPO_ROOT / "README.md", REPO_ROOT / "ROADMAP.md", DOCS_ROOT / "README.md"):
        text = entry.read_text(encoding="utf-8")
        assert "project-overview.md" in text
        assert "PV1 contract preparation is in progress" not in text
        assert "PV2-PV6 have not started" not in text


def test_local_walkthrough_keeps_failure_and_evidence_limits_explicit() -> None:
    boundary = _section("local-paid-experience.md", "Documentation-Only Commit Boundary")
    assert "does not ship those runtime changes" in boundary
    assert "response_sha256" in boundary
    assert "are not available" in boundary
    assert "separately reviewed implementation commit" in boundary
    implementation = _section("local-paid-experience.md", "Separate Implementation Follow-Up")
    assert "current docker images remain unchanged" in implementation
    assert "private-evidence repair remains paused and unimplemented" in implementation
    failure = _section("local-paid-experience.md", "Observed Approval and Failed Continuation")
    for marker in (
        "external_response_review_required",
        "no final ci answer",
        "not an independent socket-level",
        "reviewed_by=null",
    ):
        assert marker in failure
    inspection = _section("local-paid-experience.md", "Subsequent Read-Only Response Inspection")
    assert "did not preserve its raw response body" in inspection
    assert "not a root-cause finding" in inspection
    pending = _section("local-paid-experience.md", "Remaining Work and Current Hold")
    assert "not implemented" in pending
    assert "no automatic whitelist changes" in pending
    assert "no paid calls" in pending


@pytest.mark.parametrize(
    "filename",
    (
        "README.md",
        "ROADMAP.md",
        "docs/README.md",
        "docs/development-plan.md",
        "docs/milestones.md",
        "docs/post-v0.1-plan.md",
        "docs/daily/README.md",
        "docs/capability-hardening-plan.md",
    ),
)
def test_current_planning_entries_link_to_the_pilot_plan(filename: str) -> None:
    text = (REPO_ROOT / filename).read_text(encoding="utf-8")
    assert "real-scenario-pilot-plan.md" in text


def test_pilot_plan_has_one_complete_task_ledger() -> None:
    plan = (DOCS_ROOT / "real-scenario-pilot-plan.md").read_text(encoding="utf-8")
    task_ids = re.findall(r"^\| (PV[1-6]) \|", plan, flags=re.MULTILINE)
    assert task_ids == [f"PV{index}" for index in range(1, 7)]
    for task_id in task_ids:
        assert f"### {task_id}:" in plan
    progress = _section("real-scenario-pilot-plan.md", "Priority and Progress")
    assert "dependency" in progress
    assert "evidence" in progress


def test_pilot_plan_keeps_expansion_and_paid_execution_boundaries() -> None:
    scope = _section("real-scenario-pilot-plan.md", "Objective and Scope Freeze")
    assert "do not start another foundation-development phase" in scope
    assert "no production writes" in scope
    assert "separate scope decision" in scope
    budget = _section("real-scenario-pilot-plan.md", "Budget, Privacy and Stop Conditions")
    for anchor in (
        "estimated_cost=0",
        "not billing enforcement",
        "explicit approval",
        "80%",
        "usage is unknown",
        "immediately pause",
        "cannot undo remote effects or charges",
    ):
        assert _normalized(anchor) in budget


def test_pv1_draft_case_inventory_matches_the_pilot_cohorts() -> None:
    draft = (DOCS_ROOT / "pilots/pv1-2026-11-15-runbook-assistant.md").read_text(encoding="utf-8")
    case_ids = re.findall(r"^\| ([AUIX][0-9]{2}) \|", draft, flags=re.MULTILINE)
    expected = [
        f"{prefix}{index:02}"
        for prefix, count in (("A", 18), ("U", 6), ("I", 3), ("X", 3))
        for index in range(1, count + 1)
    ]
    assert case_ids == expected
    assert "question ideas only" in draft


def test_pv1_draft_records_decisions_without_implying_paid_or_runtime_acceptance() -> None:
    filename = "pilots/pv1-2026-11-15-runbook-assistant.md"
    authorization = _section(filename, "Authorization and Candidate")
    assert "at most usd 2 within usd 10" in authorization
    assert (
        "choosing a model or a proposed budget is not authorization to consume it" in authorization
    )
    budget = _section(filename, "Budget and First-Batch Authorization")
    assert "current first-batch spending authorization is **usd 2**" in budget
    assert "usd 10 ceiling selected by the maintainer" in budget
    assert "at usd 8" in budget
    models = _section(filename, "Model Decision and Read-Only Configuration Findings")
    assert "selected providers are not live-accepted" in models
    assert "configuration/integration blocker" in models
    assert "no credential was copied, exported, submitted to a service" in models


def test_pv1_github_candidate_preserves_access_and_evidence_gates() -> None:
    section = " ".join(
        _section("pilots/pv1-2026-11-15-runbook-assistant.md", heading)
        for heading in (
            "GitHub CI Read-Only Candidate",
            "Operation and Access",
            "Response Boundary",
            "Independent Invocation Evidence",
            "Remaining Entry Decisions",
        )
    )
    for phrase in (
        "candidate selected; minimal design documented",
        "get /repos/royliu1105/agent-kernel/actions/runs/{run_id}",
        "anonymous read of public repository metadata",
        "retry_safe=false",
        "require_approval",
        "does **not** enforce output-field projection",
        "this observer does not exist yet",
        "initialization or pre-dispatch journal failure must prevent dispatch",
        "cannot undo an already dispatched request",
        "response headers alone do not prove a complete response",
        "before approval (no decision)",
        "rejected approval followed by resume",
        "not github's internal processing count or global exactly-once",
        "pv2/pv3 remain not started",
    ):
        assert _normalized(phrase) in section


def test_pv1_confirmed_design_keeps_unresolved_permissions_and_evidence_open() -> None:
    filename = "pilots/pv1-2026-11-15-runbook-assistant.md"
    authorization = _section(filename, "Authorization and Candidate")
    for phrase in (
        "the maintainer accepts unverified no-training risk for this pilot",
        "at most usd 2 within usd 10; later batches require separate confirmation",
        "exact-submission ci tracking only",
        "ci tracking for this submission only",
        "submission ci tracking for the exact submitted sha only",
        "do not create an environment",
        "invoke the pilot github query",
        "provider transmission remains pending",
        "usd 0",
    ):
        assert phrase in authorization
    decisions = _section(filename, "Maintainer Confirmation Sheet")
    for phrase in (
        "maintainer accepted scope/budget owner, operator/incident contact and domain reviewer",
        "p1/p2 and specific dates explicitly deferred",
        "usd 0.25/task and usd 8 admission stop accepted",
        "run 43634747295 / pinned sha",
        "run_attempt=1 and matching identity observed",
        "full authenticated web acceptance incomplete",
        "pv1 cannot pass with unresolved required fields",
        "effective-request verification method",
        "do not require pv2 execution to sign off pv1",
    ):
        assert phrase in decisions
    prompt = _section(filename, "Accepted Task Prompt")
    assert "not installed in a running environment or sent to a provider" in prompt
    assert "file hash alone does not prove the runtime used it" in prompt
    remaining = _section(filename, "Remaining Items by Priority")
    assert "changed responses require renewed review" in remaining
    assert "pv5 entry inputs, not another pv1 technical confirmation round" in remaining
    assert "use the existing scoped authorizations" in remaining
    assert "closure + 30 calendar days" in remaining
    assert "current paid-call/environment/docker hold remains in force" in remaining
    rehearsal = _section(
        "real-scenario-pilot-plan.md", "PV2: Rehearse the Existing Workflow Without Paid Calls"
    )
    assert "not github server logs or global exactly-once" in rehearsal


def test_pv1_risk_acceptance_is_not_a_verified_provider_commitment() -> None:
    filename = "pilots/pv1-2026-11-15-runbook-assistant.md"
    privacy = _section(filename, "No-Training Requirement and Provider Evidence")
    for phrase in (
        "api inputs and outputs must not be used for model training",
        "public or synthetic content does not waive this requirement",
        "account-specific no-training commitment unverified",
        "submission not confirmed",
        "no-training is not zero retention",
        "the maintainer explicitly accepts unverified no-training risk",
        "approves the inspected full github response for deepseek",
    ):
        assert _normalized(phrase) in privacy
    for name in ("real-scenario-pilot-plan.md", "provider-compatibility.md"):
        content = _normalized((DOCS_ROOT / name).read_text(encoding="utf-8"))
        assert "no training use of api inputs/outputs" in content
        assert "unverified" in content
    preparation = _section(filename, "Offline Configuration and Budget Preparation")
    assert "not a new deployment authorization" in preparation
    assert "source defaults differ from the pilot values" in preparation
    assert "not yet demonstrated feasible" in preparation
    assert "no silent alias change" in preparation


def test_pv1_scoped_authorization_does_not_pass_pilot_or_authorize_all_data() -> None:
    filename = "pilots/pv1-authorization-2026-11-15.md"
    review = _section(filename, "Current Review Scope")
    for phrase in (
        "technical closure, offline harness code/tests",
        "current instruction authorizes review and fixes",
        "do not call paid models, create local environments or update current docker",
        "no pilot query or provider request is needed or performed",
        "retained, not exercised by this review",
        "scoped commit/push after review passes and exact-submission ci tracking only",
        "no release",
    ):
        assert phrase in review
    for name in (
        filename,
        "real-scenario-pilot-plan.md",
        "pilots/pv1-2026-11-15-runbook-assistant.md",
    ):
        content = _normalized((DOCS_ROOT / name).read_text())
        assert "no commit/push is requested in this step" not in content
        assert "review scope below records the preceding completed submission" not in content
    authority = _section(filename, "Accepted Authorization")
    for phrase in (
        "first paid batch up to usd 2 within the usd 10 total ceiling",
        "later batches require separate confirmation",
        "deepseek official reply remains pending",
        "risk acceptance is not a provider promise or zero retention",
        "reviewer gold answers",
        "personal memory are excluded",
        "no model request was made this turn",
        "keep pilot/test storage separate from agent-kernel-local",
        "blank request/evidence templates intentionally stay fail-closed",
    ):
        assert phrase in authority
    inspection = _section(filename, "Manual GitHub Inspection")
    for phrase in (
        "one manual anonymous get",
        "not zero/one agent dispatch",
        "43634747295 / 1",
        "14622 bytes",
        "author/committer names and email fields",
        "payload-specific permission",
        "no model received the body",
    ):
        assert phrase in inspection


def test_pv1_payload_permission_is_bound_to_reviewed_source_and_provider() -> None:
    inspection = _section("pilots/pv1-authorization-2026-11-15.md", "Manual GitHub Inspection")
    for phrase in (
        "37637575f2483bd19f6d91c84ae8db84a0189993e50b96ca247242a59009bc7f",
        "for transmission to deepseek as a tool result",
        "not approval for arbitrary future github responses",
        "or transmission of this tool payload to alibaba",
        "a changed response must be reviewed again before transmission",
        "matching run_id/sha/attempt alone is insufficient",
        "no projection feature or enforcement code is implemented",
        "no model received the response",
        "not the provider wire envelope",
    ):
        assert phrase in inspection
    summary = _section("pilots/pv1-2026-11-15-runbook-assistant.md", "Authorization and Candidate")
    assert "for deepseek only, not alibaba" in summary


def test_pv1_budget_preflight_is_not_claimed_as_existing_runtime_enforcement() -> None:
    budget = _section(
        "pilots/pv1-2026-11-15-runbook-assistant.md", "First USD 2 Allocation and Calculation"
    )
    for phrase in (
        "the existing runtime automatically retries eligible provider errors",
        "serial run admission alone cannot intercept those calls",
        "including retries and resume",
        "before any content is sent",
        "paid execution stays blocked",
        "not implemented by this document or its arithmetic tests",
        "not an exchange-rate quote",
        "not a provider-guaranteed hard invoice cap",
    ):
        assert phrase in budget
    harness = _section("pilots/pv1-harness-spec.md", "Preflight and Coverage")
    for phrase in (
        "every generation and embedding attempt",
        "guard denial must be non-retryable",
        "zero downstream provider dispatch on denial",
        "unimplemented pv2 obligations",
    ):
        assert phrase in harness


def test_pv1_supervised_subset_cannot_pass_independent_user_gate() -> None:
    profile = _section("pilots/pv1-2026-11-15-runbook-assistant.md", "Finalized Technical Profile")
    assert "not evidence of pv5 independent onboarding or unassisted task success" in profile
    assert "no threshold is waived" in profile
    for filename in ("pilots/pv1-offline-rehearsal.md", "real-scenario-pilot-plan.md"):
        content = _normalized((DOCS_ROOT / filename).read_text())
        assert "pv5 independent onboarding or unassisted task success" in content


def test_pv1_limit_table_matches_offline_configuration_parser() -> None:
    content = (DOCS_ROOT / "pilots/pv1-2026-11-15-runbook-assistant.md").read_text()
    rows = re.findall(r"^\| (AGENT_KERNEL_MAX_\w+) \| (\d+) \| (\d+) \|$", content, re.MULTILINE)
    expected = {
        "AGENT_KERNEL_MAX_MODEL_CALLS": "6",
        "AGENT_KERNEL_MAX_TOOL_CALLS": "8",
        "AGENT_KERNEL_MAX_ACTIVE_SECONDS": "120",
        "AGENT_KERNEL_MAX_TOTAL_TOKENS": "32000",
        "AGENT_KERNEL_MAX_OUTPUT_TOKENS": "2048",
        "AGENT_KERNEL_MAX_HISTORY_BYTES": "262144",
    }
    assert len(rows) == len(expected)
    assert {key: value for key, value, _ in rows} == expected
    # Explicit maps avoid reading host configuration or configuring a service.
    defaults = ExecutionLimits.from_env({}).model_dump()
    pilot = ExecutionLimits.from_env(expected).model_dump()
    for key, value, default in rows:
        field = key.removeprefix("AGENT_KERNEL_").lower()
        assert defaults[field] == int(default)
        assert pilot[field] == int(value)


def test_pv1_offline_sheet_keeps_request_checks_separate_from_pilot_evidence() -> None:
    sheet = _normalized((DOCS_ROOT / "pilots/pv1-offline-rehearsal.md").read_text())
    for phrase in (
        "prepared, not executed or accepted",
        "not an api body or runnable client",
        "input.task is then ignored",
        "not automatically loaded by this api path",
        "cli --input takes the inner input object",
        "resume is an active execution endpoint",
        "no claimed submitter/approver separation",
        "the github observer has fixture components",
        "in-memory serialization is not persisted resume evidence",
    ):
        assert phrase in sheet


def test_pv1_harness_spec_separates_fixture_implementation_from_full_acceptance() -> None:
    spec = _normalized((DOCS_ROOT / "pilots/pv1-harness-spec.md").read_text())
    for phrase in (
        "offline components and api/worker integration implemented",
        "isolated remote container checks passed; full pv2 open",
        "spending authorization usd 0",
        "api resume executes tools too",
        "headers alone are not a complete response",
        "unknown values are null, never zero",
        "not github server logs or global exactly-once",
        "tests of form structure alone do not implement or pass these controls",
        "do not require executed pv2 evidence to sign off pv1",
        "no learning sign-off is claimed now",
        "a planned replacement executor is allowed only after",
        "unregistered or uninstrumented executors invalidate coverage",
        "confirm fsync (or equivalent durable-store acknowledgement)",
    ):
        assert phrase in spec


def test_pv1_offline_dependency_exception_preserves_human_and_runtime_gates() -> None:
    plan = _normalized((DOCS_ROOT / "real-scenario-pilot-plan.md").read_text())
    assert "not offline harness work" in plan
    assert "full pv1 sign-off, two independent participants/dates" in plan
    assert "current no-environment/no-paid-call hold remains" in plan
    status = _section("pilots/pv1-harness-spec.md", "Offline Implementation Status")
    assert "not** a case-matrix pass" in status
    assert "shared ledger/container wiring" in status
    assert "blank evidence templates remain unchanged" in status


def test_pv1_technical_closure_preserves_original_full_pilot_requirements() -> None:
    closure = _section("pilots/pv1-2026-11-15-runbook-assistant.md", "Technical Closure")
    for phrase in (
        "technical planning scope",
        "not the original full-pilot acceptance",
        "not a waiver or invented participant consent",
        "no further routine pv1 questionnaire is needed",
        "current execution hold remains",
        "not a verified incident channel or 24/7 coverage",
    ):
        assert phrase in closure
    users = _section("real-scenario-pilot-plan.md", "PV5: Run the Controlled User Pilot")
    assert "two independent participant" in users
    assert "at least three distinct active-use dates" in users
    assert "not waived by technical planning closure" in users


def test_pilot_plan_separates_evidence_and_prevents_cherry_picked_passes() -> None:
    evidence = _section("real-scenario-pilot-plan.md", "Authority, Owners and Evidence")
    for anchor in ("fixture", "live", "human_pilot", "not live proof", "no secrets"):
        assert anchor in evidence
    scoring = _section("real-scenario-pilot-plan.md", "Scoring and Measurement Rules")
    assert "not previously measured results" in scoring
    assert "do not average a failed safety cohort" in scoring
    changes = _section("real-scenario-pilot-plan.md", "Defect Handling and Change Control")
    assert "new capabilities require a separate proposal and authorization" in changes
    assert "writing this plan does not pass pv1" in changes


@pytest.mark.parametrize(
    "filename",
    (
        "real-scenario-pilot-plan.md",
        "development-plan.md",
        "capability-hardening-plan.md",
        "README.md",
    ),
)
def test_pilot_entry_points_include_the_learning_mechanism(filename: str) -> None:
    text = (DOCS_ROOT / filename).read_text(encoding="utf-8")
    assert "pilot-learning-guide.md" in text


def test_learning_guide_keeps_participation_and_safety_boundaries() -> None:
    contract = _section("pilot-learning-guide.md", "Collaboration Contract")
    for anchor in (
        "Chinese explanations",
        "one main learning question",
        "wait for the learner's response",
        "record that assistance",
        "AI assistance is allowed",
        "contain the risk first",
        "does not authorize paid requests",
    ):
        assert _normalized(anchor) in contract
    testing = _section("pilot-learning-guide.md", "Test Verification")
    for anchor in (
        "fails on the defective behavior for the intended reason",
        "passes after the minimal fix",
        "negative case",
        "do not break the main branch",
        "existing negative regression",
    ):
        assert _normalized(anchor) in testing


def test_learning_guide_does_not_treat_task_completion_as_proficiency() -> None:
    evidence = _section("pilot-learning-guide.md", "Separate Evidence Tracks")
    for anchor in (
        "separate tracks",
        "cannot waive a failed project safety or acceptance gate",
        "Not practiced",
        "Demonstrated by Codex",
        "Practiced with guidance",
        "Observed independent on this task",
        "Revisit",
        "not proof of general mastery",
        "never write a learner answer on their behalf",
    ):
        assert _normalized(anchor) in evidence
    handoff = _section("pilot-learning-guide.md", "Session Record and Handoff")
    assert "docs/pilots/<pilot-id>.md" in handoff
    assert "no separate learning database" in handoff
    assert "do not publish personal learning notes without the learner's agreement" in handoff


def test_learning_focus_uses_existing_pilot_gates_without_new_tasks() -> None:
    guide = (DOCS_ROOT / "pilot-learning-guide.md").read_text(encoding="utf-8")
    assert re.findall(r"^\| (PV[1-6]) \|", guide, flags=re.MULTILINE) == [
        f"PV{index}" for index in range(1, 7)
    ]
    focus = _section("pilot-learning-guide.md", "Learning Focus by Pilot Gate")
    assert "not a second completion checklist" in focus
    assert "do not coach participants" in focus


def test_memory_safety_contract_records_limits_and_resume_boundaries() -> None:
    text = _normalized((DOCS_ROOT / "specs/memory-context-safety.md").read_text(encoding="utf-8"))
    for required in (
        "16 KiB",
        "4 KiB",
        "64 KiB",
        "1-8 strings",
        "1-20",
        "4096",
        "workspace-shared",
        "not per-user ACLs",
        "USER message",
        "unsupported_memory_checkpoint",
        "invalid_execution_checkpoint",
        "without memory remain compatible",
        "no schema migration",
        "does not prove",
        "HTTP/proxy body-size limits",
    ):
        assert _normalized(required) in text
    for filename in (
        "README.md",
        "specs/memory.md",
        "security-hardening.md",
        "configuration.md",
        "upgrade-migration-policy.md",
        "reference-follow-up-plan.md",
    ):
        assert "memory-context-safety.md" in (DOCS_ROOT / filename).read_text(encoding="utf-8")
