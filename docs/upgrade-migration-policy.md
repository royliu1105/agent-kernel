# Upgrade and Migration Policy

## Post-v1.0 Hardening Upgrade

Unreleased head: `0019_execution_checkpoint`. Stop API writers and all workers,
take a verified backup, then run `uv run alembic upgrade head` before deploying
the new application. Do not mix old workers (without fencing) with new workers.

- `0015_scope_knowledge_bases`: KB ownership and derived child scope.
- `0016_scope_memory_evals`: nullable ownership on memory and evaluation records.
- `0017_unique_active_lease`: one unreleased lease per run, including expired
  leases until explicitly released/recovered/replaced.
- `0018_usage_attribution`: nullable trusted Run initiator and per-model response
  usage ledger. Historical totals become `unknown` model/provider rows; historical
  principals stay null, never inferred from input JSON. Downgrade drops detailed
  attribution, preserving Run totals; back up before any downgrade.
- `0019_execution_checkpoint`: nullable private native continuation JSON on
  Runs. Existing records are retained with no invented history. Legacy native
  approvals without a checkpoint fail closed on resume; inspect effects and
  create a deliberately reviewed new run. Explicit-tool approvals are unchanged.
  Downgrade irreversibly drops continuation history; do not downgrade with
  pending native approvals. Stop all writers, back up and prefer a verified
  restore. Do not mix pre-checkpoint and new executors during this upgrade.

Checkpoints contain task, tool results and provider reasoning payloads. Protect
database backups accordingly; they are private storage, not Run API fields or
log/metric payloads. Current continuation requires the original provider route
and tool contracts. Changing either can deliberately prevent a pending resume.

Real embeddings now require explicit `AGENT_KERNEL_EMBEDDING_PROVIDER=openai`
on both API and Worker. Default mock behavior is preserved. Switching provider,
model or dimensions does not convert existing vectors: reindex the affected
documents before querying with the new configuration. Queries filter by model.

Before `0017`, run this read-only preflight:

```sql
SELECT run_id, COUNT(*) FROM worker_leases
WHERE released_at IS NULL GROUP BY run_id HAVING COUNT(*) > 1;
```

If any rows appear, stop and review their runs and possible external effects.
Do not blindly delete duplicate leases or retry writes. After stopping owners,
an operator must deliberately resolve/release conflicting claims with an audit
record. The migration fails rather than choosing an owner silently.

Legacy `knowledge_bases`, `memory_items` and `eval_runs` keep `workspace_id=NULL`.
They remain visible only to trusted auth-disabled operator access. For each
record, independently verify ownership, back up, and assign an existing workspace
in an offline transaction. Memory `source_run_id` must belong to the same
workspace. Validate A/B denial after assignment. Never assign all legacy rows to
the first API caller. Downgrades remove ownership and lease protection: stop all
writers and prefer a verified restore; do not expose downgraded code publicly.

Compatibility changes: metrics on authenticated deployments require a separate
`AGENT_KERNEL_MONITORING_TOKEN`; repeated identical approval decisions return
the original result (200), opposing decisions return 409; stale execution writes
return 409; optional shared admission limits return 429/`Retry-After`, or 503
when their required Redis backend is unavailable. The default local mock path
does not enable rate limiting, external tools or a Worker metrics listener.

This document defines the Agent Kernel v1.0 release candidate policy for
upgrading application code, configuration, and database schema.

The policy applies to self-hosted deployments. It does not describe a managed
cloud upgrade process.

## Compatibility Baseline

Agent Kernel uses:

- Git tags and release notes for application versions.
- Alembic revisions for database schema versions.
- [API and CLI Compatibility Policy](api-cli-compatibility.md) for public
  interface compatibility.
- [Versioned Configuration Reference](configuration.md) for environment
  variable compatibility.

Current unreleased mainline supports PostgreSQL only in all environments.
The historical v1.0 SQLite support is superseded by [this change](postgresql-only.md).

## Supported Upgrade Paths

Supported:

- v1.0 release candidate to a later v1.0 release candidate.
- v1.0 release candidate to v1.0 final.
- v1.0 final to a later v1.x release.
- v0.1.0 or Public Alpha/Beta development deployments to v1.0 RC after running
  all migrations and reviewing release notes.

Unsupported:

- Skipping required migrations.
- Running v1.0 application code against a database that has not been upgraded
  to the release's expected Alembic head.
