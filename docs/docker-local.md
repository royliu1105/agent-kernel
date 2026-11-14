# Docker-Only Local Runtime

Status: **Local cutover/default startup and candidate remote CI verified (2026-11-14)**.
This is the default local startup contract, replacing the mixed host/Docker
experience. It does not change the language stack or claim production acceptance.

## Start and Operate

Prerequisites: Docker Desktop/Engine with Compose supporting `!override`/`!reset`,
POSIX `sh`, `openssl`, and optionally `make`. No host Python or Node process is
needed to serve the application.

```bash
make docker-up
make docker-status
make docker-logs SERVICE=worker
make docker-stop
make docker-up
```

Without make, use `sh scripts/local-stack.sh up`, `ps`, `logs worker`, or `stop`.
The first startup generates private credentials, builds API/Worker/Web images,
runs database migrations and starts **13 services in `agent-kernel-local`**:
API, Worker, Web, PostgreSQL/pgvector, Redis, Prometheus, Blackbox, Grafana,
Alloy, Loki, Tempo, Alertmanager and Mailpit. Images are rebuilt as needed by
`docker-up`; code is not bind-mounted and there is no hot reload.

`make docker-check` validates merged Compose configuration without printing
secrets. `make docker-build` builds images without starting services.
`make docker-down` removes containers/network but **preserves volumes**.
The wrapper deliberately rejects `down --volumes`. Never delete volumes or
`.agent-kernel/docker-local` just to restart: that destroys data or credential
continuity. Services restart after Docker restarts unless explicitly stopped.

## Endpoints

| URL | Service |
| --- | --- |
| `http://127.0.0.1:3000` | Web Workbench |
| `http://127.0.0.1:8000/docs` | API documentation |
| `http://127.0.0.1:8000/readyz` | Dependency readiness |
| `http://127.0.0.1:3090` | Grafana, username `admin` |
| `http://127.0.0.1:9090` | Prometheus |
| `http://127.0.0.1:9093` | Alertmanager |
| `http://127.0.0.1:8025` | Local Mailpit inbox |
| `http://127.0.0.1:3100` / `:3200` | Loki / Tempo diagnostic APIs |
| `http://127.0.0.1:4318/v1/traces` | Alloy OTLP receiver |

PostgreSQL, Redis, Blackbox and Worker metrics are internal-only. Web uses
`http://api:8000`, not host `localhost`, for server-side requests. Port mappings
are loopback-only. Default API authentication is disabled for this **trusted
single-user local profile**; do not expose it to a LAN or public network.

## Credentials and Configuration

Generated files live in ignored `.agent-kernel/docker-local/` (0700):

- `config.env`: generated monitoring/Grafana values (0600); optional host-port overrides.
- `grafana-password`: private Grafana password (0600); `make docker-init` prints its path, not its contents.
- `monitoring-token`: matching scrape token (0644 inside the private directory for container UID access).
- `smtp-password`: empty file used only with Mailpit; not a real SMTP credential.

The wrapper intentionally ignores root `.env`, `direnv` application variables,
provider credentials and alternate Compose projects/files inherited from the
host. Its dedicated env file and Compose overlays are the source of truth.
Supported port variables are documented in [configuration](configuration.md).
Keep the monitoring token in `config.env` and `monitoring-token` consistent.
Changing Grafana's initial password does not reset an already-created Grafana DB.

Models/embeddings are mock-only by default; no paid request or external email is
implicitly authorized. Mailpit captures SMTP messages locally. Real SMTP and
provider activation require a deliberate configuration/acceptance step, not a
host environment variable accidentally leaking into this stack.

## Data and Migration Boundary

PostgreSQL is the active relational/pgvector store. Redis uses a named volume
and AOF; it remains a queue hint layer, not the authoritative Run ledger.
Objects use the existing local-file adapter in `object_data`, shared by API and
Worker. **This profile does not add MinIO or switch objects to S3.** Telemetry,
Grafana, Prometheus and Mailpit also have named volumes. Docker container logs
use the bounded `local` logging driver (10 MB, 3 files per container), separately
from application file rotation and backend retention.

PostgreSQL is now also required by host debug and automated database tests;
there is no SQLite fallback. Tests use a separate disposable Docker service,
never this runtime's volumes. See [PostgreSQL-only testing](postgresql-only.md).

For the 2026-11-14 cutover the maintainer initially selected **fresh PostgreSQL
with old data retained**, not cross-database migration. Later the same day, the
maintainer explicitly requested deletion of the legacy data and its backup.
The `.agent-kernel/local-experience/` directory (SQLite, objects, logs and old
monitoring config), its pre-Docker archive, and the older
`.agent-kernel/agent_kernel.db` have now been deleted. Old records were not
migrated, and rollback through that legacy archive is no longer available.

Current Docker data volumes and `.agent-kernel/docker-local/` credentials were
not deleted. Old monitoring containers/volumes remain stopped and were outside
this file cleanup. Do not recreate the retired host runtime. Backup/restore for
future Docker data follows [backup operations](backup-restore.md); confirm
current document commands and volume/project names before performing a restore.

## CLI and Verification

Run CLI operations inside the API container so they use the same DB/config:

