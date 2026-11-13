# Capability Hardening Verification

Date: 2026-11-13. This record covers the P0-P5 batch over baseline
`4684931`. The [canonical plan](capability-hardening-plan.md) owns scope/status.
This is not a new release announcement or production certification.

## Acceptance Checklist

- [x] Implement all thirteen remaining packages with tests and operator docs.
- [x] Real PostgreSQL/SQLite claim, approval/resume and stale-owner contracts.
- [x] Real Redis admission/queue and native pgvector contracts.
- [x] Disposable database/object restore drill and queue-loss drill.
- [x] HTTP upload/index/retrieve, queued model/tool execution, MCP approval/resume.
- [x] Native Prometheus exposition/config/rule/query validation.
- [x] Final full-suite, lint/type, Web and dependency-audit results recorded below.
- [x] Clean application image build/start and the HTTP rehearsal against it.
- [x] Actual Grafana container load and monitoring-stack scrape rehearsal.
- [ ] Green remote CI for the eventual committed SHA.
- [ ] Maintainer review of compatibility/security limitations before release.

The local implementation/deployment gates have evidence. P5.2 still awaits the
actual committed SHA's remote CI result. Commit/push and CI tracking were
explicitly authorized by the maintainer on 2026-11-13; no release was authorized.
Live-provider execution is optional and was not enabled.

## Local Environment and Evidence

Backend checks use disposable loopback-only Redis 7 and pgvector PostgreSQL 16
containers, not the project's application database. PostgreSQL tests create
random schemas; restore tests additionally require a dedicated labelled
`agent-kernel-drill-*` container and test database. Redis tests delete only their
generated keys, never FLUSHDB. See [backend operations](backend-operations.md).

Final local results after MCP/certifi/Next.js updates:

| Gate | Evidence |
| --- | --- |
| Full pytest with PostgreSQL, Redis, restore opt-in, promtool, HTTP and monitoring deployment opt-ins | **564 passed, no skips**. One existing Starlette/httpx deprecation warning. |
| Ruff lint | Passed across the repository. |
| mypy | Passed, 194 source files. |
| `make release-eval` | RAG smoke 3/3, release RAG 4/4, tool eval tests 2/2, runtime timelines 7/7. |
| `make release-load-soak` | Quick synthetic burst: 25 requested/processed/succeeded, 0 failed, 0 queued remaining. Not a production throughput claim. |
| `npm run lint` and `npm run build` | Passed with Next.js 16.4.6. |
| `npm run test:e2e` | 2 Chromium tests passed with the upgraded Web dependencies. |
| Python/npm dependency audits | No known Python vulnerabilities; npm 0 vulnerabilities. Scope in dependency-audit.md. |
| Native Prometheus checks | 3/3 passed: exposition, config/alert rules and all 14 dashboard queries; also included in full pytest. |
| Real API/Worker monitor ports | Both returned 401 without the dedicated token and 200 with valid Prometheus exposition when authorized. |
| Worker process restart | Queued a run with Worker stopped; a new Worker process completed it once; another process processed 0 runs. Contiguous audit events verified. |
| Compose application deployment | Fresh API/Worker image build, empty project volumes, Alembic startup to 0017, and full HTTP rehearsal passed. |
| Monitoring deployment | 3 tests passed against real services: scraped application samples, 14 panel queries, 9 loaded alerts, Grafana provisioning/data source/auth, Worker restart supervision. |
| Grafana browser | Login and upper/lower dashboard rendering passed in Chromium; no page errors; inspected screenshots. |
| Controlled faults | Worker target-down alert reached `firing` after its 2m hold; PostgreSQL outage produced readiness 503/probe 0. With restart supervision, database recovery restored Worker automatically, readiness 200/probe 1, and cleared the alert. Business HTTP smoke passed again. |
| Live smoke with opt-in disabled | Explicit `skipped`, no provider request or invented cost/latency evidence. |
| `git diff --check` | Passed. |

Focused contracts additionally prove cancellation-resistant late results are
fenced on SQLite/PostgreSQL, including when durable lease invalidation fails.
Independent API instances share Redis quotas and reject backend failures before
agent mutations. These local checks do not substitute for the remote CI gate.

Formatting: changed Python files pass Ruff formatting. A repository-wide format
check also found pre-existing style drift in untouched files; those unrelated
files were not mechanically rewritten. The existing CI gate uses `ruff check`,
which passes. This distinction is not a claim that global format-check passed.
After formatting and documentation finalization, 36 affected documentation,
runtime, recovery, Worker CLI and retrieval tests passed again; mypy and diff
checks also passed. All temporary API/Worker/MCP processes and the three test
containers were stopped after verification. No application database was changed.

The first HTTP rehearsal used separate host API/Worker processes. The follow-up
used rebuilt application images, fresh Compose volumes, PostgreSQL/Redis and the
synthetic stdio MCP server. Models/embeddings were credential-free fixtures.
BuildKit dependency caching was enabled; this is not a cold-cache timing claim.
It validates HTTP/container integration, not real model quality or production
performance. Local image IDs: API `sha256:8d071dd81b3ac93d76f72c757667fda4e21a134dbe614a7db8fca8bda45e84ab`,
Worker `sha256:c78edc79fbfa4f77128983610ff3e28a78f895ea4b72be0e0dd03ae11f5348b8`.

