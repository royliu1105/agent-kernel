# Versioned Configuration Reference

The unreleased [memory context contract](specs/memory-context-safety.md) adds
fixed admission limits (16 KiB content, 4 KiB metadata, 8 scopes, 20 recalled
items, 64 KiB context). These are not environment variables or Run-overridable
budgets. Existing execution budgets still apply independently.

## Post-v1.0 Hardening Additions

These additions are unreleased; apply the migration and compatibility guidance
in [Upgrade Policy](upgrade-migration-policy.md). The Python/TypeScript stack
is unchanged. Storage now requires PostgreSQL, including local tests; mock models
remain the default. See [PostgreSQL-only compatibility](postgresql-only.md).

| Variable | Default | Contract |
| --- | --- | --- |
| `AGENT_KERNEL_RUN_QUEUE_BACKEND` | `database` | Optional `redis` UUID hint queue; database remains authoritative. |
| `AGENT_KERNEL_RUN_QUEUE_NAME` | `agent-kernel:runs:queued` | Deployment-specific Redis list. |
| `AGENT_KERNEL_RUN_QUEUE_MAX_LENGTH` | `10000` | Atomic hint capacity; overflow never loses a committed Run. |
| `AGENT_KERNEL_REDIS_TIMEOUT_SECONDS` | `1` | Bounded socket operation timeout, seconds. |
| `AGENT_KERNEL_REDIS_CONNECT_TIMEOUT_SECONDS` | `1` | Bounded connect timeout, seconds. |
| `AGENT_KERNEL_REDIS_MAX_CONNECTIONS` | `20` | Redis pool limit. |
| `AGENT_KERNEL_RATE_LIMIT_REQUESTS` | `0` | Zero disables; positive enables shared per-workspace admission. Requires auth and Redis. |
| `AGENT_KERNEL_RATE_LIMIT_PRINCIPAL_REQUESTS` | `0` | Shared per-principal quota within each workspace, across that principal's keys. |
| `AGENT_KERNEL_RATE_LIMIT_API_KEY_REQUESTS` | `0` | Shared per-API-key quota within each workspace. All enabled quotas are charged atomically. |
| `AGENT_KERNEL_RATE_LIMIT_WINDOW_SECONDS` | `60` | Fixed window from first admission, 1..86400 seconds. |
| `AGENT_KERNEL_RATE_LIMIT_PREFIX` | `agent-kernel:rate-limit` | Shared policy namespace across replicas. |
| `AGENT_KERNEL_MONITORING_TOKEN` | empty | Secret, separate from workspace keys; required for authenticated API metrics and non-loopback Worker metrics. Use at least 32 random ASCII characters. |
| `AGENT_KERNEL_WORKER_METRICS_ENABLED` | `false` | Enable independent Worker metrics HTTP listener. |
| `AGENT_KERNEL_WORKER_METRICS_HOST` | `127.0.0.1` | Private bind address; do not publish on the public ingress. |
| `AGENT_KERNEL_WORKER_METRICS_PORT` | `9001` | Metrics listener port. |
| `AGENT_KERNEL_READINESS_REDIS` | inferred | `disabled`, `optional`, `required`; shared limiter forces required. |
| `AGENT_KERNEL_READINESS_S3` | inferred | Selected S3 backend must be required; otherwise disabled. |
| `AGENT_KERNEL_EXTERNAL_TOOLS_CONFIG` | empty | Trusted local JSON path; empty means no external tools. Not a user-uploaded config. |

Redis connection uses the existing `REDIS_URL`. Queue failure falls back to DB
polling; enabled shared limiting fails closed with 503. Readiness returns 503
when a required backend fails and sanitized degraded status for optional
dependencies. `/healthz` only reports process liveness.

See [backend operations](backend-operations.md),
[execution ownership](execution-ownership.md) and
[behavior regression](behavior-regression.md) for real-backend and opt-in live
smoke test settings. `AGENT_KERNEL_TEST_*` variables are test-only and must not
point at production services. Live smoke is disabled by default and never reads
credentials from the Web browser. Deployment secrets must not be committed.