- Downgrading production databases as a normal rollback strategy.
- Selecting any non-PostgreSQL database on current mainline.
- Upgrading across uncommitted local schema changes without a manual migration
  review.

## Standard Upgrade Sequence

For a production-like deployment:

1. Read the target release notes.
2. Read this policy and [Versioned Configuration Reference](configuration.md).
3. Confirm the current application version and git SHA.
4. Confirm the current database Alembic revision:

   ```bash
   uv run alembic current
   ```

5. Stop background workers.
6. Stop or drain API writes where practical.
7. Create a verified backup or restore point.
8. Deploy the new application image or checkout.
9. Run database migrations as an explicit job:

   ```bash
   uv run alembic upgrade head
   ```

10. Start the API.
11. Check health and metrics:

    ```http
    GET /healthz
    GET /metrics
    ```

12. Start workers.
13. Run the release smoke tests for the target release.
14. Watch logs, traces, metrics, and failed run counts during the observation
    window.

The Docker Compose API service runs migrations before startup for local
convenience. Production deployments should prefer an explicit migration job so
schema migration failures are separated from application startup failures.

## Migration Rules for Maintainers

### Knowledge Ownership Upgrade (P1.1)

New head: `0015_scope_knowledge_bases`, following `0014_create_eval_runs`.
This additive migration introduces nullable `knowledge_bases.workspace_id` with
a workspace foreign key and index. Existing data stays NULL-owned. It is
available in trusted auth-disabled local mode but invisible to authenticated
workspaces. No first-user claim or automatic backfill occurs.

For an existing shared deployment, ownership assignment is an explicit offline
operator operation:

1. Stop API writes and workers; take a matching database/object-store backup.
2. Run `uv run alembic upgrade head` and verify the new revision.
3. Review one KB at a time, confirm the intended workspace and membership, and
   record an explicit KB-to-workspace mapping. Do not use a blanket UPDATE.
4. Audit each source URI: it must be a canonical local/S3 key ending in
   `knowledge-bases/<kb-id>/documents/<filename>`. Parsed artifacts must end in
   `documents/<document-id>/parsed/<job-id>.txt`. Foreign references, traversal,
   URL-encoded keys, arbitrary file/HTTP URLs and noncanonical legacy sources
   are not accessible in scoped mode. Re-upload/re-ingest these documents into
   the correct KB; do not merely relabel an object from another owner.
5. Bind reviewed IDs as SQL parameters in one transaction per KB:

   ```sql
   UPDATE knowledge_bases
   SET workspace_id = :workspace_id
   WHERE id = :knowledge_base_id
     AND workspace_id IS NULL
     AND EXISTS (SELECT 1 FROM workspaces WHERE id = :workspace_id);
   ```

   Require exactly one changed row. On zero/unexpected rows, roll back and
   investigate. Record operator, IDs, time and verification evidence. This is
   initial assignment only, not an online ownership-transfer API.
6. Verify the owner's list/detail/retrieval and a second workspace's denials
   using separate API keys, then restart services. An API key grants access
   only to its own workspace; no request/body field overrides this.

Security compatibility: the knowledge-base response adds optional
`workspace_id`. Authenticated access to formerly global KBs and arbitrary
document source registrations is intentionally restricted. Upload is the
preferred authenticated ingestion path. Local auth-disabled quickstart behavior
is retained. Do not roll back to an old unscoped application against shared data:
it would bypass the new authorization boundary. Downgrade drops ownership
information and is test-only, not a production rollback strategy.

Real PostgreSQL contracts run in CI and can run locally against a **dedicated
test database** with pgvector and schema/extension creation privileges:

```bash
AGENT_KERNEL_TEST_POSTGRES_URL=postgresql+psycopg://agent_kernel:agent_kernel@localhost:5432/agent_kernel_test \
  uv run pytest tests/integration/test_pgvector_workspace_scope.py
```

Tests create and remove random `test_knowledge_*` schemas and install the vector
extension in `public` if needed. Never point this variable at production.
Without the variable, these tests skip locally; a skip is not acceptance
evidence. Coverage includes fresh/legacy upgrades, NULL ownership, pgvector
retrieval denial, and downgrade/re-upgrade checks.

Alembic migration rules:

- Every schema change must have an Alembic migration.
- Migration revision ids must fit Alembic's default `version_num VARCHAR(32)`.
- Migrations must support fresh and legacy-data upgrades on PostgreSQL/pgvector.
- The migration entrypoint rejects non-PostgreSQL connections before DDL.
- Existing PostgreSQL revision IDs and schema behavior must remain stable.
- Migrations must be deterministic and safe to run once.
- Migrations must not depend on application services being online.
- Data backfills must be idempotent where practical.
- Long-running backfills should be split from schema changes before v1.0 final.

