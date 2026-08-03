# Phase 6 Summary: v0.1 Release Hardening

## Status

Phase 6 is complete as a v0.1 release-candidate foundation:

```text
Day 34-36: Deployment, Docs, and v0.1 Release
```

Phase 6 delivered the local stack definition, release-facing documentation,
examples, contribution and security policies, roadmap, release checklist,
v0.1.0 release notes, architecture/spec/interface snapshots, and final local
quality-gate verification.

This is a release-candidate state, not a published GitHub release.

## What Users Can Do Now

Developers can clone the repository, install dependencies, run migrations,
exercise the core runtime with mock models, run RAG and memory examples, execute
deterministic evals, open the Web Workbench, and inspect release documentation.

Current user-facing shape:

```text
Local runtime:
install deps -> migrate DB -> create agent/run -> queue -> worker executes -> inspect timeline

RAG example:
create KB -> upload document -> ingest -> chunk -> index -> retrieve with citations

Memory example:
create scoped memory -> list memory -> use explicit memory context in runtime

Web:
start Workbench -> inspect dashboard/agents/runs/approvals/knowledge/evals/settings

Release docs:
quickstart -> production config -> examples -> roadmap -> release checklist -> release notes
```

## Completed Release-Hardening Work

- Full-stack Docker Compose service definitions.
- Python API/worker Dockerfile.
- Web Dockerfile.
- `.dockerignore`.
- `.env.example` alignment with actual runtime variables.
- README update for v0.1 commands and stack shape.
- Quickstart rewrite for current v0.1 workflows.
- Production configuration guide.
- Examples README.
- Mock run input fixture.
- Memory fixture.
- Deployment playbook RAG fixture.
- CONTRIBUTING guide.
- SECURITY policy.
- ROADMAP.
- Architecture v0.1 release snapshot.
- Product interface v0.1 surface.
- Feature spec status table.
- Release checklist.
- v0.1.0 release notes.
- Day 34-36 daily plans.
- Phase 6 milestone updates.

## Small Runtime Improvement

Day 36 discovered that examples used `@examples/*.json` arguments, while the CLI
only accepted inline JSON strings.

The CLI now supports JSON object arguments in both forms:

```bash
--input '{"task":"hello","model":"mock:echo"}'
--input @examples/mock-run.json
```

This also applies to other JSON object options such as memory content and
metadata.

## Verification

Final local verification passed:

```bash
docker compose config
uv run ruff check .
uv run mypy .
uv run pytest
uv run agent-kernel eval report evals/rag-smoke.json
npm run lint
npm run build
npm run test:e2e
git diff --check
```

Current results:

```text
Python tests: 190 passed
Cheap eval: passed
Playwright smoke tests: 2 passed
Docker Compose config: passed
```

Example verification passed against a temporary SQLite database and temporary
object store:

- Mock agent run.
- Worker execution.
- Run inspection.
- Run event timeline inspection.
- Knowledge base creation.
- Document upload.
- Ingestion.
- Chunking.
- Indexing.
- Retrieval with citations.
- Scoped memory creation and listing.

## Docker Compose Verification

`docker compose up --build -d` was attempted twice.

Verified:

- Python API image build completed.
- Python worker image build completed.
- Compose configuration is valid.

Previously blocked:

```text
Web image build could not fetch node:24-bookworm-slim metadata because Docker Hub token requests timed out.
```

After the Node base image was pulled successfully on Day 37, Docker Compose
reached service startup and exposed a Postgres migration bug: one Alembic
revision id exceeded the default `alembic_version.version_num VARCHAR(32)`
column. Day 37 fixed that revision id and added a regression test.

These milestone acceptance items remain unchecked:

- CI is green.

Day 37 follow-up:

- Fresh-run backend quickstart passed from a clean temporary working tree after
  fixing default SQLite migration directory creation.
- Fresh-run Web dependency install is still not confirmed because `npm install`
  made no progress for multiple minutes during verification.
- Docker Compose full stack passed with healthy API, healthy Web, healthy
  Postgres, healthy Redis, and a started worker.

## v0.1 Release Readiness

v0.1 is ready as a local release candidate:

- Core backend runtime is implemented and tested.
- Agent tools, approvals, RAG, memory, observability, and evals are present.
- Web Workbench product surface exists and has smoke tests.
- Release docs are coherent.
- Examples are verified locally.

v0.1 should not be tagged as final until:

- A complete clean fresh-clone quickstart pass, including Web dependency
  install, is completed.
- GitHub CI is verified green.
- Dependency audit risk is reviewed.

## Known Release Risks

- Fresh-run Web dependency install is not yet confirmed.
- `npm install` reports 3 high severity vulnerabilities.
- Web Workbench is mostly fixture-backed.
- Auth/RBAC/tenant isolation are not implemented.
- Provider-native function calling is not implemented.
- Live Web API integration is incomplete.
- Redis is not yet the durable runtime queue.
- OpenTelemetry exporters and Prometheus endpoint are not implemented.
- S3/MinIO object storage backend is not implemented.

## Next Phase

Public Alpha starts on Day 37:

```text
Day 37-51: Public Alpha
```

The next focus is turning the release candidate into something an early external
user can run without maintainer help:

- Run complete fresh-clone quickstart, including Web dependency install.
- Verify GitHub CI.
- Improve troubleshooting docs.
- Improve examples.
- Review npm audit findings.
- Add missing tests around fragile release paths.
- Improve Web UI polish.
- Expand behavior eval coverage.
- Capture first external-user feedback.