This document defines the Agent Kernel v1.0 release candidate configuration
contract.

## Observability Backend Additions (Unreleased)

These are optional settings for the [backend/SMTP profile](observability-backends.md),
not part of the published tag. Acceptance is tracked in the
[completion ledger](observability-completion-plan.md).

| Variable | Default | Contract |
| --- | --- | --- |
| `AGENT_KERNEL_LOG_FILE` | empty | Optional absolute sanitized JSON file path; one writer per path, 0600 files. |
| `AGENT_KERNEL_LOG_MAX_BYTES` | `10485760` | Rotation threshold, 1024..104857600 bytes. |
| `AGENT_KERNEL_LOG_BACKUP_COUNT` | `5` | Retained rotated files, 1..20; zero/unbounded mode rejected. |
| `AGENT_KERNEL_ALERTMANAGER_CONFIG_FILE` | required by full overlay | Trusted private SMTP configuration path; no recipient inferred by the app. |
| `AGENT_KERNEL_SMTP_PASSWORD_FILE` | required by full overlay | Secret file for SMTP; empty only in explicit local Mailpit mode. |
| `AGENT_KERNEL_GRAFANA_PORT` / `AGENT_KERNEL_PROMETHEUS_PORT` | `3090` / `9090` | Loopback-only host mappings. |
| `AGENT_KERNEL_LOKI_PORT` / `AGENT_KERNEL_TEMPO_PORT` | `3100` / `3200` | Trusted local diagnostic APIs; no built-in auth in this profile. |
| `AGENT_KERNEL_OTLP_PORT` | `4318` | Alloy receiver loopback mapping; application containers use `alloy:4318`. |
| `AGENT_KERNEL_ALERTMANAGER_PORT` / `AGENT_KERNEL_MAILPIT_PORT` | `9093` / `8025` | Operator UI / local test inbox loopback mappings. |

The Docker build argument `INSTALL_OBSERVABILITY=true` installs the locked
`observability` extra without developer tools. It is enabled by the full overlay.
The SMTP JSON fields are Alertmanager configuration, not application environment
variables; ordinary environment substitution does not rewrite that JSON file.

## Native Execution Bounds (Unreleased)

Set these trusted server variables consistently on API, CLI and Worker. Run
input cannot override them. Checkpoints retain the original bounds; resume
applies the stricter of saved/current settings. Invalid values fail validation.

| Variable | Default | Bound |
| --- | --- | --- |
| `AGENT_KERNEL_MAX_MODEL_CALLS` | `8` | Physical attempts across rounds, retries and initial fallback; 1..256. |
| `AGENT_KERNEL_MAX_TOOL_CALLS` | `16` | Physical tool attempts across all batches/retries/resumes; 0..1024. |
| `AGENT_KERNEL_MAX_ACTIVE_SECONDS` | `300` | Active wall time including retry sleep, excluding human approval wait; >0..86400. |
| `AGENT_KERNEL_MAX_HISTORY_BYTES` | `1048576` | Serialized private checkpoint bytes, including model history/results; 64..16777216. |
| `AGENT_KERNEL_MAX_TOTAL_TOKENS` | `64000` | Observed cumulative input + output tokens; 1..64000000. |
| `AGENT_KERNEL_MAX_OUTPUT_TOKENS` | `4096` | Per-request output cap, further limited by remaining token allowance; 1..1000000. |
| `AGENT_KERNEL_MAX_ESTIMATED_COST` | empty | Optional positive finite provider-reported cost ceiling. |

Token/cost limits stop further work once reported usage reaches the threshold;
they cannot predict unreported billing or guarantee a hard monetary cap. A
response may cross a threshold, which fails the run before further tools/models.
The built-in OpenAI adapter currently reports `estimated_cost=0`; this setting
therefore does not enforce actual OpenAI spending. Use call/token/time limits
and provider-side budgets; a priced adapter is required for nonzero cost checks.
The history limit rejects oversized state, it does not summarize/truncate it.
Timeout/cancellation is cooperative; arbitrary in-process code is not a sandbox.

