# v0.1 Release Checklist

This checklist records the `v0.1.0` release status.

## Repository State

- [x] Working tree is clean before release tagging.
- [x] Release branch is up to date with the target branch.
- [x] Version references are reviewed.
- [x] Known limitations are documented.
- [x] Dependency audit risk is reviewed.

## Python Quality Gates

- [x] `uv sync --dev`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest`
- [x] `uv run agent-kernel eval report evals/rag-smoke.json`

## Web Quality Gates

- [x] `npm install`
- [x] `npm run lint`
- [x] `npm run build`
- [x] `npm run test:e2e`

## Docker and Runtime

- [x] `docker compose config`
- [x] `docker compose up --build`
- [x] API health check passes at `http://127.0.0.1:8000/healthz`.
- [x] Web Workbench loads at `http://127.0.0.1:3000`.
- [x] Worker starts and remains healthy enough to process queued runs.
- [x] Fresh Postgres volume can run migrations.
- [x] Object storage volume persists uploaded documents in the local object store path.

## Fresh Clone Quickstart

- [x] Follow [Quickstart](quickstart.md) from a clean checkout.
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

- [x] README is current.
- [x] Docs index is current.
- [x] Architecture docs are current.
- [x] Interface docs are current.
- [x] Feature spec index is current.
- [x] Production config guide is current.
- [x] CONTRIBUTING is current.
- [x] SECURITY is current.
- [x] ROADMAP is current.
- [x] Release notes are current.

## Release Notes

- [x] `docs/releases/v0.1.0.md` exists.
- [x] Completed capabilities are listed.
- [x] Known limitations are listed.
- [x] Verification commands are listed.
- [x] Upgrade notes are included.
- [x] Public Alpha next steps are included.

## Tagging

- [x] Create annotated tag `v0.1.0`.
- [x] Push tag.
- [x] Create GitHub release from release notes.
- [x] Verify CI on the release commit.

## Post-Release

- [ ] Open Public Alpha tracking issues.
- [ ] Review dependency advisories.
- [ ] Capture first external-user feedback.

## Latest Verification Notes

Day 37:

- Fresh-run backend quickstart path passed from a clean temporary working tree
  after fixing default SQLite migration directory creation.
- Fresh-run Web dependency install was not confirmed on Day 37. `npm install`
  first failed under sandboxed npm cache/log access, then an elevated retry
  produced no progress output for multiple minutes and was interrupted. Day 38
  later confirmed fresh-run Web install, lint, and build from a clean temporary
  checkout.
- Full Docker Compose startup passed after `node:24-bookworm-slim` was pulled
  successfully and an Alembic revision id length bug was fixed.
- Docker Compose verification confirmed healthy API, healthy Web, healthy
  Postgres, healthy Redis, and a started worker.
- Local post-change gates passed: `ruff`, `mypy`, `pytest`, `rag-smoke eval`,
  `npm run lint`, `npm run build`, and `npm run test:e2e`.
- `docker compose config` passed.

Day 38:

- Fresh-run Web path passed from a clean temporary checkout:
  `npm install`, `npm run lint`, and `npm run build`.
- Dependency audit risk was reviewed and documented in
  [Dependency Audit Review](dependency-audit.md).
- `npm audit --json` still reports 3 high severity findings through Next.js
  transitive `postcss` and optional transitive `sharp`.
- No forced audit fix was applied. Latest stable Next.js was already installed,
  and the suggested fix path was incompatible with this project.
- GitHub API reported zero visible workflow runs. The repository default branch
  is `master`, but CI previously listened to `main` push only. Day 38 updates
  CI to listen to `master`, `main`, PRs, and manual dispatch.
- After the CI trigger fix was pushed, the remote GitHub Actions run completed
  successfully for `python`, `web`, and `compose`.

Post-release:

- `v0.1.0` was published as a GitHub Release.
- GitHub CI for the release commit was verified green.
- The next canonical plan is [Post-v0.1 Completion Plan](post-v0.1-plan.md).
