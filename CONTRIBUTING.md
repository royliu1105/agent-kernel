# Contributing to Agent Kernel

Thank you for considering a contribution.

Agent Kernel is built as a production-grade learning and open-source project.
Contributions should improve real runtime capability, reliability,
documentation, examples, or release quality.

## Development Setup

Required tools:

- Python 3.12 through `uv`.
- Node.js 24+.
- Docker Desktop.
- `pre-commit`.

Install dependencies:

```bash
uv sync
npm install
```

Optional local environment:

```bash
cp .env.example .env
```

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

## Quality Gates

Run Python checks:

```bash
uv run ruff check .
uv run mypy .
uv run pytest
uv run agent-kernel eval report evals/rag-smoke.json
```

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

Prefer small, reviewable pull requests.

## Issues and Public Alpha Feedback

Use the GitHub issue templates for:

- Reproducible bugs.
- Focused feature requests.
- Public Alpha first-run feedback.

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

## Documentation Guidelines

Update docs when changing:

- API or CLI behavior.
- Runtime state transitions.
- Tool policy or approval behavior.
- RAG or memory behavior.
- Observability or eval behavior.
- Deployment or local setup.

Use `docs/daily/` for short-lived implementation checklists and phase summaries
for completed phase records.

## Security

Do not include secrets in issues, pull requests, fixtures, logs, screenshots, or
test data.

For vulnerabilities, follow [SECURITY.md](SECURITY.md).