`RetryDelayPolicy` is a trusted Python configuration (default base 0.25s, cap
30s, full jitter), not a run-input API. Valid `Retry-After` is a minimum delay;
a hint above the cap fails closed instead of retrying earlier. There is no
persisted delayed scheduler or automatic restart of uncertain in-flight writes.
See [bounded execution](specs/bounded-native-execution.md) for acceptance status.

The configuration contract version is:

```text
v1.0-rc
```

This is a documentation and release contract. Agent Kernel does not require a
runtime `CONFIG_VERSION` environment variable.

## Compatibility Rules

Stable configuration variables:

- Must keep their names and documented meanings throughout v1.x.
- May gain new accepted values only when the default behavior remains
  compatible.
- May gain stricter validation only when invalid values previously led to
  unsafe or undefined behavior.
- Must be listed in this document before v1.0.
- Must be listed in release notes when defaults, requiredness, or accepted
  values change.

Preview configuration variables:

- Are available for operator feedback.
- May change before or after v1.0.
- Must be clearly marked preview in this document.

Internal configuration variables:

- Are used by framework, build, or local tooling.
- Do not have public compatibility guarantees.
- Should not be used as public extension points.

Secret handling:

- Never commit real secret values.
- Prefer platform secrets over checked-in `.env` files.
- Rotate credentials if they appear in logs, screenshots, issue reports, or
  support bundles.

## Stable Core Runtime Variables

| Variable | Components | Default | Production | Secret | Notes |
| --- | --- | --- | --- | --- | --- |
| `AGENT_KERNEL_ENV` | API, worker | `development` | `production` | No | Environment label used for deployment posture and operator diagnostics. |
| `AGENT_KERNEL_LOG_LEVEL` | API, worker | `info` | `info` | No | Logging verbosity. Use `debug` only in controlled environments. |
| `DATABASE_URL` | API, worker, migrations | Required; Docker supplies it | Required PostgreSQL URL | Yes | PostgreSQL with sync psycopg only. No implicit filesystem database or fallback. |
| `REDIS_URL` | API, worker | `redis://localhost:6379/0` in examples | Recommended when Redis has credentials | Sometimes | Redis is a coordination dependency. The default worker path remains database-first. |

Production database guidance:

- Use PostgreSQL for production.
- Use the pgvector image or install the `vector` extension before enabling the
  pgvector vector store path.
- Run Alembic migrations before starting API and worker.
- Keep tests on the dedicated disposable PostgreSQL service, never the runtime DB.

## Stable Object Storage Variables

| Variable | Components | Default | Production | Secret | Notes |
| --- | --- | --- | --- | --- | --- |
| `AGENT_KERNEL_OBJECT_STORE_BACKEND` | API, worker | `local` | `s3` or durable `local` mount | No | Accepted values: `local`, `s3`. |
| `AGENT_KERNEL_OBJECT_STORE_ROOT` | API, worker | `.agent-kernel/objects` | Durable mounted path | No | Used only by the local object store backend. |
| `AGENT_KERNEL_S3_BUCKET` | API, worker | Empty | Required for `s3` backend | No | S3 or MinIO-compatible bucket name. |
| `AGENT_KERNEL_S3_PREFIX` | API, worker | Empty | Optional environment prefix | No | Prefixes stored object keys. |
| `AGENT_KERNEL_S3_ENDPOINT_URL` | API, worker | Empty | Required for MinIO-compatible endpoints | No | Leave empty for AWS S3 default endpoint resolution. |
| `AGENT_KERNEL_S3_REGION` | API, worker | Empty | Recommended | No | Passed to the S3-compatible client. |

