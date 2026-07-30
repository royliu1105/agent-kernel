# Day 36: v0.1 Release Closure

## Goal

Close the 36-day v0.1 milestone with release-ready documentation, examples, and
verification records.

Day 36 should establish this release baseline:

```text
architecture/spec snapshot -> examples verification -> release checklist -> release notes
```

## Scope

Day 36 should cover:

- Architecture documentation update for the current v0.1 runtime shape.
- Feature spec index update for implemented/deferred status.
- Product interface update from draft-only language to v0.1 surface.
- Release checklist.
- v0.1.0 release notes.
- Example workflow verification where practical.
- Docker Compose startup verification attempt.
- Phase 6 milestone updates.
- Final Python and Web quality gates.

Day 36 should not cover:

- New runtime features.
- Public Alpha feature expansion.
- Cloud deployment automation.
- Publishing a GitHub release.

## Tasks

- [x] Check current git status.
- [x] Read Phase 6 milestones and release-facing docs.
- [x] Create Day 36 daily plan.
- [x] Update architecture docs.
- [x] Update feature spec index.
- [x] Update product interfaces.
- [x] Add release checklist.
- [x] Add v0.1.0 release notes.
- [x] Add v0.1 product snapshot.
- [x] Add Phase 6 summary.
- [x] Verify examples where practical.
- [x] Attempt full Docker Compose startup verification.
- [x] Update milestones.
- [x] Run final Python quality gates.
- [x] Run final Web quality gates.

## Acceptance

- [x] Architecture docs reflect the v0.1 runtime shape.
- [x] Feature specs clearly separate implemented and deferred capabilities.
- [x] Release checklist exists.
- [x] v0.1.0 release notes exist.
- [x] v0.1 product snapshot exists.
- [x] Phase 6 summary exists.
- [x] Example workflows are verified or documented with honest limitations.
- [x] Docker Compose full-stack startup is verified or documented with blocker.
- [x] Fresh clone path is clear from docs.
- [x] CI-equivalent local gates pass.

## Verification

Run:

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

## Notes

- Do not mark a release acceptance item complete unless it was actually
  verified.
- If Docker build/start fails due to local Docker or network constraints, record
  the blocker explicitly.
- Example verification passed for mock run, RAG search, memory, and cheap eval
  paths using a temporary SQLite database and object-store directory.
- Full `docker compose up --build -d` was attempted twice. Python API/worker
  image build succeeded, but Web image build could not fetch
  `node:24-bookworm-slim` metadata because Docker Hub token requests timed out.
  Keep `Docker Compose starts full stack` unchecked in milestones until this is
  verified from a clean network path.