```bash
sh scripts/local-stack.sh exec -T api agent-kernel --version
sh scripts/local-stack.sh exec -T api agent-kernel agent create --name "Local Agent"
sh scripts/local-stack.sh exec -T api agent-kernel run create <agent-id> --input '{"task":"hello","model":"mock:echo"}'
sh scripts/local-stack.sh exec -T api agent-kernel run queue <run-id>
sh scripts/local-stack.sh exec -T api agent-kernel run inspect <run-id>
```

The continuous Worker processes queued runs; do not start another host Worker.
Host `uv`/Node may still run short-lived lint, typecheck or tests. Browser checks
target Docker port 3000 by default without starting a host Next server. Set
`PLAYWRIGHT_BASE_URL` for another endpoint; `PLAYWRIGHT_MANAGED_SERVER=1` is an
explicit isolated-test exception used by the Web CI job, not normal startup:

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 AGENT_KERNEL_TEST_DOCKER_WEB=1 npm run test:e2e
```

Verification must include actual readiness, Web-to-API proxy access, a queued
mock Run, Loki/Tempo evidence, metrics target health and restart persistence.
See [observability acceptance](observability-completion-plan.md) for separate
fault/SMTP tests. No real-email, live-model, pilot or remote-CI claim is implied.

## Cutover Evidence

2026-11-14 local evidence:

- Confirmed no queued/running legacy Runs, then stopped the verified host API,
  Worker and Next processes and the old `agent-kernel-local-monitoring` project.
  No legacy volumes or databases were deleted during the initial cutover;
  the later authorized file cleanup is recorded below.
- Historical backup: `.agent-kernel/backups/local-experience-before-docker-20261114.tar.gz`
  (0600), verified before cleanup. SHA-256:
  `45dc2371ec8f752f579d370271bd200b85754857c07d21c446959af730cd4249`.
  The archive contained the SQLite DB, objects, logs and private monitoring config.
  It and the legacy source directory were subsequently deleted at the maintainer's
  request, along with the older `.agent-kernel/agent_kernel.db` and the then-empty
  backups directory. This hash is historical evidence, not an available backup.
- `make docker-up`: all **13 services running**. API/Web/PostgreSQL/Redis/Mailpit
  healthchecks pass; functional probes verify the remaining backends. All host
  mappings are loopback-only; PostgreSQL/Redis have no published host ports.
- `AGENT_KERNEL_TEST_DOCKER_LOCAL=1 .venv/bin/pytest -q tests/integration/test_docker_local.py`:
  **4 passed** (actual queue execution, PostgreSQL/pgvector RAG, Web proxy,
  Loki/Tempo data, 7 healthy scrape targets, Grafana and local inbox).
- `AGENT_KERNEL_TEST_DOCKER_WEB=1 npm run test:e2e`: **3 passed**, targeting Docker
  without a host Next server. Desktop 1440px and mobile 390px screenshots checked;
  the real API status is reachable. Existing preview sections remain previews.
- `make docker-down` followed by `make docker-up`: original successful Run,
  indexed document retrieval, Loki records and Tempo trace all remain queryable.
  Redis AOF is enabled. This is clean-restart evidence, not crash-loss/HA proof.
- Current sample IDs are in private `.agent-kernel/docker-local/acceptance-sample.json`.
  These are new Docker acceptance records, not migrated legacy records.
- `AGENT_KERNEL_TEST_PROMTOOL=1 .venv/bin/pytest -q`: **1063 passed, 95 skipped**.
  Opt-in Docker acceptance ran separately above; other backend profiles are not
  silently claimed by skipped tests. Ruff and mypy (**224 source files**) passed;
  Web typecheck and production image build passed. Shell syntax/config checks pass.

The CI workflow now contains the default Docker startup/acceptance steps, but no
commit, push or remote run was performed in this cutover. External SMTP, live
provider behavior and the controlled user pilot remain separate unaccepted gates.

## Subsequent Code Update

On 2026-11-14, `make docker-up` rebuilt and replaced API/Worker/Web with the
PostgreSQL-only working-tree code. Existing database, object, queue and telemetry
volumes were retained. Read-only Docker checks (3 passed) and browser checks
(3 passed) verified the update; existing business-data and object-file digests
are unchanged. The database/object backup location and the transient Loki
readiness observation are recorded in the
[PostgreSQL-only update evidence](postgresql-only.md#active-local-update).
This update did not pull remote changes, commit, push or run remote CI.

## Subsequent Remote Verification

Baseline `8f87473` and CF1 candidate `5952ba7` were later committed/pushed with
authorization. [CI run 43590573645](https://github.com/royliu1105/agent-kernel/actions/runs/43590573645)
passed all four jobs, including a fresh default Docker stack and **4 runtime/Web
proxy tests**, plus the separate **8-test** full observability rehearsal.
This happened on disposable GitHub runners. The review/push did not rebuild,
restart or migrate this machine's active containers; its CF1 code is not deployed.
See the [candidate record](reviews/2026-11-14-cf1-minimal-repair.md) for the exact
SHA, test profiles and remaining gates. Historical cutover evidence above is unchanged.
