# Upgrade and Migration Policy

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

For v1.0, the supported production database is PostgreSQL. SQLite remains
supported for local development, tests, and quickstart flows.

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
- Treating SQLite as a multi-user production database.
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

Alembic migration rules:

- Every schema change must have an Alembic migration.
- Migration revision ids must fit Alembic's default `version_num VARCHAR(32)`.
- Migrations must support fresh upgrade from an empty SQLite database unless
  they are explicitly PostgreSQL-only and guarded.
- PostgreSQL-only migrations must check the dialect before executing
  PostgreSQL-specific DDL.
- SQLite table alterations that add or drop constraints must use Alembic batch
  operations.
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
uv run pytest tests/unit/test_migrations.py
DATABASE_URL=sqlite:////tmp/agent-kernel-ci.db uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg://agent_kernel:agent_kernel@localhost:5432/agent_kernel uv run alembic upgrade head
```

The GitHub CI Python job runs SQLite and Postgres/pgvector migration smoke
checks. Local Postgres migration checks require a running Postgres/pgvector
database, such as the Docker Compose `postgres` service.

`tests/unit/test_migrations.py` must continue to cover:

- Revision id length compatibility.
- Fresh SQLite upgrade to Alembic head.
- PostgreSQL-only pgvector migration guard behavior.

## SQLite Policy

SQLite is supported for:

- Local quickstart.
- Unit and integration tests.
- Single-developer experimentation.
- Fast migration smoke checks.

SQLite is not supported for:

- Multi-user production deployments.
- Production pgvector search.
- Distributed worker coordination.
- High-concurrency write workloads.

All releases should keep SQLite fresh-upgrade compatibility unless a release
note explicitly says otherwise.

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
- SQLite must skip pgvector-specific DDL.
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

- Fresh SQLite migration.
- Fresh Postgres/pgvector migration.
- Existing database upgrade, when applicable.
- Full release smoke tests.

## Release Blockers

Block a release if:

- Fresh SQLite migration to head fails.
- Fresh Postgres/pgvector migration to head fails.
- A migration revision id exceeds the Alembic version column limit.
- A PostgreSQL-only migration runs unguarded on SQLite.
- A stable API, CLI, or configuration change is not documented.
- A migration requires data loss without release-note approval.
- The target release cannot pass the documented smoke test matrix.

## v1.0 RC Handoff

Day 79 will add backup and restore guidance. Until then, the upgrade contract is
simple:

```text
Do not run production migrations without a verified backup or restore point.
```

The v1.0 final release checklist must reference this policy and confirm that
the release's migrations were tested through the documented paths.
