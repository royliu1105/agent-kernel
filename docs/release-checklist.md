# v0.1 Release Checklist

Use this checklist before tagging `v0.1.0`.

## Repository State

- [ ] Working tree is clean.
- [ ] Release branch is up to date with the target branch.
- [ ] Version references are reviewed.
- [ ] Known limitations are documented.
- [ ] Dependency audit risk is reviewed.

## Python Quality Gates

- [ ] `uv sync --dev`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest`
- [x] `uv run agent-kernel eval report evals/rag-smoke.json`

## Web Quality Gates

- [ ] `npm install`
- [x] `npm run lint`
- [x] `npm run build`
- [x] `npm run test:e2e`

## Docker and Runtime

- [x] `docker compose config`
- [x] `docker compose up --build`
- [x] API health check passes at `http://127.0.0.1:8000/healthz`.
- [x] Web Workbench loads at `http://127.0.0.1:3000`.
- [x] Worker starts and remains healthy enough to process queued runs.
- [ ] Fresh Postgres volume can run migrations.
- [ ] Object storage volume persists uploaded documents.

## Fresh Clone Quickstart

- [ ] Follow [Quickstart](quickstart.md) from a clean checkout.
- [x] Create an agent.
- [x] Create a mock run.
- [x] Queue the run.
- [x] Execute the worker once.
- [x] Inspect run output.
- [x] Inspect run events.
- [x] Run the RAG example.
- [x] Run the memory example.
- [x] Run the cheap eval.

## Documentation

- [ ] README is current.
- [ ] Docs index is current.
- [ ] Architecture docs are current.
- [ ] Interface docs are current.
- [ ] Feature spec index is current.
- [ ] Production config guide is current.
- [ ] CONTRIBUTING is current.
- [ ] SECURITY is current.
- [ ] ROADMAP is current.
- [ ] Release notes are current.

## Release Notes

- [ ] `docs/releases/v0.1.0.md` exists.
- [ ] Completed capabilities are listed.
- [ ] Known limitations are listed.
- [ ] Verification commands are listed.
- [ ] Upgrade notes are included.
- [ ] Public Alpha next steps are included.

## Tagging

- [ ] Create annotated tag `v0.1.0`.
- [ ] Push tag.
- [ ] Create GitHub release from release notes.
- [ ] Verify CI on release tag.

## Post-Release

- [ ] Open Public Alpha tracking issues.
- [ ] Review dependency advisories.
- [ ] Capture first external-user feedback.

## Latest Verification Notes

Day 37:

- Fresh-run backend quickstart path passed from a clean temporary working tree
  after fixing default SQLite migration directory creation.
- Fresh-run Web dependency install is not yet confirmed. `npm install` first
  failed under sandboxed npm cache/log access, then an elevated retry produced
  no progress output for multiple minutes and was interrupted.
- Full Docker Compose startup passed after `node:24-bookworm-slim` was pulled
  successfully and an Alembic revision id length bug was fixed.
- Docker Compose verification confirmed healthy API, healthy Web, healthy
  Postgres, healthy Redis, and a started worker.
- Local post-change gates passed: `ruff`, `mypy`, `pytest`, `rag-smoke eval`,
  `npm run lint`, `npm run build`, and `npm run test:e2e`.
- `docker compose config` passed.
