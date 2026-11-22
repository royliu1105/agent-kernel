# Open Source Cleanup: PR Split Plan

Status: **plan active** (2026-11-22). **PR-1 through PR-5 implemented**
in-tree. Does not authorize deletion of runtime data, credentials, Docker
volumes, or a release. Later PRs still need an explicit maintainer go-ahead
before coding starts.

Goal: make the repository easy for a stranger to clone, understand, run, and
contribute to—by removing **misdirection and burden**, not by stripping the
Agent Runtime differentiators (HITL, leases, RAG, evals, observability).

## Principles

1. One current-status source of truth; historical material is archived, not mixed.
2. Prefer move/archive over silent rewrite of frozen pilot evidence.
3. Do not claim multi-tenant SaaS, BM25/Rerank, multi-agent, or streaming as done.
4. No host runtime revival; Docker-only local path stays canonical.
5. No `resource/` directory or vendored reference tree in the maintained product.
6. Large refactors only when they reduce contributor foot-guns; no language rewrite.

## Non-Goals (explicitly out of this cleanup series)

- Implementing CF3–CF8 or PV3–PV6.
- Splitting `execution.py` / `repositories.py` without a behavioral touchpoint.
- Removing S3 adapters, observability Compose services, or thin packages that are wired.
- Production certification or a new semver release (separate decision).

## Suggested PR Sequence

| PR | Title | Risk | Depends on | Merge when |
| --- | --- | --- | --- | --- |
| PR-1 | Docs: current vs archive map + OSS positioning | Low | — | Links resolve; no status contradiction in README ↔ overview |
| PR-2 | Harden `resource/` exclusion + contributor warning | Low | PR-1 optional | Ignore/docker/CI still exclude; CONTRIBUTING clear |
| PR-3 | Archive historical daily/phase status noise | Low–med | PR-1 | Current docs index still navigable; archive linked |
| PR-4 | Web: remove `/preview`; clarify live `/` workbench | Med | — | `/` remains entry; e2e and docs updated |
| PR-5 | Unify tool/policy execution entry | Med | — | One production path; tests updated; behavior unchanged |
| PR-6 | README/CONTRIBUTING/SECURITY OSS pass | Low | PR-1, PR-2 | First-hour contributor path works from clean clone |
| PR-7 (optional) | Extract reference comparison to external note | Low | PR-2 | Maintained tree has no dependency on local `resource/` tree |

Do not batch PR-4 and PR-5 with docs-only PRs; keep review and rollback simple.

---

## PR-1 — Docs: Current vs Archive + Positioning

### Change

- Add a short **Current documentation** section at the top of `docs/README.md`:
  - Product/positioning: `project-overview.md`
  - Run locally: `quickstart.md`, `docker-local.md`
  - Limits/security: `SECURITY.md`, `auth-rbac.md`, `specs/memory-context-safety.md`
  - Pilot ledger: `real-scenario-pilot-plan.md` (status only; not a feature backlog)
  - Follow-ups: `reference-follow-up-plan.md` (CF list; deferred clearly labeled)
- Add **Archive / historical** section pointing at day logs, phase summaries,
  public-alpha/beta writeups, and old milestones—labeled “not current acceptance”.
- Trim duplicated “current status” paragraphs from `ROADMAP.md` /
  `docs/milestones.md` / `docs/development-plan.md` to a single pointer:
  “Current status: see project-overview + pilot plan. This file is historical.”
- Align root `README.md` first screen with overview: what it is, Docker-only
  start, explicit limitations (single-agent, Workspace ≠ public multi-tenant SaaS).

### Do not change

- Frozen pilot materials, expected answers, prompt hashes.
- Capability evidence tables’ factual claims (edit only for navigation clarity).
- Application or package code.

### Acceptance

- [x] New contributor can find “run”, “architecture”, “limits” in ≤3 clicks from README.
- [x] No document in the “current” set still presents CF3–CF8 as in-progress delivery.
- [x] `make`-documented paths and Docker-only rule unchanged.

### Implementation note (2026-11-22)

Updated `README.md`, `docs/README.md`, `ROADMAP.md`, `docs/milestones.md`, and
`docs/development-plan.md` only. No application/package code and no frozen
pilot materials.

---

## PR-2 — `resource/` Exclusion Hygiene

Context: `.gitignore` and `.dockerignore` already list `resource/`. Local trees
may still exist on maintainer machines (~hundreds of MB) and confuse clones.

### Change

- Keep ignore rules; add a root `resource/README.md` **only if** the directory
  must exist as a placeholder—stating: not shipped, not a dependency, do not
  commit, comparison notes live in docs.
