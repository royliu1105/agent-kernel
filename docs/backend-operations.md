# Backend Reliability and Operations

## Authority and Failure Semantics

PostgreSQL is the durable source of truth for run status, execution ownership,
events, approvals, and recovery. Redis run lists are scheduling hints only.
Successful enqueue does not grant execution ownership. Duplicate, lost, malformed,
stale, and missing hints must not alter the persisted lifecycle.

The Redis components are in `kernel_runtime.queue` and
`kernel_runtime.redis_support`. The API and Worker composition roots wire them
into startup/shutdown and queue processing. Two independent API instances are
also tested against real Redis for shared admission and fail-closed behavior.
An adapter test alone is not proof that that wiring exists.

The Compose Worker uses `restart: unless-stopped`. A database outage fails the
current process closed; Docker supervises process restart with its own backoff.
An explicit operator stop remains stopped. Other deployment platforms must
provide equivalent supervision. This is not automatic Run retry: running work
with uncertain external effects stays subject to lease expiry and explicit
recovery, while committed queued runs remain available for a new process.
Investigate persistent restart loops rather than suppressing configuration,
authentication or schema failures.

Required integration contract:

1. Commit the queued run in the database before calling `queue.enqueue(run.id)`.
2. Catch `QueueUnavailableError` (including `QueueFullError`); record a bounded
   failure metric without rolling back or hiding the committed run. Return the
   accepted persisted run. Never report enqueue as successful when it failed.
3. Workers use hints to select candidates, then acquire execution ownership in
   the database. They continue periodic database polling even when Redis is
   healthy and constantly nonempty; otherwise missed hints can starve forever.
4. Queue empty/error/malformed-only batches immediately allow database polling.
   A worker crash after LPOP loses a hint, not the task. Recovery must use leases
   and persisted status; an LPOP is not an acknowledgment or an execution lock.
5. Use a bounded polling interval and batch size. The queue adapter accepts at
   most 1,000 items per dequeue and never loops to replace malformed items.
6. These adapters are synchronous. Use a thread boundary in async API handlers
   and do not block an event loop on Redis socket operations. Close the client
   during application shutdown after workers stop using it.

## Configuration and API

`RedisSettings.from_env()` validates configuration without making a connection.
`create_redis_client(settings)` returns an application-owned redis-py client.
`create_run_queue(settings, client=client)` returns a bounded `RedisRunQueue` or
`None` in database-only mode. Import these directly from
`kernel_runtime.redis_support`; exceptions are in `kernel_runtime.queue`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Connection URL; use `rediss` outside trusted local development |
| `AGENT_KERNEL_RUN_QUEUE_BACKEND` | `database` | `database` or `redis` |
| `AGENT_KERNEL_RUN_QUEUE_NAME` | `agent-kernel:runs:queued` | Deployment-specific hint list |
| `AGENT_KERNEL_RUN_QUEUE_MAX_LENGTH` | `10000` | Atomic queue capacity, 1 to 1,000,000 |
| `AGENT_KERNEL_REDIS_TIMEOUT_SECONDS` | `1` | Per-operation socket timeout, positive and at most 30 seconds |
| `AGENT_KERNEL_REDIS_CONNECT_TIMEOUT_SECONDS` | `1` | Connection timeout with the same bounds |
| `AGENT_KERNEL_REDIS_MAX_CONNECTIONS` | `20` | Client pool cap, 1 to 1,000 |
| `AGENT_KERNEL_RATE_LIMIT_PREFIX` | `agent-kernel:rate-limit` | Deployment-specific admission keys |
| `AGENT_KERNEL_RATE_LIMIT_PRINCIPAL_REQUESTS` | `0` | Optional workspace-local principal quota across keys |
| `AGENT_KERNEL_RATE_LIMIT_API_KEY_REQUESTS` | `0` | Optional independent key quota; admission checks all enabled quotas atomically |

