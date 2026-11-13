# Production Configuration Guide

This guide describes the current production configuration expectations for
Agent Kernel deployments. Use release-matched documentation when operating an
older tag; historical release notes do not define the current configuration.

Agent Kernel is a self-hosted runtime. It is deployable as separate API,
worker, Web, Postgres, Redis, and object-storage components, but it is not a
fully managed cloud platform.

The versioned environment-variable contract lives in
[Versioned Configuration Reference](configuration.md). This file focuses on
deployment expectations and operational guidance.

## Runtime Processes

Agent Kernel has these production-facing processes:

```text
API      - FastAPI service for state, inspection, and control APIs
Worker   - background queued-run executor
Web      - Next.js Agent Workbench
Postgres - relational runtime state and pgvector-ready storage
Redis    - optional scheduling hints and shared workspace admission limits
Objects  - document upload and parsed artifact storage
```

Run API and Worker as separate processes. New runs execute in the Worker.
Approval `POST /v1/runs/{id}/resume` currently executes one bounded continuation
segment synchronously in the API and returns at completion/failure/next approval.
Set proxy/client timeouts above the configured active-time bound (default 300s);
`agent-kernel run resume --timeout-seconds 330` is the CLI default. A transport
timeout is not evidence of execution failure: inspect Run/tool state before
another action. Background queued resume is not implemented by this change.
PostgreSQL remains the source of truth; Redis hints are not execution ownership
or completion acknowledgments. See [backend operations](backend-operations.md).

## Environment Variables

Use [Versioned Configuration Reference](configuration.md) as the source of
truth for defaults, stability level, secret status, and change-control rules.

Recommended production baseline:

Core runtime:

```bash
AGENT_KERNEL_ENV=production
AGENT_KERNEL_LOG_LEVEL=info
AGENT_KERNEL_API_KEY_AUTH_ENABLED=true
DATABASE_URL=postgresql+psycopg://user:password@postgres:5432/agent_kernel
REDIS_URL=redis://redis:6379/0
AGENT_KERNEL_OBJECT_STORE_BACKEND=s3
AGENT_KERNEL_OBJECT_STORE_ROOT=/data/objects
AGENT_KERNEL_S3_BUCKET=agent-kernel
AGENT_KERNEL_S3_PREFIX=prod
AGENT_KERNEL_S3_ENDPOINT_URL=
AGENT_KERNEL_S3_REGION=us-east-1
AGENT_KERNEL_VECTOR_STORE=auto
AGENT_KERNEL_EMBEDDING_PROVIDER=mock
AGENT_KERNEL_OTEL_ENABLED=true
AGENT_KERNEL_OTEL_SERVICE_NAME=agent-kernel
AGENT_KERNEL_OTEL_EXPORTER=otlp-http
AGENT_KERNEL_OTEL_ENDPOINT=http://otel-collector:4318
```

Web:

```bash
NEXT_PUBLIC_AGENT_KERNEL_API_URL=https://agent-kernel.example.com
```

Optional OpenAI embeddings (explicitly opt in instead of the mock baseline):

```bash
OPENAI_API_KEY=
AGENT_KERNEL_EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536
```

Use `mock:*` and `replay:*` providers for deterministic local and CI workflows.
Use `openai:*` models only when `OPENAI_API_KEY` is configured.
`AGENT_KERNEL_EMBEDDING_PROVIDER=mock` is the default RAG path. Set
`AGENT_KERNEL_EMBEDDING_PROVIDER=openai` to select `OpenAIEmbeddingProvider` for
API indexing, retrieval, and API/Worker `kb_search`. An `OPENAI_API_KEY` alone
never enables paid embeddings. Keep the selection identical across API and
Worker processes. Unknown providers or missing/malformed OpenAI embedding
credentials fail configuration rather than silently falling back to mock.

## Storage

Recommended production storage:

```text
Postgres + pgvector image
```

Backup and restore expectations for Postgres, SQLite local development, local
object storage, and S3/MinIO-compatible object storage are defined in
[Backup and Restore Guide](backup-restore.md).

