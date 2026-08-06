# Versioned Configuration Reference

This document defines the Agent Kernel v1.0 release candidate configuration
contract.

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
| `DATABASE_URL` | API, worker, migrations | `sqlite:///./.agent-kernel/agent_kernel.db` | Required Postgres URL | Yes | Postgres is the production database. SQLite is for local development and tests. |
| `REDIS_URL` | API, worker | `redis://localhost:6379/0` in examples | Recommended when Redis has credentials | Sometimes | Redis is a coordination dependency. The default worker path remains database-first. |

Production database guidance:

- Use PostgreSQL for production.
- Use the pgvector image or install the `vector` extension before enabling the
  pgvector vector store path.
- Run Alembic migrations before starting API and worker.
- Keep SQLite for local quickstart, tests, and single-user development only.

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
| `OPENAI_API_KEY` | API, worker, CLI workflows | Empty | Required for `openai:*` models or OpenAI embeddings | Yes | Mock and replay providers do not require this. |
| `OPENAI_EMBEDDING_MODEL` | API, worker | `text-embedding-3-small` | Pin per environment | No | Keep indexing and retrieval on the same model. |
| `OPENAI_EMBEDDING_DIMENSIONS` | API, worker | `1536` | Pin per environment | No | Must match the embedding model and pgvector index strategy. |

Vector store behavior:

- `auto` uses pgvector on PostgreSQL and JSON-vector fallback on SQLite.
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
