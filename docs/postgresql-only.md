# PostgreSQL-Only Storage

Status: local implementation, verification and active PostgreSQL-only Docker update
complete (2026-11-14); committed in `8f87473` and verified by candidate CI at `5952ba7`.
See the [review/CI record](reviews/2026-11-14-cf1-minimal-repair.md); CF1 itself is
not deployed to the active local runtime. This supersedes
SQLite support claims in earlier daily plans, release snapshots and acceptance
records; those historical results are not rewritten as PostgreSQL evidence.

## Decision and Compatibility

- PostgreSQL is the only supported relational database in development, tests
  and deployment. The default Docker runtime includes pgvector.
- `DATABASE_URL` is mandatory outside the configured Docker profile. Missing,
  malformed or unsupported database URLs fail before opening a connection.
  `postgresql://` is normalized to the installed sync psycopg driver.
- SQLite filesystem setup, thread options, dialect fallback and partial-index
  variants are removed. SQLite URLs remain only in explicit rejection tests.
- `auto` and `pgvector` use native pgvector. Explicit `json` remains a PostgreSQL
  JSON-vector similarity mode for existing callers; it is not another database.
- No new schema revision or data rewrite is needed for existing PostgreSQL at
  head. Historical revision IDs and PostgreSQL table/column contracts stay stable.
- This is an unreleased compatibility change: previous SQLite users need an
  older checkout to read their data or a separately planned export/import.
  There is no automatic SQLite-to-PostgreSQL migration.

## Isolated Tests

Never run test setup or destructive drills against the active local runtime DB.
Start a separate, disposable Docker PostgreSQL service:

```bash
make test-db-up
make test
make release-eval
make release-load-soak
make test-db-down
```

The test service uses project `agent-kernel-test`, loopback port 55432 and tmpfs
storage, not any `agent-kernel-local` data volume. Stopping this test database
discards only test data. For direct pytest/script commands, set
`AGENT_KERNEL_TEST_POSTGRES_URL` explicitly to the test service; `DATABASE_URL`
is never used as the fixture source. Make provides the dedicated test URL.

Each fixture/regression scenario creates and drops its own randomly named
schema, with real Alembic migrations and pgvector. Test URLs must name a database
ending in `_test` or starting with `agent_kernel_test_`, and cannot supply a
custom search path. Tests that require a DB fail clearly when it is absent;
they do not silently switch backend or skip the main storage gate. Keep test
credentials separate from production credentials; naming guards are not access
control. Independent-schema/process tests retain their concurrency boundaries.

Test connections must use an explicit loopback host and cannot override routing
through query parameters such as `service`, `host` or `dbname`. A different local
port can be selected with `make test-db-up AGENT_KERNEL_TEST_POSTGRES_PORT=55433`
and the same port argument on subsequent Make test/gate commands. Direct commands
can use the default service as follows:

```bash
export AGENT_KERNEL_TEST_POSTGRES_URL=postgresql+psycopg://agent_kernel:test-only@127.0.0.1:55432/agent_kernel_test
uv run pytest
```

Pytest validates an explicitly configured test URL before collecting tests, so
the same guards also apply to older opt-in PostgreSQL fixtures.

## Acceptance Ledger

- [x] PostgreSQL configuration rejection/normalization and isolation guards.
- [x] Full Python suite against the isolated PostgreSQL/pgvector service.
- [x] Fresh and legacy-data upgrades, downgrade/re-upgrade, checkpoint persistence.
- [x] Runtime timeline, bounded execution, approval, retries and load gates.
- [x] Ruff, mypy, documentation consistency and Compose validation.
- [x] Active Docker readiness and existing business records unchanged.
- [ ] Remote CI (requires a later authorized commit/push).

## Local Evidence

Verification used `agent-kernel-test` PostgreSQL, a dedicated Redis on port 56379,
a separate `agent-kernel-pgonly-check` API/Worker deployment, and a guarded
`agent-kernel-drill-pgonly-20261114` restore container. None shares the active
runtime's database, Redis or object volumes. All model calls were fixtures/mocks.