S3-compatible backends also rely on standard AWS-style credentials from the
runtime environment, such as:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN
```

These credential variables are secrets. They are not Agent Kernel-specific, but
production deployments using `AGENT_KERNEL_OBJECT_STORE_BACKEND=s3` must manage
them through platform secret storage.

## Stable Vector and Embedding Variables

| Variable | Components | Default | Production | Secret | Notes |
| --- | --- | --- | --- | --- | --- |
| `AGENT_KERNEL_VECTOR_STORE` | API, worker | `auto` | `auto` or `pgvector` | No | Accepted values: `auto`, `json`, `pgvector`. |
| `AGENT_KERNEL_EMBEDDING_PROVIDER` | API, worker | `mock` | Explicit `openai` for real embeddings | No | Same selection for indexing, retrieval and `kb_search`; an API key alone never enables paid embeddings. |
| `OPENAI_API_KEY` | API, worker, CLI workflows | Empty | Required for `openai:*` models or OpenAI embeddings | Yes | Mock and replay providers do not require this. |
| `OPENAI_EMBEDDING_MODEL` | API, worker | `text-embedding-3-small` | Pin per environment | No | Keep indexing and retrieval on the same model. |
| `OPENAI_EMBEDDING_DIMENSIONS` | API, worker | `1536` | Pin per environment | No | Must match the embedding model and pgvector index strategy. |

Vector store behavior:

- `auto` uses native pgvector; there is no database-dialect fallback.
- `json` forces portable JSON-vector similarity.
- `pgvector` requires PostgreSQL and the pgvector migration.

If `OPENAI_EMBEDDING_DIMENSIONS` changes from `1536`, add and validate a
matching pgvector expression index before treating the path as
performance-ready.

## Stable Observability Variables

| Variable | Components | Default | Production | Secret | Notes |
| --- | --- | --- | --- | --- | --- |
| `AGENT_KERNEL_OTEL_ENABLED` | API, worker | `false` | `true` when exporting traces | No | Boolean values accept common true/false spellings. |
| `AGENT_KERNEL_OTEL_SERVICE_NAME` | API, worker | `agent-kernel` | Per process, such as `agent-kernel-api` | No | Used as OpenTelemetry `service.name`. |
| `AGENT_KERNEL_OTEL_EXPORTER` | API, worker | `otlp-http` | `otlp-http` | No | Accepted values: `otlp-http`, `console`. |
| `AGENT_KERNEL_OTEL_ENDPOINT` | API, worker | `http://localhost:4318` | Collector base URL | Sometimes | May contain collector credentials depending on deployment. |
| `AGENT_KERNEL_OTEL_TRACES_ENDPOINT` | API, worker | Empty | Optional explicit traces URL | Sometimes | Overrides `AGENT_KERNEL_OTEL_ENDPOINT` for traces. |

Metrics:

- `/metrics` is configured by the API process and does not require a separate
  Agent Kernel environment variable.
- Keep `/metrics` private or protect it with upstream network controls.

## Stable Auth Variables

| Variable | Components | Default | Production | Secret | Notes |
| --- | --- | --- | --- | --- | --- |
| `AGENT_KERNEL_API_KEY_AUTH_ENABLED` | API | `false` | `true` | No | Enables API-key authentication middleware for `/v1/*` routes. |

API keys themselves are secrets. Agent Kernel accepts them through:

```http
Authorization: Bearer <key>
X-Agent-Kernel-Api-Key: <key>
```

The header names are part of the public API contract. Plaintext API keys
returned during creation must be stored by the operator; Agent Kernel stores
only hashes.

## Stable Client and Web Variables

