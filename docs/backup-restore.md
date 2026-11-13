# Backup and Restore Guide

This guide defines the v1.0 release candidate backup and restore expectations
for self-hosted Agent Kernel deployments.

Agent Kernel stores important state in two places:

- Database: agents, runs, events, approvals, memories, knowledge-base metadata,
  document metadata, ingestion jobs, chunks, embeddings, leases, API keys, and
  eval runs.
- Object storage: uploaded document bytes and parsed document artifacts.

Both must be backed up together. A database backup without matching object
storage can leave documents, citations, ingestion artifacts, and retrieval
workflows incomplete.

## Automated Test-Only Restore Rehearsal

`python -m scripts.backend_drill backup` implements a real `pg_dump`/`pg_restore`
rehearsal with a matching local-object manifest. It is deliberately not a
production backup command. The exact disposable service setup and test commands
are in [Backend operations](backend-operations.md#reproducible-test-services).

Safety gates are mandatory: `AGENT_KERNEL_ALLOW_BACKEND_DRILL=1`, a loopback
PostgreSQL URL whose database is exactly `agent_kernel_test`, and no URL query
overrides. The script creates two random `agent_kernel_drill_*` databases using
that dedicated service account. It never dumps, restores, migrates or deletes
an existing application database. Objects and backup files live under a newly
created temporary directory. Cleanup drops only databases created by this
invocation and removes that temporary directory.

A force-killed process cannot guarantee cleanup. Inspect only the disposable
service for leftover `agent_kernel_drill_*` databases and temporary directories;
stop/remove the dedicated test container to discard its whole test-only state.
Never use a broad database-prefix cleanup command against an application server.

The account needs CREATE DATABASE on the disposable service. With local
PostgreSQL tools, `pg_dump` and `pg_restore` must be on PATH and version-compatible
with the test server. Without local tools, `--pg-tools-container` uses the tools
inside the disposable PostgreSQL container; it must have the
`agent-kernel-drill-` name prefix and `agent-kernel.drill=true` label. Only these
test database names reach the tool subprocesses. Credentials are passed through
environment variables and are not printed in the JSON report.

The rehearsal performs these checks:

1. Apply current Alembic migrations to a fresh fixture database, including
   native pgvector schema.
2. Persist a workspace, knowledge base, document source, parsed ingestion
   artifact, chunk and embedding with real references and SHA-256 checksums.
3. Record all database rows, the Alembic revision, linked object URIs, object
   byte counts and checksums in a manifest. Reject source/KB, parsed/job and
   embedding/chunk/document linkage mismatches.
4. Produce a custom-format database dump and record its SHA-256 alongside the
   object manifest. Copy the matching object set while the fixture is quiescent.
5. Restore into the second empty database and a separate object root. Compare
   full canonical database row content, not just row counts, and verify every
   linked original/parsed object against both its DB checksum and the manifest.
6. Execute a native pgvector similarity query on the restored fixture.
7. Corrupt one restored artifact and prove validation rejects it. Unit tests
   also cover missing bytes, modified DB rows and unsafe object paths.

The JSON report contains pass/fail, tables/objects verified, native retrieval
verification and corruption-detection result. It contains no real user data;
retain reports with the commit SHA and service versions as release evidence.
Failed subprocess/driver details are intentionally not echoed because they may
contain credentials. Inspect the disposable service locally for diagnosis.

Limitations: this is a synthetic, quiescent PostgreSQL + **local-object-store**
rehearsal, not proof of S3 versioning, production RPO/RTO, replication recovery,
encryption-key recovery, or restoring an arbitrary historical production dump.
S3/MinIO deployments must additionally rehearse their bucket/version snapshot
and remapping procedure below; do not mark that backend verified from this test.
Manifest hashes detect accidental corruption, not malicious tampering: sign or
authenticate production manifests separately and encrypt backup artifacts.

## Backup Scope

Required production backup scope:

- PostgreSQL database.
- Object storage bucket or local object store volume.
- Deployment configuration, excluding secret values in plaintext.
- Secret inventory and recovery process.
- Release version, git SHA, image digests, and Alembic revision.

Recommended metadata to record with every backup:

```text
agent_kernel_version
git_sha
container_image_digest
alembic_revision
database_engine
object_store_backend
object_store_bucket_or_path
created_at
operator
```

## PostgreSQL Backup

Recommended logical backup:

```bash
pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file agent-kernel-$(date +%Y%m%d%H%M%S).dump \
  "$DATABASE_URL"
```

Recommended restore into a fresh database:

```bash
createdb agent_kernel_restore
pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --dbname "$RESTORE_DATABASE_URL" \
  agent-kernel-YYYYMMDDHHMMSS.dump
```

After restore:

```bash
DATABASE_URL="$RESTORE_DATABASE_URL" uv run alembic current
DATABASE_URL="$RESTORE_DATABASE_URL" uv run alembic upgrade head
```

Operational notes:

- Use managed database snapshots where available, but keep a tested logical
  backup path for portability.
- Back up before every production migration.
- Keep backups encrypted at rest.
- Store backups outside the primary database host or primary volume.
- Monitor backup job success and backup age.
- Test restore into an isolated environment before trusting the backup policy.

## SQLite Local Backup

SQLite is not a production database for Agent Kernel, but local development data
can still matter.

Default SQLite path:

```text
.agent-kernel/agent_kernel.db
```

Simple local backup while the API and worker are stopped:

```bash
cp .agent-kernel/agent_kernel.db .agent-kernel/agent_kernel.backup.db
```

SQLite online backup through the SQLite shell:

```bash
sqlite3 .agent-kernel/agent_kernel.db ".backup '.agent-kernel/agent_kernel.backup.db'"
```

Restore:

```bash
cp .agent-kernel/agent_kernel.backup.db .agent-kernel/agent_kernel.db
uv run alembic upgrade head
```

SQLite backups are for developer convenience only. Do not treat them as a
production disaster-recovery strategy.

## Local Object Store Backup

Local object storage is controlled by:

```bash
AGENT_KERNEL_OBJECT_STORE_BACKEND=local
AGENT_KERNEL_OBJECT_STORE_ROOT=.agent-kernel/objects
```

Back up the object store root with a tool that preserves directory structure
and file contents:

```bash
tar -czf agent-kernel-objects-$(date +%Y%m%d%H%M%S).tgz .agent-kernel/objects
```

Restore:

```bash
mkdir -p .agent-kernel
tar -xzf agent-kernel-objects-YYYYMMDDHHMMSS.tgz -C .
```

Production local object storage requires a durable mounted volume. Do not store
production artifacts only in an ephemeral container filesystem.

## S3 and MinIO Backup

S3-compatible object storage is controlled by:

```bash
AGENT_KERNEL_OBJECT_STORE_BACKEND=s3
AGENT_KERNEL_S3_BUCKET=agent-kernel
AGENT_KERNEL_S3_PREFIX=prod
AGENT_KERNEL_S3_ENDPOINT_URL=
AGENT_KERNEL_S3_REGION=us-east-1
```

Recommended AWS S3 protections:

- Enable bucket versioning.
- Enable server-side encryption.
- Enable lifecycle policies for retention and archival.
- Restrict bucket access to the Agent Kernel deployment and backup operators.
- Monitor object count, replication status, and failed replication metrics.

Recommended MinIO protections:

- Use distributed MinIO or another highly available topology for production.
- Enable object versioning where practical.
- Replicate to another bucket or cluster for disaster recovery.
- Back up MinIO configuration and credentials separately through your platform
  secret management process.

Portable object backup with AWS CLI-compatible tooling:

```bash
aws s3 sync \
  "s3://$AGENT_KERNEL_S3_BUCKET/$AGENT_KERNEL_S3_PREFIX" \
  ./agent-kernel-object-backup/
```

Restore:

```bash
aws s3 sync \
  ./agent-kernel-object-backup/ \
  "s3://$AGENT_KERNEL_S3_BUCKET/$AGENT_KERNEL_S3_PREFIX"
```

For MinIO, configure the AWS CLI endpoint:

```bash
aws --endpoint-url "$AGENT_KERNEL_S3_ENDPOINT_URL" s3 sync \
  "s3://$AGENT_KERNEL_S3_BUCKET/$AGENT_KERNEL_S3_PREFIX" \
  ./agent-kernel-object-backup/
```

## Coordinated Backup

Database and object storage should be backed up as a coordinated unit.

Minimum coordinated backup sequence:

1. Record the current application version, git SHA, image digest, and Alembic
   revision.
2. Stop workers.
3. Drain or temporarily stop write-heavy API traffic where practical.
4. Back up PostgreSQL.
5. Back up object storage or confirm object-store versioning/snapshot point.
6. Restart workers if they were stopped.
7. Store backup metadata with both backup artifacts.

For strict consistency, use database snapshots and object-store versioning or
provider snapshots taken as close together as possible. For small self-hosted
deployments, a short maintenance window is usually simpler and safer.

## Restore Sequence

Restore into an isolated environment first:

1. Provision a fresh database.
2. Restore the database backup.
3. Restore or point to the matching object storage backup.
4. Configure `DATABASE_URL` and object-store environment variables.
5. Run:

   ```bash
   uv run alembic current
   uv run alembic upgrade head
   ```

6. Start the API.
7. Check:

   ```http
   GET /healthz
   GET /metrics
   ```

8. Start one worker with a small limit:

   ```bash
   agent-kernel-worker --once --limit 1
   ```

9. Run restore validation checks.

Only promote a restored environment after validation passes.

## Restore Validation Checklist

Validate restored database state:

- Agents can be inspected.
- Runs can be inspected.
- Run events are present.
- Approval records are present.
- Knowledge bases and documents list correctly.
- Memory records list correctly.
- Eval runs list correctly.
- Alembic revision is current.

Validate restored object storage:

- Uploaded document source objects can be read.
- Parsed text artifacts can be read.
- Document ingestion, chunking, and indexing metadata still reference valid
  object URIs.
- Retrieval citations point to existing document metadata and source URIs.

Validate runtime behavior:

- API health check passes.
- `/metrics` responds.
- CLI can inspect an existing run.
- Worker can start without schema errors.
- Deterministic eval report still runs.

Suggested commands:

```bash
uv run alembic current
uv run agent-kernel run inspect <run-id>
uv run agent-kernel kb list
uv run agent-kernel memory list --limit 5
uv run agent-kernel eval report evals/rag-smoke.json
```

## Retention Guidance

Minimum practical retention for self-hosted pilots:

- Daily backups for 7 days.
- Weekly backups for 4 weeks.
- Monthly backups for 3 months.
- Backup before every migration.

Production teams should adapt retention to compliance, cost, and recovery-time
requirements.

## Recovery Objectives

Define these before production use:

- RPO: maximum acceptable data loss window.
- RTO: maximum acceptable service restore time.

Agent Kernel does not enforce RPO or RTO. The operator's database, object
storage, deployment platform, and monitoring choices determine them.

## Security Requirements

Backups can contain sensitive data:

- Prompts and user inputs.
- Tool arguments and outputs.
- Approval decisions.
- Memory content.
- Document text and uploaded files.
- API key hashes.
- Trace IDs and operational metadata.

Backup storage must:

- Encrypt backups at rest.
- Restrict read access.
- Keep restore credentials separate from application runtime credentials.
- Avoid dumping plaintext API keys into logs.
- Support credential rotation after incident response.

## Release Requirements

Before v1.0 final:

- This guide must be linked from the release checklist.
- A clean restore rehearsal should run against a non-production environment.
- Release notes must mention any migration that changes backup or restore
  expectations.
- Operators must not run production migrations without a verified backup or
  restore point.

## Explicit Non-Goals

This guide does not implement:

- Backup scheduling automation.
- Encrypted backup pipelines.
- Managed cloud disaster recovery.
- Cross-region replication templates.
- Object-store lifecycle policies as code.
- Restore drills in CI.

Those are deployment-specific and may be automated in a later operations track.