| Check | Result |
| --- | --- |
| Config rejection/normalization, isolated schema cleanup and migration/checkpoint checks | 51 passed |
| Full pytest, dedicated PostgreSQL/Redis and promtool enabled; restore test run separately | 1102 passed, 15 skipped in 228.23 s |
| Final focused docs and native-vector persistence checks | 82 passed, including the newly added documentation contract |
| Final no-database docs/config/startup and collection safety checks | 93 passed |
| `make release-eval` | RAG 3/3 and 4/4; tool evals 2/2; execution/approval/backoff/deadline 71/71; timelines 7/7 |
| `make release-load-soak` | 25/25 succeeded, zero failed/queued, 1320 ms (5-second limit) |
| Separate production-image build and HTTP deployment rehearsal | API/Worker images built; 1 E2E test passed: upload, ingest/chunk/index/retrieve, queue execution, MCP approval/resume |
| Actual pg_dump/pg_restore and matching object manifest | 1 passed, including pgvector and checkpoint recovery |
| Ruff / mypy | Passed; mypy checked 226 source files; changed tracked Python files and new test helpers pass format checks |
| Default/test Compose configuration and diff whitespace checks | Passed |
| Test fixture cleanup | Zero remaining `test_%` schemas before test DB teardown |
| Active runtime | All 13 original services still running; `/readyz` ready |

The full suite's 15 skips were Docker-local acceptance (4), monitoring deployment
(3), full observability/SMTP fault rehearsal (7), and HTTP deployment (1). The
HTTP deployment case was executed separately above. The other opt-in checks were
not silently counted as passing for this change; the earlier observability ledger
retains their historical evidence. The final focused run covers assertions added
after the full suite was collected.

The first restore attempt correctly rejected an incorrectly named test container.
It passed after the fixture container was renamed to satisfy the existing prefix
and label guards; the safety checks were not weakened.

Read-only business-database data dumps before and after verification had identical
SHA-256 (random pg_dump restrict markers excluded):
`dc15826ac97c186185b75e55bea00e4db8a63e355a8d988edc4d5d9f3489cc8b`.
During that isolated verification, no migration, test seeding, container rebuild,
or volume deletion was performed against `agent-kernel-local`. Its running images
still predated this code change at that point. The subsequent maintainer-authorized
active update is recorded below, separately from the disposable deployment.

All disposable test/deployment containers and their test storage were removed
after acceptance. The old stopped monitoring project was left untouched.

## Active Local Update

On 2026-11-14, the maintainer authorized `make docker-up` with existing data
preserved. API, Worker and Web images were rebuilt from the current working tree;
their containers were replaced. The existing PostgreSQL container and all data
volumes were retained. Storage configuration source hashes in API and Worker
match the working tree. Alembic remains at `0019_execution_checkpoint`.

- Before updating, no Runs were queued/running. A private custom-format
  PostgreSQL dump and object archive were saved under
  `.agent-kernel/backups/docker-update-20261114-S7QlbZ/`; both archive indexes
  were read successfully. This is a new PostgreSQL backup, not the deleted
  legacy SQLite backup.
- After updating, all 13 services are running; API dependency readiness passes,
  Worker is polling, and all 7 Prometheus targets are UP with no active alerts.
- Read-only Docker acceptance: **3 passed, 1 deselected**. The excluded case
  creates business data; it was deliberately not run against the active DB.
- Docker-targeted browser tests: **3 passed**, including the real Web/API
  connection and desktop/mobile rendering, without starting a host Web server.
- The original succeeded Run is accessible directly and through the Web proxy;
  document retrieval, its original Loki logs and Tempo trace remain accessible.
- The post-update business-data dump has the same SHA-256 recorded above.
  Both object files are unchanged; their sorted path/content manifest digest is
  `4f88e2a67031e51ac91bb2f025e7c5218149e067ba92f64192817741c4ef2b59`.
- One Loki readiness probe returned HTTP 503; a subsequent probe returned 200
  without intervention. No corresponding warning/error appeared in the inspected
  Loki log window. This observation does not establish a root cause or HA proof.

No volume deletion, new business fixture, Git pull, commit, push or remote CI was
performed during this update. Current local SMTP still ends at Mailpit; external
email delivery and live providers were not tested.
