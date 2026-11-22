# Contributing to Agent Kernel

Thank you for considering a contribution.

Agent Kernel is a self-hosted single-agent runtime (API + Worker + CLI + Web).
Contributions should improve real runtime capability, reliability,
documentation, examples, or release quality—not expand into deferred CF items
without an explicit proposal.

## Development Setup

Start all local runtime services with `make docker-up`; see
[Docker-only local runtime](docs/docker-local.md). Host Python/Node are for
short-lived contributor tools, not the default API/Worker/Web startup path.
Local browser smoke tests target the Docker Web at port 3000 by default.

Required tools:

- Python 3.12 through `uv`.
- Node.js 24+.
- Docker Desktop.
- `direnv` (recommended for host tooling).
- `pre-commit`.

Install dependencies:

```bash
uv sync
npm install
```

Optional host-tool/custom-deployment environment (not read by the Docker wrapper):

```bash
cp .env.example .env
```

Fresh-clone intent (no hidden local state): follow
[clean-machine rehearsal](docs/clean-machine-rehearsal.md) when validating a
release path; day-to-day contributors normally use `make docker-up` on an
existing checkout.

## Repository Shape

```text
apps/api      - FastAPI API
apps/cli      - Typer CLI
apps/worker   - queued-run worker
apps/web      - Next.js Workbench
packages/*    - bounded Python runtime packages
docs/         - canonical planning and user docs
examples/     - runnable local examples
tests/        - Python unit/integration tests
evals/        - deterministic eval datasets
```

Respect module boundaries. Do not import app code from core packages.

Do not add a `resource/` directory or vendor third-party reference trees into
this repository. Optional maintainer comparison notes (no local tree required):
[docs/reference-project-comparison.md](docs/reference-project-comparison.md).

## Quality Gates

Run Python checks:

```bash
uv run ruff check .
uv run mypy .
make test-db-up
make test
uv run agent-kernel eval report evals/rag-smoke.json
```

Database tests require the dedicated PostgreSQL test service via
`make test-db-up` / `AGENT_KERNEL_TEST_POSTGRES_URL`. **Never** point tests or
drills at the active Docker runtime database (`make docker-up`). Make supplies
the test URL; direct pytest invocations need `AGENT_KERNEL_TEST_POSTGRES_URL`.
See [test isolation](docs/postgresql-only.md). Use `make test-db-down` after
database checks and release gates finish.

Run Web checks:

```bash
npm run lint
npm run build
npm run test:e2e
```

Validate Docker Compose:

```bash
docker compose config
```

Convenience targets:

```bash
make verify
make verify-web
```

## Pull Request Expectations

Every meaningful pull request should include:

- A clear problem statement.
- Focused implementation.
- Tests or evals for changed behavior.
- Documentation updates when user-facing behavior changes.
- Known limitations when something is intentionally deferred.

Prefer small, reviewable pull requests. Do not open foundation expansion (CF3–CF8
multi-agent, hybrid retrieval, etc.) unless a maintainer authorized that scope.

## Issues and Feedback

Use the GitHub issue templates for:

- Reproducible bugs.
- Focused feature requests.
- First-run feedback.

Good issues include exact commands or UI actions, expected behavior, actual
behavior, environment details, and redacted logs when useful.

Do not include secrets, API keys, tokens, private documents, or private logs.

## Coding Guidelines

- Follow existing package boundaries and naming.
- Keep domain models in core/runtime packages, not API handlers.
- Keep long-running execution in the worker.
- Use deterministic mock or replay providers in tests.
- Avoid network-dependent tests in default CI.
- Keep security-sensitive behavior explicit and auditable.
- Do not commit generated local runtime data.
- Tool policy: `ToolPolicyEvaluator` is the only decision engine. Production
  Runs go through `RunExecutionService` + `create_runtime_tool_registry`.
  Use `PolicyAwareToolExecutor` only for direct non-Run invokes (examples /
  unit tests). Do not teach contributors that the wrapper is the Run path; see
  [docs/specs/tool-calling.md](docs/specs/tool-calling.md#how-tools-are-invoked-current).

## Documentation Guidelines

Update docs when changing:

- API or CLI behavior.
- Runtime state transitions.
- Tool policy or approval behavior.
- RAG or memory behavior.
- Observability or eval behavior.
- Deployment or local setup.

### Current vs archive

- **Current** docs live under `docs/` (overview, quickstart, docker-local, pilot
  ledger, specs). Start from [docs/README.md](docs/README.md).
- **Archive / historical** material lives under `docs/archive/` (and stubs such
  as `docs/daily/README.md`). Day 1–90 checklists are history, not acceptance
  criteria. Prefer updating current ledgers rather than restarting a day-number
  schedule.
- Do not cite deferred CF items (CF3–CF8) as shipped features in README,
  CONTRIBUTING, or user-facing docs.

## Security

Do not include secrets in issues, pull requests, fixtures, logs, screenshots, or
test data.

Default `make docker-up` runs with application auth **disabled** on loopback.
That is for a trusted local machine only—not a public deployment template.

For vulnerabilities, follow [SECURITY.md](SECURITY.md).