Model and repository rules:

- SQLAlchemy models and Alembic migrations must stay aligned.
- New persisted domain concepts should include storage repository tests.
- Existing columns should not be repurposed with incompatible meaning.
- Nullable columns are preferred when preserving local development or upgrade
  compatibility for existing rows.

## Migration Test Expectations

Release-blocking migration checks:

```bash
make test-db-up
AGENT_KERNEL_TEST_POSTGRES_URL=postgresql+psycopg://agent_kernel:test-only@127.0.0.1:55432/agent_kernel_test \
  uv run pytest tests/unit/test_migrations.py tests/integration/test_execution_checkpoint_storage.py tests/integration/test_usage_migration.py
```

The GitHub CI Python job runs PostgreSQL/pgvector migration checks in isolated
test schemas. Local checks use the dedicated test service, never the active
Docker experience database. See [test setup](postgresql-only.md).

`tests/unit/test_migrations.py` must continue to cover:

- Revision id length compatibility.
- Fresh PostgreSQL upgrade to Alembic head.
- Native pgvector migration, legacy data and downgrade/re-upgrade behavior.

## Removed Backend

SQLite is no longer supported. Old data must be exported with an older checkout
and migrated separately if needed; this change does not provide an automatic
cross-database importer. Existing PostgreSQL deployments need no data rewrite.

## PostgreSQL Policy

PostgreSQL is the production database target.

Production expectations:

- Use PostgreSQL for production deployments.
- Use pgvector where production vector search is needed.
- Run migrations before API and worker startup.
- Keep the database on a private network.
- Monitor migration runtime, lock waits, and application errors during upgrade.

pgvector expectations:

- The pgvector migration installs the `vector` extension when running on
  PostgreSQL.
- Non-PostgreSQL URLs must fail before migration execution.
- The default HNSW expression index targets 1536-dimensional vectors.
- Different embedding dimensions require an index review before production use.

## Rollback Policy

Application rollback:

- Prefer rolling back application code only when the database migration was
  additive and the older application remains compatible.
- Confirm the older application does not depend on removed or renamed columns.
- Keep workers stopped until rollback compatibility is understood.

Database rollback:

- Do not rely on Alembic downgrade as the primary production rollback path.
- Treat database restore from backup or snapshot as the primary rollback path
  for destructive or incompatible migrations.
- Alembic downgrade functions are useful for local development and migration
  review, but they are not a substitute for production backups.

Destructive migration rule:

- Dropping columns, dropping tables, narrowing column types, or rewriting
  persisted JSON shapes requires explicit release-note callout.
- Prefer a two-release process: add new shape, dual-read or backfill, then
  remove old shape later.

## Configuration Upgrade Policy

Before upgrading:

- Compare `.env.example` with your deployment configuration.
- Review [Versioned Configuration Reference](configuration.md).
- Add new required production variables before deploying the new code.
- Do not put secrets in `NEXT_PUBLIC_*` variables.

Configuration changes are release blockers when:

- A stable variable is renamed without a compatibility path.
- A default changes production behavior in a security-sensitive way.
- A previously optional production variable becomes required without release
  notes.
- Accepted values change without validation tests.

## Release Note Requirements

Every release note must include:

- Expected Alembic head revision.
- Migration instructions.
- Any required configuration changes.
- Any destructive or potentially long-running migrations.
- Any known downgrade limitations.
- Any manual operator steps before or after migration.

For v1.0 RC releases, release notes should also state whether the release was
validated against:

- Fresh Postgres/pgvector migration.
- Existing database upgrade, when applicable.
- Full release smoke tests.

## Release Blockers

Block a release if:

- Fresh Postgres/pgvector migration to head fails.
- A migration revision id exceeds the Alembic version column limit.
- An unsupported database URL is accepted by the migration entrypoint.
- A stable API, CLI, or configuration change is not documented.
- A migration requires data loss without release-note approval.
- The target release cannot pass the documented smoke test matrix.

## Backup and Restore Requirement

Backup and restore guidance lives in [Backup and Restore Guide](backup-restore.md).
The upgrade contract is:

```text
Do not run production migrations without a verified backup or restore point.
```

The v1.0 final release checklist must reference this policy and confirm that
the release's migrations were tested through the documented paths.