URL query overrides are rejected so URL parameters cannot silently disable
timeouts or TLS verification. Credentials are not included in settings repr or
adapter error messages. Supply secrets through the deployment secret mechanism.
The factory disables automatic command retries: a timed-out write may already
have executed. Database-only mode does not import redis-py. Redis mode requires
an explicitly declared and locked redis-py dependency in the host application.

For compatibility, direct `RedisRunQueue(client=...)` construction without
`max_length` retains the earlier unbounded behavior. Production composition must
use the factory or provide `max_length`. Bounded enqueue uses one Lua EVAL;
`LLEN` followed by a separate push would race across API replicas. Queue overflow
rejects the new hint and leaves older hints intact. Deploy a single consistent
capacity policy across producers.

Malformed UUID strings and invalid UTF-8 bytes are removed and counted via
`malformed_items` and optional `on_malformed(count)` callback, without retaining
raw payloads. A broken callback cannot discard valid siblings. Unsupported
non-byte/non-string values indicate a client contract bug and raise `TypeError`.

Redis needs ACL permission for the deployment's keys and commands EVAL, LLEN,
RPUSH, LPOP, GET, INCR, PEXPIRE, PTTL, PING, and connection setup commands used by
the selected redis-py version. Test ACLs against the locked client before deploy.
Use an isolated Redis instance or capacity budgets; key prefixes are not ACLs.

## Shared Workspace Admission Limits

`RedisWorkspaceRateLimiter(client=client, prefix=settings.rate_limit_prefix)`
provides `check(workspace_id, limit=..., window_seconds=...)` returning
`RateLimitDecision(allowed, remaining, retry_after_seconds)`.

The authenticated workspace UUID comes from trusted API identity, not request
arguments. Workspace membership authorization runs before rate limiting; health checks and
operator endpoints need an explicit admission policy. All replicas must use
the same Redis backend, prefix, limit, and window for one shared quota.
Route-level permission checks follow admission; denied route attempts by an
otherwise valid member still count against its workspace's request quota.

The algorithm is a fixed window beginning at the first admitted request. One
atomic Lua operation reads the count, increments an admitted request, and sets
TTL on first use. Rejected requests do not extend TTL. Policy values are part of
the key to avoid inheriting an incompatible expiration after policy changes.
The key expires automatically. Counts have no raw user/API-key content.

- Allowed: proceed; expose remaining quota only to the authorized caller.
- Denied: return HTTP 429 with `Retry-After` from the decision.
- `RateLimitUnavailableError`: return HTTP 503. Do not silently allow or fall
  back to a per-process limiter while claiming distributed enforcement.
- Invalid/missing TTL or malformed server response: fail closed.

Atomicity on one primary does not mean lossless replication during Redis
failover. Eviction, restart without persistence, or failover can reset counters.
This is request admission, not billing, a durable spending cap, or exactly-once
enforcement. A strict financial budget requires database-backed accounting.

## Reproducible Test Services

Use dedicated loopback-only services, never existing application containers:

```bash
docker run -d --rm --name agent-kernel-drill-redis-p4 \
  --label agent-kernel.drill=true -p 127.0.0.1:16379:6379 redis:7-alpine
docker run -d --rm --name agent-kernel-drill-postgres-p4 \
  --label agent-kernel.drill=true -p 127.0.0.1:15432:5432 \
  -e POSTGRES_USER=agent_kernel -e POSTGRES_PASSWORD=drill-only \
  -e POSTGRES_DB=agent_kernel_test pgvector/pgvector:pg16
export AGENT_KERNEL_ALLOW_BACKEND_DRILL=1
export AGENT_KERNEL_TEST_REDIS_URL=redis://127.0.0.1:16379/15
export AGENT_KERNEL_TEST_POSTGRES_URL=postgresql+psycopg://agent_kernel:drill-only@127.0.0.1:15432/agent_kernel_test
export AGENT_KERNEL_TEST_PG_TOOLS_CONTAINER=agent-kernel-drill-postgres-p4
uv run python -m pytest -q tests/integration/test_real_redis_contract.py tests/integration/test_real_backend_drill.py
uv run python -m pytest -q tests/integration/test_real_pgvector_backend_contract.py tests/integration/test_pgvector_workspace_scope.py
uv run python -m scripts.backend_drill queue
uv run python -m scripts.backend_drill backup --pg-tools-container agent-kernel-drill-postgres-p4
docker stop agent-kernel-drill-redis-p4 agent-kernel-drill-postgres-p4
```

