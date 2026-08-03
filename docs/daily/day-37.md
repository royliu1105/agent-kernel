# Day 37: Public Alpha Release Blocker Triage

## Goal

Start Public Alpha by reducing the remaining v0.1 release-candidate risks that
would block a new user from running the project.

Day 37 should focus on:

```text
release candidate -> fresh-run validation -> troubleshooting docs -> honest blocker status
```

## Scope

- Fresh-clone quickstart validation from a clean temporary checkout.
- Docker Compose full-stack startup retry.
- Troubleshooting documentation for the most likely local setup failures.
- Release checklist and milestone updates based only on verified results.

## Non-Scope

- New agent runtime features.
- Provider-native function calling.
- Web Workbench live-data rewrite.
- Public Alpha announcement.
- GitHub release tagging.

## Tasks

- [x] Review v0.1 release checklist and Public Alpha milestone.
- [x] Add Day 37 daily plan.
- [x] Add troubleshooting guide for local setup and release verification failures.
- [x] Link troubleshooting guide from the documentation index.
- [x] Retry Docker Compose full-stack startup.
- [x] Validate fresh-clone quickstart path in a temporary checkout.
- [x] Fix default SQLite migration failure discovered during fresh-run validation.
- [x] Update release checklist with verified status and remaining blockers.
- [x] Update Public Alpha milestone if Day 37 completes a milestone item.

## Acceptance

- [x] Troubleshooting docs explain common Docker, uv, npm, port, and service health failures.
- [x] Docker Compose status is verified or the blocker is documented with concrete output.
- [x] Fresh-clone quickstart status is verified or the blocker is documented with concrete output.
- [x] Release checklist remains honest: only verified items are checked.
- [x] Public Alpha next work is clear.

## Verification

- [x] `docker compose config`
- [x] `docker compose up --build`
- [x] Fresh temporary checkout quickstart backend commands.
- [ ] Fresh temporary checkout Web dependency install.
- [x] Relevant local quality gates after documentation/code changes.

## Notes

- Day 37 starts after v0.1 release-candidate closure.
- Treat this as release engineering, not feature expansion.
- Do not mark `v0.1.0` as ready until fresh-clone and full-stack checks are
  confirmed.
- Fresh-run validation discovered a real SQLite bug: Alembic migrations did not
  create the default `.agent-kernel/` database directory before opening SQLite.
  Day 37 fixed this in the storage configuration boundary.
- Verified fresh-run backend path:
  `uv sync -> alembic upgrade head -> API healthz -> agent create -> run create -> run queue -> worker once -> inspect/events -> RAG upload/ingest/chunk/index/search -> memory create/list -> rag-smoke eval`.
- Docker Compose initially failed while fetching Docker Hub auth metadata for
  `node:24-bookworm-slim`: `failed to fetch oauth token ... i/o timeout`.
  After the base image was pulled successfully, Compose exposed a real
  Postgres migration bug: one Alembic revision id exceeded the default
  `alembic_version.version_num VARCHAR(32)` column.
- Day 37 fixed the migration revision id from
  `0004_create_knowledge_base_tables` to `0004_create_kb_tables` and added a
  regression test that enforces the 32-character Alembic revision limit.
- Verified Docker Compose full stack after the fix:
  API healthy at `http://127.0.0.1:8000/healthz`, Web healthy at
  `http://127.0.0.1:3000`, Postgres healthy, Redis healthy, and worker started.
- Fresh-run `npm install` was blocked after multiple minutes without progress.
  The first sandboxed attempt failed writing npm logs under `~/.npm`; the
  elevated attempt was interrupted after no output.
- Local post-change gates passed:
  `ruff`, `mypy`, `pytest`, `rag-smoke eval`, `npm run lint`,
  `npm run build`, and `npm run test:e2e`.