SQLite is supported for local development only. Do not use SQLite as the primary
multi-user production database.

Object storage is selected with:

```bash
AGENT_KERNEL_OBJECT_STORE_BACKEND=local
AGENT_KERNEL_OBJECT_STORE_BACKEND=s3
```

Local object storage is controlled by:

```bash
AGENT_KERNEL_OBJECT_STORE_ROOT=/data/objects
```

Mount this path as durable storage when using the local backend.

S3/MinIO-compatible storage is controlled by:

```bash
AGENT_KERNEL_S3_BUCKET=agent-kernel
AGENT_KERNEL_S3_PREFIX=prod
AGENT_KERNEL_S3_ENDPOINT_URL=https://minio.example.com
AGENT_KERNEL_S3_REGION=us-east-1
```

Leave `AGENT_KERNEL_S3_ENDPOINT_URL` empty for AWS S3. Set it for MinIO or
another S3-compatible service. Production deployments should provide standard
AWS-compatible credentials through platform secrets, such as
`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.

The S3 backend uses `s3://bucket/key` URIs and stores document artifacts with
sha256 metadata. Application images that enable `AGENT_KERNEL_OBJECT_STORE_BACKEND=s3`
must include `boto3` or inject an S3-compatible client.

Embedding storage:

- Mock embeddings remain suitable for local development, CI, and deterministic
  evals.
- OpenAI embeddings require `AGENT_KERNEL_EMBEDDING_PROVIDER=openai` and valid
  `OPENAI_API_KEY` credentials.
- Keep the same embedding provider and model for indexing and retrieval.
- Store `OPENAI_API_KEY` as a secret.
- `OPENAI_EMBEDDING_MODEL` and `OPENAI_EMBEDDING_DIMENSIONS` should be pinned
  per environment so retrieval quality does not drift accidentally.
- `AGENT_KERNEL_VECTOR_STORE=auto` uses pgvector on PostgreSQL and JSON-vector
  fallback on SQLite.
- `AGENT_KERNEL_VECTOR_STORE=json` forces portable JSON-vector similarity.
- `AGENT_KERNEL_VECTOR_STORE=pgvector` requires PostgreSQL and the
  `0013_pgvector_embeddings` migration.
- JSON vectors remain stored for compatibility; pgvector uses the
  `chunk_embeddings.vector_pg` column and cosine HNSW index for PostgreSQL
  similarity search.
- The default pgvector index targets 1536-dimensional vectors, matching the
  default `text-embedding-3-small` configuration. If you choose a different
  embedding dimension in production, add a matching pgvector expression index
  before treating that path as performance-ready.

## OpenTelemetry

OpenTelemetry trace exporter setup is controlled by:

```bash
AGENT_KERNEL_OTEL_ENABLED=true
AGENT_KERNEL_OTEL_SERVICE_NAME=agent-kernel-api
AGENT_KERNEL_OTEL_EXPORTER=otlp-http
AGENT_KERNEL_OTEL_ENDPOINT=http://otel-collector:4318
AGENT_KERNEL_OTEL_TRACES_ENDPOINT=
```

Supported exporters:

- `otlp-http`: sends spans to an OTLP/HTTP collector. If
  `AGENT_KERNEL_OTEL_TRACES_ENDPOINT` is empty, Agent Kernel appends
  `/v1/traces` to `AGENT_KERNEL_OTEL_ENDPOINT`.
- `console`: writes spans to stdout for local inspection.

OpenTelemetry is disabled by default. Production images that enable it must
include `opentelemetry-sdk` and `opentelemetry-exporter-otlp-proto-http`.
The API and worker both call the shared configuration helper at startup. The
helper is idempotent, so repeated app creation in tests and local reload flows
does not attach duplicate span processors.

## Database Migrations

Upgrade sequencing, migration compatibility rules, and release-blocking
migration checks are defined in
[Upgrade and Migration Policy](upgrade-migration-policy.md).

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

Prometheus scrape endpoint:

```http
GET /metrics
```

