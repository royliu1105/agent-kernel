# v1.0 Release Checklist

This checklist is the final gate for publishing Agent Kernel v1.0.

Current status:

```text
created on Day 88; not yet completed
```

Do not tag or publish v1.0 until every required item is checked, fixed, or
explicitly waived according to [v1.0 Scope Freeze](v1-scope-freeze.md).

## Release Identity

- [ ] Final version string is confirmed.
- [ ] Target commit SHA is recorded.
- [ ] Release branch is up to date with the target branch.
- [ ] Working tree is clean before tagging.
- [ ] GitHub CI is green on the release commit.

## Scope Freeze

- [x] v1.0 scope freeze exists.
- [x] Accepted v1.0 limitations are documented.
- [x] Deferred beyond-v1.0 work is documented.
- [ ] No new feature scope has been added after Day 87 without release-owner
  approval.
- [ ] Any waiver names the waived item, evidence reviewed, risk owner, and
  follow-up milestone.

## Required Python Gates

- [ ] `uv sync --dev`
- [ ] `uv run ruff check .`
- [ ] `uv run mypy .`
- [ ] `uv run pytest`
- [ ] `uv run pytest tests/unit/test_migrations.py`
- [ ] `uv run pytest tests/unit/test_docs_consistency.py`

## Required Release Gates

- [ ] `make release-eval`
- [ ] `make release-smoke`
- [ ] `make release-load-soak`
- [ ] `docker compose config`
- [ ] `AGENT_KERNEL_API_PORT=8011 docker compose config`
- [ ] `git diff --check`

## Required Web Gates

- [ ] `npm install`
- [ ] `npm run lint`
- [ ] `npm run build`
- [ ] `npm run test:e2e`

## Migration and Storage Gates

- [ ] Fresh SQLite database upgrades to Alembic head.
- [ ] Fresh PostgreSQL database upgrades to Alembic head.
- [ ] pgvector extension path is validated on PostgreSQL.
- [ ] Local object storage path is writable and survives container restart.
- [ ] S3/MinIO configuration docs are reviewed against current behavior.
- [ ] Backup and restore guide is reviewed against current migration behavior.

## Clean-Machine Rehearsal

- [ ] Fresh checkout dependency install passes.
- [ ] Fresh checkout Python gates pass.
- [ ] Fresh checkout Web gates pass.
- [ ] Fresh checkout release eval/smoke/load-soak gates pass.
- [ ] Fresh full-stack Docker Compose restart passes.
- [ ] If a fresh full-stack restart is not executed, a release-owner waiver is
  recorded with evidence and follow-up.

## Runtime Smoke

- [ ] API `/healthz` returns healthy.
- [ ] API `/metrics` returns Prometheus-compatible metrics.
- [ ] Web Workbench loads.
- [ ] Worker starts and can process a queued run.
- [ ] Mock run lifecycle completes.
- [ ] Tool call lifecycle completes.
- [ ] Approval pause/resume lifecycle completes.
- [ ] Knowledge base retrieval returns citations.
- [ ] Memory write/read/retrieve lifecycle completes.
- [ ] Eval report publish/list/read lifecycle completes.

## Security and Dependency Review

- [ ] `AGENT_KERNEL_API_KEY_AUTH_ENABLED=true` production posture is documented.
- [ ] Stable `/v1/*` routes have authorization coverage.
- [ ] `/metrics` protection requirement is documented.
- [ ] Secrets are absent from committed files and examples.
- [ ] Dependency audit is reviewed.
- [ ] Accepted dependency advisories, if any, are listed in release notes.
- [ ] SECURITY reporting instructions are current.
- [ ] No silent security limitation remains.

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
- [ ] README, docs index, roadmap, and quickstart match the final v1.0 state.
- [x] Known limitations in release notes match the scope freeze.
- [x] Upgrade notes in release notes match the migration policy.

## Accepted v1.0 Limitations

Before release, verify that these limitations are present in release notes:

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

These items must not block v1.0:

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

- [ ] Create annotated tag `v1.0.0`.
- [ ] Push release commit.
- [ ] Push tag.
- [ ] Confirm GitHub CI is green after push.
- [ ] Create GitHub release from `docs/releases/v1.0.0.md`.
- [ ] Verify release page renders expected notes.

## Post-Release

- [ ] Open v1.x follow-up issues for deferred scope.
- [ ] Open any waiver follow-up issues.
- [ ] Record first-user feedback channel.
- [ ] Monitor dependency advisories after release.
- [ ] Update roadmap with v1.x priorities.
