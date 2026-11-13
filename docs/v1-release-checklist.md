# v1.0 Release Checklist

This checklist records the historical gates and publication of Agent Kernel v1.0.

Current status:

```text
v1.0.0 published 2026-08-07; publication evidence reconciled 2026-11-14
```

Verified against the existing GitHub release, annotated tag and Actions run:

- Release commit: `46849314d9f7740729fa9b3535fe06e9554366b6`.
- Annotated tag object: `e797623707c3e888989255c4b5f008fc8a7e1ac8` (`v1.0.0`).
- [GitHub Release](https://github.com/royliu1105/agent-kernel/releases/tag/v1.0.0):
  published `2026-08-07T11:29:59Z`; neither draft nor prerelease.
- [Release commit CI](https://github.com/royliu1105/agent-kernel/actions/runs/31122498218): success.

Local results below retain the recorded Day 90 scope. Unchecked historical items
mean evidence was not reconstructed, not that publication is still pending.
Publishing does not prove that every historical process check was performed.
The original release rules and waivers are in [v1.0 Scope Freeze](v1-scope-freeze.md).
Current unreleased work has separate gates in the
[capability hardening plan](capability-hardening-plan.md). This correction neither
creates a release nor retroactively adds new capabilities to the v1.0.0 tag.

## Release Identity

- [x] Final version string is confirmed.
- [x] Target commit SHA is recorded above and matches the annotated tag.
- [ ] Release branch was up to date before tagging: historical evidence unavailable.
- [ ] Working tree was clean before tagging: historical evidence unavailable.
- [x] GitHub CI is green on the release commit (run linked above).

## Scope Freeze

- [x] v1.0 scope freeze exists.
- [x] Accepted v1.0 limitations are documented.
- [x] Deferred beyond-v1.0 work is documented.
- [x] No new feature scope has been added after Day 87 without release-owner
  approval.
- [x] Any waiver names the waived item, evidence reviewed, risk owner, and
  follow-up milestone.

## Required Python Gates

- [x] `uv sync --dev`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest`
- [x] `uv run pytest tests/unit/test_migrations.py`
- [x] `uv run pytest tests/unit/test_docs_consistency.py`

## Required Release Gates

- [x] `make release-eval`
- [x] `make release-smoke`
- [x] `make release-load-soak`
- [x] `docker compose config`
- [x] `AGENT_KERNEL_API_PORT=8011 AGENT_KERNEL_WEB_PORT=3011 AGENT_KERNEL_POSTGRES_PORT=55432 AGENT_KERNEL_REDIS_PORT=56379 docker compose config`
- [x] `git diff --check` was recorded as passed in [Day 90](daily/day-90.md).

## Required Web Gates

- [x] `npm install`
- [x] `npm run lint`
- [x] `npm run build`
- [x] `npm run test:e2e`

## Migration and Storage Gates

- [x] Fresh SQLite database upgrades to Alembic head.
- [x] Fresh PostgreSQL database upgrades to Alembic head.
- [x] pgvector extension path is validated on PostgreSQL.
- [x] Local object storage path is writable and survives container restart.
- [x] S3/MinIO configuration docs are reviewed against current behavior.
- [x] Backup and restore guide is reviewed against current migration behavior.

## Clean-Machine Rehearsal

- [x] Fresh checkout dependency install passes.
- [x] Fresh checkout Python gates pass.
- [x] Fresh checkout Web gates pass.
- [x] Fresh checkout release eval/smoke/load-soak gates pass.
- [x] Fresh full-stack Docker Compose restart passes.
- [x] No fresh full-stack restart waiver is needed because Day 90 executed the
  restart with isolated host ports.

## Runtime Smoke

- [x] API `/healthz` returns healthy.
- [x] API `/metrics` returns Prometheus-compatible metrics.
- [x] Web Workbench loads.
- [x] Worker starts and can process a queued run.
- [x] Mock run lifecycle completes.
- [x] Tool call lifecycle completes.
- [x] Approval pause/resume lifecycle completes.
- [x] Knowledge base retrieval returns citations.
- [x] Memory write/read/retrieve lifecycle completes.
- [x] Eval report publish/list/read lifecycle completes.

## Security and Dependency Review

- [x] `AGENT_KERNEL_API_KEY_AUTH_ENABLED=true` production posture is documented.
- [x] Stable `/v1/*` routes have authorization coverage.
- [x] `/metrics` protection requirement is documented.
- [x] Secrets are absent from committed files and examples.
- [x] Dependency audit is reviewed.
- [x] Accepted dependency advisories, if any, are listed in release notes.
- [x] SECURITY reporting instructions are current.
- [x] No silent security limitation remains.

## Documentation Review

- [x] v1.0 API and CLI compatibility policy exists.
- [x] Versioned configuration reference exists.
- [x] Upgrade and migration policy exists.
- [x] Backup and restore guide exists.
- [x] Security hardening checklist exists.
- [x] Release eval gates exist.
- [x] Release smoke tests exist.
- [x] Load and soak scenarios exist.
- [x] Clean-machine rehearsal runbook exists.
- [x] Docs consistency audit exists.
- [x] v1.0 scope freeze exists.
- [x] v1.0 release notes exist.
- [x] README, docs index, roadmap and phase publication status were reconciled
  on 2026-11-14; stale pre-publication text was found and corrected. Historical
  release notes are distinguished from current quickstart/operator guidance.
- [x] Known limitations in release notes match the scope freeze.
- [x] Upgrade notes in release notes match the migration policy.

## Accepted v1.0 Limitations

These are the limitations recorded for the published tag, not a list of current
branch limitations. Some have since been addressed by unreleased hardening:

- [x] API-key auth is disabled by default for local quickstart compatibility.
- [x] Browser login, OIDC, SSO, and password auth are not included.
- [x] Web Workbench is not a full administration console.
- [x] Public hosted SaaS tenant isolation is out of scope.
- [x] `/metrics` must be protected by external network or gateway controls.
- [x] Secrets manager integration is deployment-specific.
- [x] Remote sandbox execution is not implemented.
- [x] Browser session automation is not implemented.
- [x] Redis queue adapter exists, but database-backed polling remains default.
- [x] Stuck-run recovery is conservative.
- [x] Server-side eval jobs and LLM-as-judge are outside the stable v1.0
  surface.
- [x] OpenTelemetry collector, dashboards, retention, and alerts are operator
  responsibilities.

## Deferred Non-Blocking Scope

These items were explicitly outside the v1.0 release scope:

- [x] Hosted multi-tenant SaaS.
- [x] Multi-region managed cloud deployment.
- [x] Enterprise SSO administration.
- [x] Billing and quota management.
- [x] Third-party tool marketplace.
- [x] Visual no-code workflow builder.
- [x] Browser session automation product surface.
- [x] Remote sandbox execution service.
- [x] Cross-browser Web test matrix.
- [x] Public performance dashboard.
- [x] Large-scale benchmark leaderboard.
- [x] Stable advanced retrieval APIs for hybrid retrieval, RRF, reranking, and
  query rewriting.
- [x] Stable server-side eval dataset and eval job APIs.

## Release Notes

- [x] `docs/releases/v1.0.0.md` exists.
- [x] Completed capabilities are listed.
- [x] Stable public surfaces are listed.
- [x] Accepted limitations are listed.
- [x] Deferred scope is listed.
- [x] Verification commands and results are listed.
- [x] Upgrade notes are included.
- [x] Dependency audit status is included.
- [x] Security posture is included.

## Tagging and Publication

- [x] Annotated tag `v1.0.0` exists and resolves to the release commit.
- [x] Release commit is present on GitHub.
- [x] Tag is present on GitHub.
- [x] GitHub CI for the pushed release commit succeeded.
- [x] GitHub release exists with the v1.0 notes; API metadata and body verified.
- [ ] Visual release-page rendering was not rechecked in this reconciliation;
  API verification alone does not establish browser rendering.

## Post-Release

- [ ] Open v1.x follow-up issues for deferred scope.
- [ ] Open any waiver follow-up issues.
- [ ] Record first-user feedback channel.
- [ ] Monitor dependency advisories after release.
- [x] Roadmap points to the current post-v1.0 hardening plan and its acceptance gates.
