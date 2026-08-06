# Clean-Machine Release Rehearsal

This runbook defines the v1.0 release candidate clean-machine rehearsal.

The rehearsal answers:

```text
Can a maintainer reproduce the release from a fresh checkout without relying on
hidden local state?
```

Day 84 defines the plan. Day 85 executes the rehearsal and fixes release
blockers discovered by the run.

## Scope

Required checks:

- Fresh clone from the release branch or release candidate commit.
- Python dependency install through `uv`.
- Web dependency install through `npm`.
- SQLite migration and local runtime path.
- Deterministic release evals.
- Release smoke matrix.
- Quick load/soak gate.
- Docker Compose config validation.
- Full Docker Compose startup when Docker Desktop is available.
- API health check.
- Web Workbench load check.
- Worker startup check.
- Evidence capture.

Optional checks:

- Live OpenAI provider smoke.
- Real embeddings.
- pgvector retrieval quality with a realistic corpus.
- S3/MinIO interoperability.
- Browser e2e in multiple browsers.
- Longer soak runs.

Optional checks must not block the default rehearsal unless the release owner
explicitly promotes them to blockers.

## Environment Assumptions

Record these before starting:

```bash
sw_vers
git --version
uv --version
uv python list --only-installed
node --version
npm --version
docker --version
docker compose version
```

Expected baseline:

- Python 3.12 is available through `uv`.
- Node.js 24 or newer is available.
- Docker Desktop is running for Compose checks.
- No `OPENAI_API_KEY` is required for default rehearsal gates.

## Fresh Checkout

Use a temporary directory outside the normal development checkout:

```bash
mkdir -p /tmp/agent-kernel-rehearsal
cd /tmp/agent-kernel-rehearsal
git clone https://github.com/royliu1105/agent-kernel.git
cd agent-kernel
git status --short
git rev-parse HEAD
```

Expected:

```text
git status --short
```

prints no changes.

If rehearsing a specific release candidate commit:

```bash
git checkout <release-candidate-sha>
```

## Dependency Install

Install Python dependencies:

```bash
uv sync --dev
```

Install Web dependencies:

```bash
npm install
```

Expected:

- Both commands complete without manual package edits.
- No dependency install requires secrets.
- Any vulnerability warnings are reviewed against
  [Dependency Audit Review](dependency-audit.md).

## SQLite Quick Path

Run migrations without Docker:

```bash
unset DATABASE_URL
uv run alembic upgrade head
```

Run core local checks:

```bash
uv run agent-kernel --version
uv run agent-kernel-worker --help
```

Expected:

- Migrations complete.
- CLI and worker command surfaces load.

Start the API on a rehearsal-specific port to avoid collisions with an existing
development server:

```bash
AGENT_KERNEL_API_HOST=127.0.0.1 AGENT_KERNEL_API_PORT=8011 uv run agent-kernel-api
```

In another terminal:

```bash
curl http://127.0.0.1:8011/healthz
```

Expected:

```json
{"status":"ok","service":"agent-kernel-api"}
```

Stop the foreground API with `Ctrl-C`.

## Release Gates

Run:

```bash
uv run ruff check .
uv run mypy .
uv run pytest
make release-eval
make release-smoke
make release-load-soak
```

Expected:

- All commands exit with status `0`.
- `make release-eval` reports all eval cases passing.
- `make release-smoke` reports selected critical-path tests passing.
- `make release-load-soak` reports `"passed": true`.

## Web Gates

Run:

```bash
npm run lint
npm run build
npm run test:e2e
```

Expected:

- Next.js type generation succeeds.
- Production build succeeds.
- Playwright smoke tests pass.

## Docker Compose Rehearsal

Validate configuration:

```bash
docker compose config
```

If another local Agent Kernel stack is already using the default ports, verify
an isolated host-port mapping:

```bash
AGENT_KERNEL_API_PORT=8011 \
AGENT_KERNEL_WEB_PORT=3011 \
AGENT_KERNEL_POSTGRES_PORT=55432 \
AGENT_KERNEL_REDIS_PORT=56379 \
docker compose config
```

Start the full stack:

```bash
docker compose up --build
```

In another terminal, check:

```bash
curl http://127.0.0.1:8000/healthz
curl -I http://127.0.0.1:3000
docker compose ps
```

Expected:

- Postgres is healthy.
- Redis is healthy.
- API is healthy.
- Web serves `http://127.0.0.1:3000`.
- Worker starts and remains able to poll queued runs.

Stop the stack:

```bash
docker compose down
```

Do not delete volumes during the rehearsal unless specifically testing fresh
volume behavior.

## Evidence Capture

Record:

- Date and timezone.
- Host OS and architecture.
- Tool versions.
- Commit SHA.
- Whether Docker Desktop was running.
- Each command run.
- Exit status.
- Short success output or failure output.
- Any manual workarounds used.

Use this template:

```text
Date:
Host:
Commit:
Docker available:

Command:
Result:
Notes:
```

## Failure Classification

Classify failures as:

- `blocker`: A documented required path fails from a clean checkout.
- `documentation`: The product works but the runbook or quickstart is wrong.
- `environment`: The host is missing a documented prerequisite.
- `network`: External registry or package download failed.
- `optional`: A non-blocking scenario failed.

Blockers must be fixed before v1.0 release readiness can be claimed.

Documentation failures should be fixed immediately because they create user
trust problems even when the code works.

Network failures require rerun evidence before they are dismissed.

## Day 85 Handoff

After running the rehearsal, update:

- [Milestones](milestones.md)
- [Release Checklist](release-checklist.md) or the v1.0 checklist when created.
- [Troubleshooting](troubleshooting.md) for any recurring failure mode.
- Release notes limitations if a known gap remains.

Day 85 should only mark the clean-machine rehearsal as passed after the required
checks above have actual run evidence.
