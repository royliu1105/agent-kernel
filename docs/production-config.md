# Production Configuration Guide

This guide describes the production configuration expectations for Agent Kernel
v0.1.

v0.1 is a self-hosted runtime foundation. It is deployable as separate API,
worker, Web, Postgres, Redis, and object-storage components, but it is not yet a
fully managed cloud platform.

## Runtime Processes

Agent Kernel has these production-facing processes:

```text
API      - FastAPI service for state, inspection, and control APIs
Worker   - background queued-run executor
Web      - Next.js Agent Workbench
Postgres - relational runtime state and pgvector-ready storage
Redis    - future queue/cache dependency, included in the local stack
Objects  - document upload and parsed artifact storage
```

Run API and worker as separate processes. The API should not execute long-running
agent loops directly.

## Required Environment Variables

Core runtime:

```bash
AGENT_KERNEL_ENV=production
AGENT_KERNEL_LOG_LEVEL=info
DATABASE_URL=postgresql+psycopg://user:password@postgres:5432/agent_kernel
REDIS_URL=redis://redis:6379/0
AGENT_KERNEL_OBJECT_STORE_ROOT=/data/objects
```

Web:

```bash
NEXT_PUBLIC_AGENT_KERNEL_API_URL=https://agent-kernel.example.com
```

Optional provider credentials:

```bash
OPENAI_API_KEY=
```

Use `mock:*` and `replay:*` providers for deterministic local and CI workflows.
Use `openai:*` models only when `OPENAI_API_KEY` is configured.

## Storage

Recommended production storage:

```text
Postgres + pgvector image
```

SQLite is supported for local development only. Do not use SQLite as the primary
multi-user production database.

Object storage in v0.1 is a local filesystem-backed abstraction controlled by:

```bash
AGENT_KERNEL_OBJECT_STORE_ROOT=/data/objects
```

Mount this path as durable storage in container deployments. S3/MinIO-compatible
object storage is a later enhancement.

## Database Migrations

Run migrations before starting API and worker:

```bash
uv run alembic upgrade head
```

The local Docker Compose API service runs migrations before starting the API.
For production deployments, prefer an explicit migration job so application
startup and schema migration failure modes are separated.

## API

Recommended API command:

```bash
agent-kernel-api
```

Health check:

```http
GET /healthz
```

Expected response:

```json
{"status":"ok","service":"agent-kernel-api"}
```

## Worker

Recommended worker command:

```bash
agent-kernel-worker --loop --limit 25 --poll-interval 2
```

Run at least one worker process for queued agent execution.

Current worker behavior uses persisted queued runs as the MVP queue. The Beta
storage layer now includes worker leases and an explicit stuck-run recovery
mode:

```bash
agent-kernel-worker --recover-stuck --limit 100
```

Recovery marks expired `running` or `resuming` runs as failed instead of
automatically requeueing them. This avoids blindly repeating side effects.
The worker polling loop has not yet switched to lease-backed claiming.
Redis-backed scheduling and advanced retry queues are later Beta slices.

## Web

Recommended Web command after build:

```bash
npm --workspace apps/web exec -- next start --hostname 0.0.0.0
```

The Web Workbench is an operator console. In v0.1, most Web data is
fixture-backed and intended to show the product surface. Do not represent it as
a fully live production console until live Web API integration is implemented.

## Secrets

Do not commit secrets.

Production deployments should inject secrets through the deployment platform:

```text
Docker secrets, Kubernetes secrets, cloud secret manager, or CI/CD environment secrets
```

At minimum, treat these as secrets:

- `DATABASE_URL`
- `REDIS_URL` when credentials are present
- `OPENAI_API_KEY`
- Plaintext Agent Kernel API keys returned during creation
- Future auth signing keys
- Future encryption keys

## API Authentication

Beta API key authentication can be enabled with:

```text
AGENT_KERNEL_API_KEY_AUTH_ENABLED=true
```

When enabled:

- `/healthz` remains public.
- API keys can be supplied with `Authorization: Bearer <key>`.
- API keys can also be supplied with `X-Agent-Kernel-Api-Key`.
- Missing, invalid, revoked, expired, or disabled-principal API keys are
  rejected with `401 Unauthorized`.
- Valid API keys load the principal, key, and workspace memberships into the
  request auth context.
- Existing `/v1/*` routes enforce route-level permissions and return
  `403 Forbidden` when the authenticated role lacks the required permission.

Local quickstart flows keep API key authentication disabled by default. Route
permission checks currently use the authenticated API key's workspace as the
request workspace. Object-level workspace scoping is added in later Beta
slices.

Current object-level workspace scoping:

- Agents are created and read within the authenticated API key workspace.
- Runs are created and read within the authenticated API key workspace.
- Approval list, detail, approve, reject, and resume approval prechecks are
  scoped through the related run workspace.
- Knowledge, memory, document, tool-call, eval, and observability resources are
  scoped in later Beta slices.

See [Auth and RBAC](auth-rbac.md) for the full role, permission, object-scope,
and security test matrix.

## Networking

Expose only the API and Web services publicly.

Recommended defaults:

```text
API: 8000 behind HTTPS reverse proxy
Web: 3000 behind HTTPS reverse proxy
Postgres: private network only
Redis: private network only
Object store path: private mounted storage only
```

## Observability

v0.1 includes trace IDs, structured logs, metrics recorders, and deterministic
eval reports.

Recommended production log format:

```text
JSON logs with trace_id, run_id, agent_id, operation, status, latency, tokens, cost
```

OpenTelemetry exporters and Prometheus endpoints are not implemented yet.

## Security Posture

Current v0.1 safety controls:

- Tool risk levels.
- Policy decisions.
- Human approval records.
- Approval interrupt/resume.
- Audit timeline for tool calls and decisions.
- Sensitive structured-log field redaction.

Not implemented yet:

- End-user authentication.
- Role-based authorization.
- Tenant isolation.
- Browser session management.
- Remote sandbox execution.
- Secrets manager integration.

Do not deploy v0.1 as a public multi-tenant service without adding auth,
authorization, tenant isolation, network controls, and secret management.

## Local Compose Baseline

Validate the local stack definition:

```bash
docker compose config
```

Start the local stack:

```bash
docker compose up --build
```

Services:

```text
API: http://127.0.0.1:8000
Web: http://127.0.0.1:3000
Postgres: localhost:5432
Redis: localhost:6379
```

## Release-Hardening Checklist

Before calling a deployment production-ready:

- Run full CI.
- Run `docker compose up --build` from a clean checkout.
- Verify `/healthz`.
- Verify migrations from an empty Postgres volume.
- Verify worker can process a queued mock run.
- Verify object storage path persists uploaded documents.
- Verify Web Workbench starts.
- Review `npm audit`.
- Review Python dependency advisories.
- Confirm secrets are injected, not committed.
- Confirm public network exposure is limited to API/Web.
