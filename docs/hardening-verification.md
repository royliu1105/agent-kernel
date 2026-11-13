# Capability Hardening Verification

This is the historical P0-P5/R1-R10 evidence record. Subsequent N1-N5 bounded
execution, approval continuation and retry-backoff evidence is tracked separately
in the [capability hardening plan](capability-hardening-plan.md). The older green
CI below does not verify later changes.

Date: 2026-11-13. This record covers the P0-P5 batch over baseline
`4684931`. The [canonical plan](capability-hardening-plan.md) owns scope/status.
This is not a new release announcement or production certification.

## Acceptance Checklist

**Reopened 2026-11-13:** the audit at `1efc174` found reproducible defects and
unfulfilled original requirements. The checked historical gates below retain
their evidence, but do not establish acceptance of the remediation. See R1-R10
in the canonical plan. Record new commands/results separately; never relabel
historical results as tests of changed code.

- [x] Resolve R1-R10 and individually record behavioral regression evidence.
- [x] Reconcile all thirteen packages with the original requirements; record implemented scope and explicit limits below.
- [x] Run full local gates on the repaired code, including real backends/deployment (746 passed, no skips).
- [x] Record green remote CI for the repaired implementation SHA (`d65e833`, run 43375236175).
- [x] Final requirement-by-requirement acceptance review within the documented self-hosted scope.

### Historical Gates (Before Audit)

- [ ] Implement all thirteen remaining packages with tests and operator docs (previous blanket acceptance withdrawn).
- [x] Real PostgreSQL/SQLite claim, approval/resume and stale-owner contracts.
- [x] Real Redis admission/queue and native pgvector contracts.
- [x] Disposable database/object restore drill and queue-loss drill.
- [x] HTTP upload/index/retrieve, queued model/tool execution, MCP approval/resume.
- [x] Native Prometheus exposition/config/rule/query validation.
- [x] Final full-suite, lint/type, Web and dependency-audit results recorded below.
- [x] Clean application image build/start and the HTTP rehearsal against it.
- [x] Actual Grafana container load and monitoring-stack scrape rehearsal.
- [x] Green remote CI for implementation `6c9fa92ddc0660c1cfe40453d5f42ad0ed791c51`.
- [ ] Maintainer review of compatibility/security limitations before release.

The historical local implementation/deployment and remote CI gates have evidence.
P5.2 was reopened by the audit; the current remediation and scope review below
now establish its scoped acceptance. Commit/push and CI tracking were explicitly
authorized by the maintainer; no release was authorized. Live-provider execution
is optional and was not enabled. The unchecked release review remains separate
from implementation acceptance.

## Remediation Verification

Baseline: `1efc174`. Repairs are implemented and the final local full gate passed.
Implementation `d65e833af7f59583c6830a8d1a710e00b02ffc1e` also passed remote CI
43375236175. The separate requirement review below accepts the documented scope;
earlier green CI is not evidence for these changes. The
maintainer has authorized committing/pushing this remediation to `origin/master`
and tracking its CI. No tag or release is authorized.

| Item | New evidence | Additional gate, now verified |
| --- | --- | --- |
| R1 | `test_observability_logging_entrypoints.py` exercises configured Uvicorn DB exceptions, Worker top-level exceptions, startup and malformed SDK notifications; raw SQL/prompt/secret sentinels absent. MCP diagnostic tests also assert raw LogRecords are sanitized before plain handlers. | Remote |
| R2 | `test_external_mcp_failures.py` exercises actual SDK transport: redirects send once, HTTP failures preserve caller, later calls reconnect, catalog drift fails closed, pending/canceled calls are not replayed. | Remote |
| R3 | `test_openai_runtime_contract.py` uses the actual adapter/runtime with HTTP-only fixtures. Correct call IDs/output/reasoning, transient and permanent classification, bounded synthesis retries, exactly one tool execution, usage and zero unsafe fallback calls verified. | Remote |
| R4 | Three new deadline/heartbeat/late-result tests first failed on baseline, passed after offloading and are included in the full suite. Read-only worker threads may finish after timeout but cannot complete the failed Run. | Remote |
| R5 | Real multi-client Redis and dual-API quota tests passed. Independent review found canonical-number parsing could cause partial charging; six malformed-counter cases now assert no other bucket is charged. TTL-zero denial also fixed. | Remote |
| R6 | `test_usage_attribution.py`, `test_usage_migration.py`, readiness/operational-signal and `test_embedding_bootstrap.py` verify trusted principal/model attribution, cross-workspace denial, fresh/legacy SQLite/PostgreSQL migration, selected real embedding adapter and retryable embedding failure. | Remote |
| R7 | Native Prometheus exposition/rules/query tests passed, including firing cases for all 15 rules. Actual scrape and Grafana provisioning passed for 24 panels; upper/lower browser screenshots inspected, no page errors. | Remote |
| R8 | Actual stdio/HTTP tool/resource/prompt deadlines plus runtime approval/denial/audit and OpenAPI binding policy tests passed. Central and binding policy compose conservatively. | Remote |
| R9 | Actual faulty Redis queue attached to Worker: one observed dequeue failure and three successful DB-polled runs. Real pg_dump/restore, matching objects, corruption detection and native vector retrieval passed. Fixture extended to include nonempty model usage, then restore test passed again. | Remote |
| R10 local | Full final `pytest`: **746 passed, no skips** with PostgreSQL, Redis, restore, promtool, HTTP and monitoring enabled. Ruff, mypy (207 files), release eval (3/3 + 4/4 + 2/2 + timelines 7/7), Web types/build and Chromium (2/2) passed. Quick synthetic burst: 25 succeeded, 0 failed/remaining. | Remote CI, final acceptance |