| Variable | Components | Default | Production | Secret | Notes |
| --- | --- | --- | --- | --- | --- |
| `AGENT_KERNEL_API_HOST` | API | `0.0.0.0` | Bind host for the API process | No | Use `127.0.0.1` for local-only binding. |
| `AGENT_KERNEL_API_PORT` | API | `8000` | Bind port for the API process | No | Use another port when `8000` is occupied during rehearsal. |
| `AGENT_KERNEL_WEB_PORT` | Docker Compose | `3000` | Published Web host port | No | Does not change the Web container port. Use another port when `3000` is occupied. |
| `AGENT_KERNEL_POSTGRES_PORT` | Docker Compose | `5432` | Published Postgres host port | No | Does not change the internal Postgres service port used by API and worker. |
| `AGENT_KERNEL_REDIS_PORT` | Docker Compose | `6379` | Published Redis host port | No | Does not change the internal Redis service port used by API and worker. |
| `AGENT_KERNEL_API_URL` | CLI, Web server routes | `http://127.0.0.1:8000` | Internal API URL | Sometimes | Used by CLI and same-origin Web proxy routes. |
| `AGENT_KERNEL_API_KEY` | CLI only | Empty | A scoped API key | When API auth is enabled | Sent as a Bearer header for JSON and file uploads; not a workspace override. Not forwarded by Web. Use HTTPS outside localhost. |
| `NEXT_PUBLIC_AGENT_KERNEL_API_URL` | Web browser and Web server routes | `http://127.0.0.1:8000` | Public API URL or same-origin gateway | No | Exposed to browser bundles by Next.js. Do not put secrets here. |

Web route preference:

- Same-origin Web proxy routes prefer `AGENT_KERNEL_API_URL` when present.
- Browser-facing code can read `NEXT_PUBLIC_AGENT_KERNEL_API_URL`.
- Do not put credentials, API keys, or private network secrets in
  `NEXT_PUBLIC_*` variables.

## Stable Process Defaults

API:

```bash
agent-kernel-api
```

The API binds to `AGENT_KERNEL_API_HOST` and `AGENT_KERNEL_API_PORT`.

Worker:

```bash
agent-kernel-worker --loop --limit 25 --poll-interval 2
```

Web:

```bash
npm --workspace apps/web exec -- next start --hostname 0.0.0.0
```

Docker Compose publishes Web, Postgres, and Redis to
`AGENT_KERNEL_WEB_PORT`, `AGENT_KERNEL_POSTGRES_PORT`, and
`AGENT_KERNEL_REDIS_PORT`. These variables affect host port bindings only; the
service-to-service container network still uses ports `3000`, `5432`, and
`6379`.

Migrations:

```bash
uv run alembic upgrade head
```

## Preview Configuration Surfaces

These surfaces are available but not frozen as v1.x public configuration
contracts:

- Redis-first worker scheduling. `RedisRunQueue` exists, but the default worker
  path remains database-first.
- OpenTelemetry SDK installation strategy. The environment variables are
  stable, but packaging optional SDK dependencies remains deployment-specific.
- Web Workbench feature flags, if added later.
- Provider-specific base URLs beyond currently documented OpenAI defaults.

## Internal or Tooling Variables

These variables may appear in Dockerfiles, Node.js tooling, or framework
generated output. They are not Agent Kernel public configuration contracts:

| Variable | Owner | Notes |
| --- | --- | --- |
| `PYTHONUNBUFFERED` | Python runtime | Container runtime hygiene. |
| `UV_COMPILE_BYTECODE` | uv/Docker build | Build/runtime optimization. |
| `NODE_ENV` | Next.js/Node.js | Framework runtime mode. |
| `NEXT_TELEMETRY_DISABLED` | Next.js | Disables Next.js telemetry. |
| `NO_COLOR` / `FORCE_COLOR` | CLI/test tooling | Output formatting only. |

## Deferred Configuration

These are intentionally not part of the current configuration contract:

- Tenant-domain routing configuration for hosted SaaS.
- Browser automation credentials.
- External workflow engine settings such as Temporal.
- Release-blocking eval scheduler configuration.
- Backup retention policy variables.
- Encryption key hierarchy and KMS configuration.

Deferred items may become stable only after a later design and release
candidate review.

## Configuration Change Checklist

When adding or changing configuration:

1. Update `.env.example`.
2. Update this document.
3. Update `docs/production-config.md` if deployment guidance changes.
4. Add validation tests when accepted values or defaults matter.
5. Mark the variable as stable, preview, internal, or deferred.
6. Mention default or requiredness changes in release notes.

Do not add new public environment variables silently. Configuration is part of
the v1.0 operator contract.