- Or document in CONTRIBUTING/AGENTS: “If you keep a local reference checkout,
  place it outside the repo or under ignored `resource/`.”
- Grep docs for wording that implies `resource/` is part of the product; point
  readers to `docs/reference-project-comparison.md` as optional maintainer note.
- Ensure CI and release artifacts never pack `resource/`.

### Do not change

- Delete a maintainer’s local `resource/` tree without explicit approval.
- Vendor the reference TypeScript project into `packages/` or `examples/`.

### Acceptance

- [x] Clean clone has no requirement to populate `resource/` to build or test.
- [x] AGENTS.md / CONTRIBUTING agree on the exclusion.
- [x] `git check-ignore` ignores reference trees under `resource/**` while
      allowing the tracked `resource/README.md` placeholder.

### Implementation note (2026-11-22)

Updated `.gitignore` (`resource/**` + `!resource/README.md`), added
`resource/README.md`, aligned `AGENTS.md` / `CONTRIBUTING.md` /
`docs/reference-project-comparison.md` / `docs/README.md`, and added
`test_resource_trees_are_optional_and_excluded_from_git_and_builds`. Did **not**
delete any maintainer-local reference tree under `resource/`.

---

## PR-3 — Archive Historical Doc Noise

### Change

- Move (git mv) high-churn historical sets under `docs/archive/`, for example:
  - `docs/daily/` → `docs/archive/daily/`
  - selected `docs/phase-*-summary.md`, public-alpha/beta long-forms if they
    duplicate `docs/releases/` and post-v0.1 history
- Leave a stub `docs/daily/README.md` (or redirect note) linking to the archive.
- Update `docs/README.md` archive index only; do not rewrite daily contents.

### Do not change

- `docs/pilots/`, `docs/reviews/`, `docs/specs/` current contracts.
- Release notes under `docs/releases/` that readers need for upgrade policy.
- Any file whose path is asserted by tests (`tests/unit/test_docs_consistency.py`
  etc.) without updating those tests in the same PR.

### Acceptance

- [x] Doc consistency tests pass.
- [x] Current operator guides remain at stable paths or have explicit redirects.
- [x] Archive banner: “Historical; not acceptance criteria.”

### Implementation note (2026-11-22)

- Moved `docs/daily/` → `docs/archive/daily/` with stub at `docs/daily/README.md`.
- Moved phase summaries, Public Alpha/Beta long-forms, and related historical
  notes into `docs/archive/` (kept `docs/releases/*`, pilot/review/specs, and
  operator guides in place).
- Rewrote archived relative links; updated inbound links and
  `tests/unit/test_docs_consistency.py` path assertions.
- Did not rewrite historical prose paths inside day checklists (archaeological).

---

## PR-4 — Web: Remove `/preview` + clarify live `/`

### Change

- Delete `apps/web/src/app/preview/`.
- Keep `/` as the only Workbench entry; update `docs/web-first-use.md` and
  related operator docs.
- Retarget Playwright smoke to live `/` (anonymous + run lookup/results).
- Improve `/` operator layout: Agents → Knowledge → Runs → Results hierarchy,
  collapse UUID/advanced options by default, promote run status/approvals/events.

### Do not change

- Authenticated first-use API contracts validated in PV2 evidence (open Advanced
  options before filling system prompt).
- Backend APIs or approval semantics.

### Acceptance

- [x] Playwright smoke for the maintained path targets `/`.
- [x] Docs never tell new users to start on `/preview`.
- [x] `/preview` route removed.

### Implementation note (2026-11-22)

Removed the fixture Workbench route and reworked live Workbench CSS/structure.
Historical pilot/archive mentions of preview may remain as period evidence.

---

## PR-5 — Unify Tool / Policy Execution Entry

### Change

- Make production Run execution and tests share one policy-aware entry
  (either promote `PolicyAwareToolExecutor` into the runtime path, or delete the
  unused wrapper after inlining its guarantees once).
- Prefer a single registry factory used by API/Worker
  (`create_rag_tool_registry` or a renamed `create_runtime_tool_registry`) with
  `create_default_tool_registry` limited to unit tests / echo-only cases.
- Keep external behavior: risk decisions, approval pause, deny, audit events.

### Do not change

- Tool schema contracts, MCP transport behavior, OpenAPI binding security rules
  beyond the single entrypoint wiring.
- Approval resume semantics and lease fencing.

### Acceptance

- [x] Existing unit/integration suites for policy, approval, MCP, and native
      continuation pass without weakening assertions.