`/metrics` returns Prometheus text exposition format. It is exempt from workspace
API-key middleware, but has its own conditional monitoring authentication:

| API-key auth | `AGENT_KERNEL_MONITORING_TOKEN` | API `/metrics` access |
| --- | --- | --- |
| Disabled | Unset/empty | No application authentication; trusted local use only. |
| Disabled | Configured | Matching monitoring token required; otherwise HTTP 401. |
| Enabled | Unset/empty | HTTP 401 for every scrape (fails closed). |
| Enabled | Configured | Matching monitoring token required; otherwise HTTP 401. |

Send `Authorization: Bearer <monitoring-token>`. The monitoring token is a
separate deployment secret, not a workspace API key; ordinary workspace keys
do not grant metrics access. Inject `AGENT_KERNEL_MONITORING_TOKEN` through the
deployment secret store and use at least 32 random ASCII characters. The Worker
listener enforces that minimum for configured tokens; the API does not enforce
the same length check.

Keep scraping on a private network even with token authentication. API metrics
include process counters and deployment-wide durable gauges across all
workspaces; they are not tenant APIs. `/healthz` and sanitized dependency
`/readyz` probes remain exempt from authentication. A failed required readiness
dependency returns HTTP 503. See [Observability Operations](observability-operations.md)
for readiness and scrape configuration.

## Worker

Recommended worker command:

```bash
agent-kernel-worker --loop --limit 25 --poll-interval 2
```

Run at least one worker process for queued agent execution.

### Worker Metrics

The independent Worker HTTP listener is opt-in. Defaults:

```bash
AGENT_KERNEL_WORKER_METRICS_ENABLED=false
AGENT_KERNEL_WORKER_METRICS_HOST=127.0.0.1
AGENT_KERNEL_WORKER_METRICS_PORT=9001
```

Set `AGENT_KERNEL_WORKER_METRICS_ENABLED=true` to serve `GET /metrics`.
A non-loopback bind requires `AGENT_KERNEL_MONITORING_TOKEN`; a configured token
must contain at least 32 ASCII characters and cannot be all whitespace.
Scrapes then require `Authorization: Bearer <monitoring-token>`, including on
loopback. A loopback listener without a token permits unauthenticated scraping.
Do not publish this port on public ingress. The listener starts once per Worker
process and closes on shutdown.

Worker execution, model/tool, and retrieval metrics are process-local. API
scrapes do not include Worker process counters. Scrape every API and Worker
instance directly; counters reset on restart. See
[Observability Operations](observability-operations.md) for the metric inventory
and the optional monitoring overlay.

### Execution Ownership

Every execution/resume acquires a database lease with a heartbeat and stale-owner
write fencing. Workers poll persisted queued runs on every pass; optional Redis
hints are enabled with `AGENT_KERNEL_RUN_QUEUE_BACKEND=redis`. The default
`database` mode does not require Redis for scheduling.

Compose supervises the Worker with `restart: unless-stopped`. A failed process
can recover when a database outage ends; an explicit operator stop remains
stopped. Use equivalent supervision on other platforms. Process restart does
not retry uncertain in-flight operations. Inspect leases and use explicit
stuck-run recovery when appropriate:

```bash
agent-kernel-worker --recover-stuck --limit 100
```

Recovery marks expired `running` or `resuming` runs as failed instead of
automatically requeueing them. This avoids blindly repeating side effects.
Redis mode uses the default hint list `agent-kernel:runs:queued`. API enqueue
failure leaves the committed database run available, and Worker database polling
continues if Redis is unavailable. Shared admission limits, when configured,
instead fail closed with HTTP 503 during Redis failure. These deliberately
different semantics are described in [backend operations](backend-operations.md).

Durable retry and restart visibility:

- Provider retry and fallback events are persisted in run timelines.
- Safe tool retry events are persisted in run timelines.
- Regression coverage verifies retry events remain visible after reopening a
  database session.
- Regression coverage verifies a restarted worker does not re-execute a run
  failed by stuck-run recovery.
