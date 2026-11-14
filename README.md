# Agent Kernel

Agent Kernel is a self-hosted, observable, evaluable, resumable production-grade AI Agent Runtime for building real agent applications with tools, memory, knowledge bases, human approval, and workflows.

The canonical project baseline is captured in [docs/README.md](docs/README.md).

Run the Docker-only local stack with [docs/quickstart.md](docs/quickstart.md)
and [Docker operations](docs/docker-local.md).

If local setup gets stuck, use [docs/troubleshooting.md](docs/troubleshooting.md).

Current release:

- [Agent Kernel v1.0.0](https://github.com/royliu1105/agent-kernel/releases/tag/v1.0.0), published 2026-08-07.

Current development:

- The authorized [observability completion](docs/observability-completion-plan.md)
  workstream tracks centralized logs, trace backend and SMTP
  alerts. Implementation/verification are tracked separately; external email
  delivery is not accepted without inbox evidence.
  The optional single-host Loki/Tempo/Alertmanager/Mailpit profile has passed
  local end-to-end verification and exact-commit remote CI; see the ledger for evidence.
- [Real-scenario acceptance and controlled pilot](docs/real-scenario-pilot-plan.md)
  has started PV1 contract preparation; required decisions remain pending and
  PV2-PV6 have not started. No live/user-pilot result exists.
  Other foundation feature expansion is frozen.
- [Reference comparison](docs/reference-project-comparison.md) records the
  code/test review. Its [follow-up plan](docs/reference-follow-up-plan.md) owns
  pilot-entry checks and deferred enhancements. CF1's minimal memory-context
  repair passed code review and local regressions, with acceptance still pending;
  see its [verification record](docs/reviews/2026-11-14-cf1-minimal-repair.md).
  Its candidate CI passed, but the active local Docker stack has not been updated
  with CF1. Deployment/pilot acceptance is still pending. CF2 now has an
  [isolated authenticated API/CLI rehearsal](docs/reviews/2026-11-14-cf2-workflow-inventory.md#docker-rehearsal-evidence)
  using offline model fixtures. Web authentication and pilot-profile acceptance
  remain open; CF3-CF8 remain deferred/conditional.
- Completed [post-v1.0 capability hardening](docs/capability-hardening-plan.md)
  retains the implementation evidence and explicit limits.
- `master` contains unreleased changes beyond the `v1.0.0` tag. Historical
  release CI does not verify those changes; implementation CI and pilot
  acceptance are separate evidence, and live pilot results do not exist yet.
- Review the [upgrade and migration policy](docs/upgrade-migration-policy.md)
  before upgrading an existing deployment.

Historical delivery:

- [Public Alpha, Beta, and v1.0 plan](docs/post-v0.1-plan.md)
- [v1.0.0 release notes](docs/releases/v1.0.0.md)
- [Public Alpha summary](docs/public-alpha-summary.md)
- [Feedback templates](.github/ISSUE_TEMPLATE)

Project shape:

```text
Python API + CLI + worker + PostgreSQL/pgvector storage + RAG/memory/tools/evals + Next.js Workbench
```

## Local Development

The default runtime is **Docker only**, including API, Worker, Web, PostgreSQL,
Redis and the full observability stack. Mock models and a local Mailpit inbox
require no external model/SMTP credentials. See [Docker operations](docs/docker-local.md)
for data, private Grafana credentials, endpoints and the legacy-data boundary.

```bash
make docker-up
make docker-status
make docker-logs SERVICE=worker
make docker-stop
```

`make docker-down` preserves data volumes. Do not start host API/Worker/Next
processes alongside this stack. The Web is at `http://127.0.0.1:3000`, API docs
at `http://127.0.0.1:8000/docs`, Grafana at `http://127.0.0.1:3090` and Mailpit
at `http://127.0.0.1:8025`. This trusted localhost profile is not public hosting.

### Contributor Toolchain

Required tools:

- Python 3.12 through `uv`
- Node.js 24+
- Docker Desktop
- `direnv`
- `pre-commit`

Set up the workspace:

```bash
uv sync
npm install
```

Run backend checks:

```bash
uv run ruff check .
uv run mypy .
make test-db-up
make test
make test-db-down
```

PostgreSQL is required for database tests; there is no SQLite fallback.
The test service has separate disposable storage from your running app.
See [PostgreSQL-only storage and testing](docs/postgresql-only.md).

Run the CLI in the active Docker environment:

```bash
sh scripts/local-stack.sh exec -T api agent-kernel --version
```

Run frontend checks:

```bash
npm run lint
npm run build
npm run test:e2e
```

Validate infrastructure config:

```bash
docker compose config
```

Use `make docker-check` for the default merged local profile. Bare
`docker compose` refers to the lower-level base template, not the full default.

Run the standard local verification set:

```bash
make verify
make verify-web
```

`make verify` avoids browser e2e tests by default. `make verify-web` includes Playwright.

## Feedback

Agent Kernel is preparing real-scenario acceptance and a controlled pilot. Please
use GitHub Issues for reproducible bugs, focused feature requests, or first-run
feedback. Redact secrets, API keys, tokens, private documents, and private logs
before sharing output.