Start only after verifying the named ports are free; choose different loopback
ports if needed. Container test passwords are not production defaults. Test
failures must remain failures; do not convert unreachable configured services
to skips. With no test URL, opt-in suites skip explicitly.

Redis contracts exercise two independent clients and concurrent admissions,
atomic queue capacity, FIFO, malformed bytes, expiry, workspace separation,
wrong-type failures, and real connection refusal with bounded client timeouts.
They never call FLUSHDB; cleanup deletes only generated
test keys. The queue drill intentionally loses dequeued hints, rejects overflow,
and injects a queue WRONGTYPE error, then proves database polling executes all
persisted fixture runs. Its durable store is an isolated PostgreSQL schema selected
by `AGENT_KERNEL_TEST_POSTGRES_URL`. It does not claim actual network-partition
coverage; separate worker tests cover concurrency and lease contracts.

Native pgvector contracts additionally exercise cosine ranking/top-k, model and
dimension separation, replacing an existing model's vectors, retaining other
models, and rollback after a failed replacement transaction. Existing workspace
contracts cover fresh migrations, legacy upgrade/downgrade and scoped retrieval.
These tests use generated schemas, not the application's public schema.

Local verification on 2026-11-13: 32 unit contracts passed; the combined real
backend suite above passed 8 tests on Redis 7 and pgvector PostgreSQL 16. The
queue CLI recovered 3 persisted fixture runs after hint loss/overflow and a
queue error. The restore CLI verified 19 tables, 2 linked objects, native vector
retrieval and deliberate corruption rejection. These are synthetic local test
results, not production throughput, RPO/RTO, S3 recovery or remote CI evidence.

For an integrated deployment outage drill: create a set of committed runs,
stop only its dedicated Redis test container, verify the configured worker
continues DB polling, restart Redis, and assert every run reaches exactly one
allowed terminal lifecycle. Record queue errors, poll latency, stale lease
recovery, and provider-side idempotency evidence. Never kill shared Redis.

## Semantic Cache Assessment

Decision: defer implementation until a measured workload demonstrates useful
net benefit. Current functional/fixture tests do not establish reuse rates or
real-model savings, so this document supplies no invented cache hit figures.

Collect an opt-in, redacted, workspace-scoped replay dataset covering ordinary
questions, near duplicates, changed documents, changed prompts/models, tool
side effects, approvals, and revoked permissions. Record prompt/model versions,
retrieval document/index revisions, policy context, token counts, provider cost,
latency, outcome, and exact citation IDs. Never pool data across workspaces.

Evaluate an uncached baseline, exact-key cache, then a proposed semantic cache
offline on a held-out set. Sweep similarity thresholds and review false hits
with the same behavior/citation/security evals used for live execution. Report:

- Eligible queries, exact and semantic hit ratios, with sample count and period.
- False-hit rate and answer/citation correctness relative to the baseline.
- Cross-workspace, revoked-access, changed-document and changed-prompt failures.
- Net token/cost savings after embedding, lookup, storage and invalidation cost.
- End-to-end p50/p95 latency including cache misses and maintenance overhead.

Predeclare acceptance thresholds with maintainers before looking at held-out
results. Tool writes, approval decisions, secrets, unversioned sources, and
permission-sensitive context are ineligible unless correctness can be proved.
Any security false hit blocks release regardless of average savings. Version
cache keys and invalidate on knowledge/policy/model/prompt changes. If exact
caching captures most benefit or net gains are unconvincing, retain no semantic
cache. No Redis adapter completion is evidence that semantic caching is needed.

## References

- [redis-py connection configuration](https://redis.readthedocs.io/en/stable/connections.html)
- [Redis EVAL command](https://redis.io/docs/latest/commands/eval/)
- [Backup and restore](backup-restore.md)