- [x] One documented “how tools are invoked” paragraph in `docs/external-tools.md`
      or `docs/specs/tool-calling.md`.
- [x] No dual “which executor is real?” ambiguity in CONTRIBUTING.

### Implementation note (2026-11-22)

- Shared direct-invoke gate: `enforce_direct_execution` used by
  `PolicyAwareToolExecutor`; Run path uses `_decide_tool_policy` + persistence.
- Production registry factory renamed to `create_runtime_tool_registry`
  (`create_rag_tool_registry` kept as deprecated alias).
- Docs/CONTRIBUTING state the two invocation modes explicitly.

---

## PR-6 — OSS Front Door (README / CONTRIBUTING / SECURITY)

### Change

- README: problem → architecture sketch → Docker-only quickstart → limitations →
  doc map → contributing link.
- CONTRIBUTING: toolchain, `make test-db-up`, never point tests at the live Docker
  DB, PR expectations, doc current-vs-archive rule.
- SECURITY: Workspace scoping vs non-goals (public multi-tenant SaaS), how to
  report issues, auth-disabled localhost warning.

### Do not change

- Private credential layouts or real endpoints beyond `.env.example`.
- Pilot authorization ledgers’ legal/budget language (link, don’t fork).

### Acceptance

- [x] Clean-machine path matches `docs/clean-machine-rehearsal.md` intent (or
      points to it).
- [x] Limitations section matches overview (single-agent, Workspace model, mock
      default).

### Implementation note (2026-11-22)

- README reordered: problem → architecture sketch → Docker quickstart → limits →
  doc map → status → contributor toolchain; links clean-machine rehearsal.
- CONTRIBUTING: test-db isolation, current-vs-archive docs rule, localhost
  auth-disabled warning; points at clean-machine for release-path intent.
- SECURITY: Workspace vs public multi-tenant non-goals; dedicated localhost
  auth-disabled section; reporting channel unchanged.

---

## PR-7 (Optional) — Reference Comparison Decoupling

### Change

- Keep `docs/reference-project-comparison.md` as a maintainer research note.
- Remove any implication that cloning this repo includes the reference tree.
- If comparison path anchors are painful without `resource/`, rephrase as
  “local maintainer reference” without requiring paths in CI.

### Do not change

- CF1–CF8 decisions already recorded; do not reopen foundation expansion.

### Acceptance

- [x] Comparison doc readable without a local `resource/` tree; reference
      anchors are plain-text locators, not required Markdown links.
- [x] Placeholder / overview / docs map state that clone does not ship a
      reference project.
- [x] CF1–CF8 not reopened.

### Implementation note (2026-11-22)

- Strengthened “local maintainer research note” framing; prefer reference
  checkout outside the repo.
- Reference source anchors labeled private-local-only; skippable without tree.
- Follow-up (same day, maintainer-authorized): deleted the local `resource/`
  tree (including the private reference source checkout), removed
  `.gitignore` / `.dockerignore` / placeholder / contributor conventions for
  that path, and rewrote docs/tests so the repo neither ships nor hosts a
  reference project.

---

## Verification Matrix (per PR)

| Check | PR-1 | PR-2 | PR-3 | PR-4 | PR-5 | PR-6 | PR-7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Docs link sanity / consistency tests | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ruff` / `mypy` / backend tests | — | — | if paths asserted | if touched | ✓ | — | — |
| Web lint / e2e | — | — | — | ✓ | — | — | — |
| Docker-only docs still accurate | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Paid provider calls are **out of scope** for cleanup PRs unless separately
authorized.

## Rollback

- Docs/archive PRs: revert the merge commit; archive moves are reversible with git.
- Web demotion: revert route/docs; keep data volumes untouched.
- Executor unification: revert merge; no DB migration should be required for PR-5.
  If a migration sneaks in, abort and split it out.

## Interview / Positioning Note (not a PR)

After cleanup, public positioning should stay:

> Self-hosted, auditable, resumable single-agent runtime with tools, policy,
> HITL, RAG, evals, and observability—not a multi-agent SaaS studio.

Resume and README must not cite deferred CF items as shipped features.

## Execution Order for the Maintainer

1. Approve this plan (this file).
2. Authorize **PR-1** only; merge after acceptance checklist.
3. Proceed PR-2 → PR-3 → PR-6 early for OSS readability.
4. Schedule PR-4 / PR-5 when ready for behavior-sensitive review.
5. Consider PR-7 only if `resource/` confusion persists.

When authorizing implementation, say which PR id to start (e.g. “implement PR-1”).