Final application images (after the limiter follow-up): API
`sha256:c0b56b54a8f9c517877e86542382bdd747252da01aee51a75ad4b207ca567e06`,
Worker `sha256:09bf3d1258f71cca270188acc2ef1a8dbb0c2a28e1a429b508e40de15b110008`.
New disposable project: `agent-kernel-remediation`; dedicated test PostgreSQL
and Redis used loopback ports 55488 and 56488. No application database was used.
Build cache was used; this is not a cold-cache benchmark.

Final full-gate environment (synthetic Grafana password supplied privately):

```bash
AGENT_KERNEL_TEST_POSTGRES_URL=postgresql+psycopg://agent_kernel:drill-only@127.0.0.1:55488/agent_kernel_test \
AGENT_KERNEL_TEST_REDIS_URL=redis://127.0.0.1:56488/15 \
AGENT_KERNEL_ALLOW_BACKEND_DRILL=1 \
AGENT_KERNEL_TEST_PG_TOOLS_CONTAINER=agent-kernel-drill-remediation-pg \
AGENT_KERNEL_TEST_PROMTOOL=1 \
AGENT_KERNEL_TEST_DEPLOYMENT_URL=http://127.0.0.1:28080 \
AGENT_KERNEL_TEST_MONITORING=1 \
AGENT_KERNEL_TEST_COMPOSE_PROJECT=agent-kernel-remediation \
AGENT_KERNEL_TEST_GRAFANA_PASSWORD="$AGENT_KERNEL_GRAFANA_ADMIN_PASSWORD" \
uv run pytest -q --tb=short
```

Runtime boundaries retained: no paid model request was made; HTTP fixtures prove
protocol behavior, not upstream availability or model quality. Provider readiness
validates configuration, not credentials with the vendor. Costs are estimates,
including unknown legacy attribution, not billing. Native tool follow-up retries
stay on the same provider/model and never replay tools; cross-provider follow-up
fallback and a general reasoning/tool loop are not claimed. Existing single-tool
loop and approval-resume boundaries remain documented in behavior-regression.md.
No dependency lockfile changed and no new online vulnerability audit is claimed.

The first real Redis attempt was blocked by the execution sandbox's loopback
network policy, not skipped or counted as passed; the same tests passed with
authorized access to disposable containers. A first PostgreSQL migration fixture
incorrectly found public's Alembic version table; it was corrected to create an
isolated version table and assert physical table ownership before inserting data.
Only the dedicated test database was involved.

An intermediate integration run reported seven failures (693 passed, four
deployment skips): follow-up retry count expectations, native-history wire
assertions, and plain-handler logging tests under globally configured logging.
Those assertions were reconciled with the intended behavior without removing
privacy, side-effect-count or protocol checks. Subsequent local runs progressed
to 740 and finally 746 passing tests with all deployment opt-ins enabled.

Cleanup was verified after the local gates: the disposable
`agent-kernel-remediation` Compose project and its volumes, dedicated
`agent-kernel-drill-remediation-pg` / `agent-kernel-drill-remediation-redis`
containers, and temporary monitoring-token file were removed. No user-owned
application database or volume was removed. Remote CI and the separate final
scope review passed as recorded below; release approval remains separate.
The changed-file pre-commit checks passed (YAML, EOF/whitespace, Ruff lint and
format). TOML and the unchanged Compose override had no matching files.

## Remediation Remote Verification