The fault drill exposed a missing default Worker restart policy, now fixed with
`restart: unless-stopped`. Only the database was manually restarted in the final
recovery attempt; Docker restored the Worker. This does not automatically retry
uncertain in-flight Runs. See [execution ownership](execution-ownership.md).

## Repeat the Full Backend Gate

Start the dedicated services described in backend operations, then:

```bash
export AGENT_KERNEL_TEST_POSTGRES_URL=postgresql+psycopg://agent_kernel:drill-only@127.0.0.1:15432/agent_kernel_test
export AGENT_KERNEL_TEST_REDIS_URL=redis://127.0.0.1:16379/15
export AGENT_KERNEL_ALLOW_BACKEND_DRILL=1
export AGENT_KERNEL_TEST_PG_TOOLS_CONTAINER=agent-kernel-drill-postgres-p4
export AGENT_KERNEL_TEST_PROMTOOL=1
uv sync --locked --dev
uv run ruff check .
uv run mypy .
uv run pytest -q --tb=short
make release-eval
npm ci
npm run lint
npm run build
npm run test:e2e
git diff --check
```

The HTTP suite skips unless `AGENT_KERNEL_TEST_DEPLOYMENT_URL` points to a
disposable localhost deployment with the fixture MCP binding. A configured
unreachable service must fail, never be converted to a skip.
For a no-skip full run, also enable the monitoring deployment below and set its
test variables before pytest. Its three tests otherwise skip explicitly.

## Clean Container Rehearsal

Only use a new disposable project name; these commands remove that project's
volumes. Check that the selected ports and project name are unused first.
The checked-in overlay enables an unscoped synthetic tool for local testing;
it is not a production external-tool configuration. No real API keys are needed.
Compose 2.24.4+ is required for `!override`. The smoke overlay binds host ports
to loopback, fixes the API's container port at 8000, and treats
`AGENT_KERNEL_API_PORT` as the published host port. The YAML hook validates custom
tag syntax; native `docker compose config` validates the merged semantics.

```bash
export AGENT_KERNEL_API_PORT=28080
export AGENT_KERNEL_POSTGRES_PORT=25432
export AGENT_KERNEL_REDIS_PORT=26379
export AGENT_KERNEL_API_KEY_AUTH_ENABLED=false
export AGENT_KERNEL_RUN_QUEUE_BACKEND=redis
export OPENAI_API_KEY=
docker compose -p agent-kernel-hardening -f docker-compose.yml -f deploy/hardening-smoke.compose.yml config --quiet
docker compose -p agent-kernel-hardening -f docker-compose.yml -f deploy/hardening-smoke.compose.yml up --build --detach --wait --wait-timeout 180 api worker
AGENT_KERNEL_TEST_DEPLOYMENT_URL=http://127.0.0.1:28080 uv run pytest -q tests/integration/test_self_hosted_hardening.py
docker compose -p agent-kernel-hardening -f docker-compose.yml -f deploy/hardening-smoke.compose.yml logs --no-color --tail 150
docker compose -p agent-kernel-hardening -f docker-compose.yml -f deploy/hardening-smoke.compose.yml down --volumes --remove-orphans
```

For the combined monitoring rehearsal, prepare private random credentials as
described in [observability operations](observability-operations.md). Add
`-f deploy/observability/docker-compose.yml --profile observability` to every
Compose command above and include `prometheus blackbox grafana` in `up`. Run the
HTTP suite first so application samples exist, then:

```bash
AGENT_KERNEL_TEST_MONITORING=1 \
AGENT_KERNEL_TEST_GRAFANA_PASSWORD="$AGENT_KERNEL_GRAFANA_ADMIN_PASSWORD" \
uv run pytest -q tests/integration/test_monitoring_deployment.py
```

Optional endpoint overrides: `AGENT_KERNEL_TEST_PROMETHEUS_URL` and
`AGENT_KERNEL_TEST_GRAFANA_URL`, defaulting to localhost ports 9090 and 3090.
Tests refuse non-loopback HTTP destinations. CI runs the image/HTTP/monitoring
path with synthetic isolated credentials; a historical configuration-only
green Compose job does not satisfy this gate.

## Open Gates and Limits

- Earlier PyPI/Grafana download failures were resolved by retrying the official
  sources, without changing proxy/VPN settings, adding mirrors or bypassing TLS.
  Both application and Grafana deployment gates now pass locally.
- Remote CI evidence is pending the authorized commit/push. The previously
  green [run 31122498218](https://github.com/royliu1105/agent-kernel/actions/runs/31122498218)
  covers baseline `4684931` only, not this batch. No tag/release is authorized.
- No paid provider request, measured live-model cost baseline, production
  throughput/RPO/RTO, S3 restore or exactly-once external effects are claimed.
- Workspace-scoped APIs are for reviewed self-hosted deployment, not an audited
  public SaaS security boundary. Web SSO/admin workflows, MCP OS sandboxing and
  same-session ordering remain outside this batch's accepted scope.