- Regression coverage verifies the real worker CLI can execute queued runs once
  and recover expired in-flight leases.
- The completed worker leasing, recovery, retry visibility, queue adapter, and
  operator command scope is summarized in
  [Execution Ownership and Recovery](execution-ownership.md); the
  [Durable Execution Summary](durable-execution-summary.md) is historical scope.
- Eligible in-process provider/read-only tool retries use capped exponential
  backoff with full jitter (base 0.25s, cap 30s), honor safe `Retry-After`, and
  retain lease heartbeats/cancellation while waiting. Oversized hints fail closed.
  Approved/write tools do not auto-retry. Public manual retry APIs and persisted
  delayed scheduling remain separate work.
- Unreleased native execution supports bounded rounds, serial tool batches and
  persisted approval continuation. Apply migration `0019_execution_checkpoint`
  and the [trusted execution limits](configuration.md#native-execution-bounds-unreleased)
  consistently to every executor. This does not permit automatic replay of
  uncertain in-flight effects. Verification status remains in
  [N1-N5](capability-hardening-plan.md#active-follow-up-bounded-agent-execution).

## Web

Recommended Web command after build:

```bash
npm --workspace apps/web exec -- next start --hostname 0.0.0.0
```

The Web Workbench is an operator console. Core run, approval, knowledge, eval,
health, and retrieval workflows have live same-origin backend routes. Some
dashboard summaries, agent catalog summaries, document detail views, memory
detail views, and admin settings remain preview-backed rather than stable
automation contracts.

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
- `AGENT_KERNEL_MONITORING_TOKEN`
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` when using S3/MinIO
- Plaintext Agent Kernel API keys returned during creation

## API Authentication

API key authentication can be enabled with:

```text
AGENT_KERNEL_API_KEY_AUTH_ENABLED=true
```

When enabled:

- `/healthz` and `/readyz` remain public probe endpoints.
- `/metrics` uses the separate monitoring-token check described above, not
  workspace API-key authorization.
- API keys can be supplied with `Authorization: Bearer <key>`.
- API keys can also be supplied with `X-Agent-Kernel-Api-Key`.
- Missing, invalid, revoked, expired, or disabled-principal API keys are
  rejected with `401 Unauthorized`.
- Valid API keys load the principal, key, and workspace memberships into the
  request auth context.
- Existing `/v1/*` routes enforce route-level permissions and return
  `403 Forbidden` when the authenticated role lacks the required permission.
- Eval report persistence routes use `eval:read` and `eval:write` permissions.

Local quickstart flows keep API key authentication disabled by default. Route
permission checks currently use the authenticated API key's workspace as the
request workspace, not a workspace selector in user or model input.

Current object-level workspace scoping:

- Agents are created and read within the authenticated API key workspace.
- Runs are created and read within the authenticated API key workspace.
- Approval list, detail, approve, reject, and resume approval prechecks are
  scoped through the related run workspace.
- Knowledge bases store workspace ownership; documents, chunks, embeddings,
  and ingestion jobs derive scope through their knowledge base. `kb_search`
  uses the persisted Run workspace, including Worker and approval-resume paths.
- Memory and eval records store workspace ownership. Memory business `scope`
  strings are not authorization; source runs must belong to the same workspace.
- Tool calls and run events derive scope through their Run. `/v1/usage` and
  `/v1/usage/breakdown` require `run:read` and filter by authenticated workspace.
- Foreign resource IDs return HTTP 404; missing role permissions return HTTP 403.
- Legacy NULL-owned knowledge, memory, and eval records are hidden from
  authenticated workspaces. `workspace_id=None` is trusted local/operator
  access, not a tenant boundary. Never share an auth-disabled API across tenants.
- Process metrics and deployment-wide gauges are monitoring-only; logs/traces
  require deployment-level access controls, not workspace API permissions.

See [Auth and RBAC](auth-rbac.md) for the full role, permission, object-scope,
and security test matrix.

## Evals

Persisted eval reports are available through:

```http
POST /v1/evals/runs
GET /v1/evals/runs
GET /v1/evals/runs/{eval_run_id}
```

The API stores submitted report JSON plus summary counts, status, metadata,
trace ID, and timestamps. Run deterministic local evals with:

```bash
agent-kernel eval report evals/rag-smoke.json --publish
```

Deterministic, credential-free release-blocking gates already run locally and
in the Python CI `Release Eval Gates` step:

```bash
make release-eval
```

That target runs:

```bash
uv run agent-kernel eval report evals/rag-smoke.json
uv run agent-kernel eval report evals/release-rag-gate.json
uv run pytest tests/unit/test_tool_call_evals.py
uv run python scripts/timeline_regression.py
```

The Python CI `Test` step additionally runs actual-adapter HTTP mock contracts
and timeline mutation tests:

```bash
uv run pytest tests/unit/test_openai_provider.py tests/integration/test_openai_runtime_contract.py
uv run pytest tests/integration/test_timeline_regression.py
```

`make release-eval` alone does not establish that those additional tests passed.
See [Release Eval Gates](release-eval-gates.md) for the blocking contract and
[Behavior Regression](behavior-regression.md) for coverage and limits. Live
provider evals and LLM-as-judge remain optional, not default release gates.
Server-side dataset upload, arbitrary eval execution, and eval job queues are
not provided by the eval report persistence API.

## Networking

Expose only the API and Web services publicly.

Recommended defaults:

```text
API: 8000 behind HTTPS reverse proxy
Web: 3000 behind HTTPS reverse proxy
Postgres: private network only
Redis: private network only
Worker metrics: private network only, opt-in port 9001
Object store path: private mounted storage only
```

## Observability

Agent Kernel includes trace IDs, structured logs, metrics recorders,
OpenTelemetry exporter configuration, Prometheus-compatible API/Worker metrics, and
persisted deterministic eval reports.

Recommended production log format:

```text
JSON logs with trace_id, run_id, agent_id, operation, status, latency, tokens, cost
```

OpenTelemetry trace exporter setup is available through the environment
variables above. Both processes use a bounded `AggregatingMetricsRecorder`;
duration histograms are exported in seconds. Scrape each API instance and each
enabled Worker listener. Aggregate process counters with `sum(rate(...))`;
API-only durable gauges describe the shared database and use `max`, never
`sum`, across replicas sharing that database. These metrics are not a billing
ledger. See [Observability Operations](observability-operations.md).

## Security Posture

Release-level security gates and operator checks are defined in
[Security Hardening Checklist](security-hardening.md).

Current safety controls:

- Tool risk levels.
- Policy decisions.
- Human approval records.
- Approval interrupt/resume.
- Audit timeline for tool calls and decisions.
- Sensitive structured-log field redaction.
- API-key authentication.
- Role-based route authorization.
- Workspace-scoped agents, runs, approvals, knowledge, memory, evals, and
  Run-derived tool calls, events, and usage APIs.
- Separate monitoring-token authorization for protected metrics endpoints.

Not production-complete yet:

- End-user browser login.
- Public hosted SaaS tenant isolation.
- Browser session management.
- Remote sandbox execution.
- Built-in managed secrets provisioning; secret injection remains
  deployment-specific.

The implemented workspace boundaries do not certify hostile hosted-tenant
isolation or replace ongoing object-scope regression review.

Do not deploy Agent Kernel as a public multi-tenant service without adding
end-user authentication, hosted-tenant isolation, network controls, and managed
secret storage.

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
- Run `make release-eval` and the provider wire/timeline mutation tests above.
- Run `docker compose up --build` from a clean checkout.
- Verify `/healthz`.
- Verify `/readyz` and protected API/Worker metrics scraping.
- Verify migrations from an empty Postgres volume.
- Verify worker can process a queued mock run.
- Verify object storage path persists uploaded documents.
- Verify Web Workbench starts.
- Review `npm audit`.
- Review Python dependency advisories.
- Confirm secrets are injected, not committed.
- Confirm public network exposure is limited to API/Web.