Implementation: `d65e833af7f59583c6830a8d1a710e00b02ffc1e`.
[CI run 43375236175](https://github.com/royliu1105/agent-kernel/actions/runs/43375236175)
completed successfully on 2026-11-13. No CI-only repair or waived assertion was
needed for this implementation.

| Job | Verified result |
| --- | --- |
| Python | SQLite/PostgreSQL migrations through 0018, Ruff, mypy (207 files), main suite **741 passed / 4 skipped**, independent guarded PostgreSQL restore **1 passed**, release eval gates 3/3 + 4/4 + 2/2 + timelines 7/7. |
| Web | Typecheck, production build and **2 Chromium tests passed**. |
| Compose | Built and started the application and monitoring stack; HTTP deployment **1 passed**, monitoring deployment **3 passed**, temporary deployment removed successfully. |

The four main-suite skips are exactly the HTTP deployment test and three
monitoring deployment tests exercised by Compose. The restore test is excluded
from the main invocation and executed in its own guarded step. Thus the workflow
exercises the same 746 pytest cases as the no-skip local run across separate
jobs/steps; no deployment test is waived. Protocol fixtures remain fixtures:
green CI does not mean a paid provider call or a live quality/cost benchmark ran.
Existing Action Node-runtime deprecations and runner-image notices are maintenance
items, not failed gates. No tag or GitHub release was created.

The evidence-update commit changes documentation only. This record identifies
the tested implementation SHA; it does not try to embed its own commit hash.

## Final Scope Review

Date: 2026-11-13. Reviewed implementation: `d65e833`. A separate read-only review
compared the maintainer's original capability plan, the canonical package mapping,
implementation paths and behavioral test assertions. No required-scope blocker
was found. The reviewer did not rerun the suite; local results and verified CI
logs above are the execution evidence. Acceptance means the documented
self-hosted contracts are implemented and verified, not an independent security
certification, production SLA or authorization to release.

| Package | Accepted behavior and evidence | Limit retained |
| --- | --- | --- |
| P1.2 | Memory/eval ownership, foreign source-run denial, legacy quarantine and trusted runtime scope: [isolation tests](../tests/integration/test_memory_eval_isolation.py). | Auth-disabled local operation is not a multi-tenant boundary. |
| P1.3 | Scoped tool/audit/usage views and atomic workspace/principal/key quotas: [API admission](../tests/integration/test_shared_admission_api.py), [real Redis](../tests/integration/test_real_redis_contract.py), [usage](../tests/integration/test_usage_attribution.py). | Standalone Redis fixed-window admission, not Redis Cluster or billing. |
| P2.1 | Claims, lease renewal, stale-owner fences, nonblocking retrieval deadlines: [ownership](../tests/integration/test_execution_ownership.py), [deadline regressions](../tests/integration/test_rag_execution_deadlines.py). | Timed-out read-only threads may finish; late run writes remain fenced. |
| P2.2 | Idempotent approval decisions, exclusive resume, conservative crash recovery: [ownership/concurrency](../tests/integration/test_execution_ownership.py), [cancellation](../tests/integration/test_execution_cancellation.py). | No exactly-once external effects or blind uncertain-write replay. |
| P0.1 | Configured readiness, low-cardinality metrics, entry-point privacy and authorized attribution: [logging](../tests/integration/test_observability_logging_entrypoints.py), [signals](../tests/integration/test_observability_operational_signals.py), [usage migration](../tests/integration/test_usage_migration.py). | Provider readiness validates configuration; legacy usage has unknown attribution. |
| P0.2 | 24 dashboard panels and 15 alerts including queue/approval/cost: [native rules/queries](../tests/integration/test_observability_prometheus.py), [deployed monitoring](../tests/integration/test_monitoring_deployment.py). | Templates require workload-specific thresholds and receivers. |
| P3.1 | Governed stdio tools, metadata/SDK-log sanitization, lifecycle/deadline contracts: [MCP](../tests/integration/test_external_mcp.py), [failures](../tests/integration/test_external_mcp_failures.py). | Operator-approved processes, not an OS sandbox. |
| P3.2 | Streamable HTTP tools/resources/prompts with policy, approval, audit, cancellation and single-send recovery: same MCP suites plus [bootstrap](../tests/integration/test_external_bootstrap.py). | No arbitrary endpoints, OAuth flow or automatic failed-write replay. |
| P3.3 | Reviewed OpenAPI bindings, per-tool policy/timeouts/retry eligibility and idempotency identity: [OpenAPI contracts](../tests/integration/test_external_openapi.py). | Remote service must enforce its own idempotency contract. |
| P4.1 | Native vector dimensions/migrations/scoped retrieval, Redis hints/admission and DB-authoritative execution: [pgvector](../tests/integration/test_real_pgvector_backend_contract.py), [real Redis](../tests/integration/test_real_redis_contract.py). | Vector/model changes require reindexing; queue hints are not execution truth. |
| P4.2 | Matched PostgreSQL/local-object/usage restore, corruption detection and actual queue failure fallback: [guarded restore](../tests/integration/test_real_backend_drill.py), [drill implementation](../scripts/backend_drill.py), [cache assessment](backend-operations.md#semantic-cache-assessment). | Cache implementation deferred without fabricated savings; no S3 restore or production RPO/RTO claim. |
| P5.1 | Seven runtime goldens, persisted ordering/correlation and mutation failures, actual OpenAI adapter wire contracts: [timelines](../tests/integration/test_timeline_regression.py), [adapter/runtime](../tests/integration/test_openai_runtime_contract.py). | Protocol fixtures do not prove upstream compatibility or model quality. |
| P5.2 | Bounded opt-in live smoke, nonblocking comparable cost/latency reports and full credential-free gates: [smoke](../scripts/live_provider_smoke.py), [release gate contract](release-eval-gates.md). | Paid smoke was not enabled; no measured live cost/quality baseline. |

P1.1 predates these 13 packages and remains covered by the full regression gate.
Semantic Cache, Milvus, SQLite-to-Postgres data tooling, same-session ordering,
enterprise identity and public SaaS isolation retain their documented deferrals
or exclusions. Acceptance does not include those capabilities.

## Historical Remote Verification

Verified implementation: `6c9fa92ddc0660c1cfe40453d5f42ad0ed791c51`, following
the main hardening commit `ced4a4b22f642ac824b2d2312a8e6464bab6d753`.
[CI run 43362548617](https://github.com/royliu1105/agent-kernel/actions/runs/43362548617)
completed successfully on 2026-11-13:

| Job | Evidence |
| --- | --- |
| Python | SQLite/PostgreSQL migrations, Ruff, mypy; 561 tests passed and 4 deployment tests explicitly skipped for the separate Compose job; independent guarded restore test passed; all release eval gates passed. |
| Web | Typecheck, production build and 2 Chromium smoke tests passed. |
| Compose | Fresh image build/start; HTTP business rehearsal and all 3 live monitoring tests passed; disposable deployment removed. |

Thus the four Python deployment skips are exercised in Compose, not waived.
The PostgreSQL restore test is deliberately excluded from the main invocation
and run separately against the labelled disposable test database. The two CI
fixture regressions are covered with a pre-migrated public schema and native
Linux container permissions. Existing action-runtime deprecation notices and
the Starlette/httpx warning are non-failing maintenance items, not hidden tests.

The follow-up closure commit changes documentation only. This record names the
verified implementation SHA so it remains stable instead of trying to embed a
commit's own hash in itself; the closure commit also runs the same CI workflow.

## Historical Local Environment and Evidence

Backend checks use disposable loopback-only Redis 7 and pgvector PostgreSQL 16
containers, not the project's application database. PostgreSQL tests create
random schemas; restore tests additionally require a dedicated labelled
`agent-kernel-drill-*` container and test database. Redis tests delete only their
generated keys, never FLUSHDB. See [backend operations](backend-operations.md).

Pre-audit local results after MCP/certifi/Next.js updates (not evidence for the
current remediation):

| Gate | Evidence |
| --- | --- |
| Full pytest with PostgreSQL, Redis, restore opt-in, promtool, HTTP and monitoring deployment opt-ins | **566 passed, no skips** after CI fixture corrections, with public schema already migrated. One existing Starlette/httpx deprecation warning. |
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
checks also passed. Earlier temporary API/Worker/MCP processes and test
containers were stopped after their verification. After final acceptance, the
separate `agent-kernel-hardening` Compose project and its temporary volumes,
the labelled restore container and random monitoring credentials were removed.
User-owned containers and application databases were not changed.

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

- First remote attempt: [run 43361454998](https://github.com/royliu1105/agent-kernel/actions/runs/43361454998)
  for `ced4a4b22f642ac824b2d2312a8e6464bab6d753` passed Web and the full Compose
  rehearsal, but Python reported nine failures across three test/CI setup issues.
  Ownership fixtures allowed `public` search-path fallback, so `create_all`
  reused migrated public tables; fixtures now use only their own schema and
  assert physical table ownership. The native promtool container now uses the
  host UID/GID to read private pytest bind mounts on Linux. CI explicitly opts
  into the disposable Redis drill and runs the PostgreSQL restore contract in
  its separate guarded step. None of these fixes weakens runtime permissions or
  drill safety checks. The corrected SHA passed the green run recorded above.
- Earlier PyPI/Grafana download failures were resolved by retrying the official
  sources, without changing proxy/VPN settings, adding mirrors or bypassing TLS.
  Both application and Grafana deployment gates now pass locally.
- The previously green
  [run 31122498218](https://github.com/royliu1105/agent-kernel/actions/runs/31122498218)
  covers baseline `4684931` only. Batch acceptance uses the implementation run
  above, not that historical evidence. No tag/release is authorized.
- No paid provider request, measured live-model cost baseline, production
  throughput/RPO/RTO, S3 restore or exactly-once external effects are claimed.
- Workspace-scoped APIs are for reviewed self-hosted deployment, not an audited
  public SaaS security boundary. Web SSO/admin workflows, MCP OS sandboxing and
  same-session ordering remain outside this batch's accepted scope.
