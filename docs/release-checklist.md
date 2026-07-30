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
- [ ] `uv run ruff check .`
- [ ] `uv run mypy .`
- [ ] `uv run pytest`
- [ ] `uv run agent-kernel eval report evals/rag-smoke.json`

## Web Quality Gates

- [ ] `npm install`
- [ ] `npm run lint`
- [ ] `npm run build`
- [ ] `npm run test:e2e`

## Docker and Runtime

- [ ] `docker compose config`
- [ ] `docker compose up --build`
- [ ] API health check passes at `http://127.0.0.1:8000/healthz`.
- [ ] Web Workbench loads at `http://127.0.0.1:3000`.
- [ ] Worker starts and remains healthy enough to process queued runs.
- [ ] Fresh Postgres volume can run migrations.
- [ ] Object storage volume persists uploaded documents.

## Fresh Clone Quickstart

- [ ] Follow [Quickstart](quickstart.md) from a clean checkout.
- [ ] Create an agent.
- [ ] Create a mock run.
- [ ] Queue the run.
- [ ] Execute the worker once.
- [ ] Inspect run output.
- [ ] Inspect run events.
- [ ] Run the RAG example.
- [ ] Run the memory example.
- [ ] Run the cheap eval.

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
