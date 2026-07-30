# Day 34: Docker Compose and Fresh Clone Runtime Path

## Goal

Start Phase 6 by making the v0.1 local runtime path clearer and closer to a
fresh-clone release experience.

Day 34 should establish this baseline:

```text
copy env -> install deps -> start services -> migrate -> run API/worker/Web
```

## Scope

Day 34 should cover:

- Full-stack Docker Compose service definitions for API, worker, Web, Postgres,
  and Redis.
- Container build files for Python runtime services and the Web app.
- `.env.example` cleanup and alignment with actual runtime variables.
- Quickstart update from Phase 1-only wording to current v0.1 workflow.
- README update for current backend, Web, Docker, and e2e commands.
- Makefile update for Web e2e verification.
- Phase 6 milestone updates where justified.
- Docker Compose config verification.
- Existing Python and Web quality gates.

Day 34 should not cover:

- Production Kubernetes or cloud deployment.
- Published container images.
- Secrets manager integration.
- HTTPS/TLS termination.
- Full release notes.
- CONTRIBUTING, SECURITY, or ROADMAP.

## Tasks

- [x] Check current git status.
- [x] Read Phase 6 milestones and current runtime docs.
- [x] Create Day 34 daily plan.
- [x] Add Python runtime Dockerfile.
- [x] Add Web Dockerfile.
- [x] Expand Docker Compose to full local stack.
- [x] Align `.env.example`.
- [x] Update README.
- [x] Update Quickstart.
- [x] Update Makefile verification commands.
- [x] Update milestones.
- [x] Run Docker Compose config verification.
- [x] Run Python quality gates.
- [x] Run Web quality gates.

## Acceptance

- [x] Docker Compose describes API, worker, Web, Postgres, and Redis.
- [x] `.env.example` documents current runtime variables.
- [x] Quickstart reflects the current v0.1 local workflow.
- [x] README points to current quality and smoke commands.
- [x] `docker compose config` passes.
- [x] Python tests pass.
- [x] Web lint/build/e2e passes.

## Verification

Run:

```bash
docker compose config
uv run ruff check .
uv run mypy .
uv run pytest
npm run lint
npm run build
npm run test:e2e
git diff --check
```

## Notes

- The first Docker Compose target is a credible local stack definition, not a
  cloud production deployment.
- Compose build/start may still require local Docker Desktop and network access
  for dependency download.
- Day 34 verified `docker compose config`; full `docker compose up --build`
  startup remains a Phase 6 release-hardening check.
