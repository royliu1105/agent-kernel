# Post-v1.0 Capability Hardening Plan

## Status and Authority

Status: the authorized P0-P5 implementation batch is accepted within the scoped
guarantees below. Implementation commit `6c9fa92ddc0660c1cfe40453d5f42ad0ed791c51`
passed [remote CI 43362548617](https://github.com/royliu1105/agent-kernel/actions/runs/43362548617)
on 2026-11-13, including Python, Web and the live Compose rehearsal. Per-package
evidence and explicit deferrals are recorded below. Retain the Python backend
and TypeScript Web stack. This is not a new release.

Batch execution authorization (2026-11-13): the maintainer requested continuous
implementation of the remaining 13 packages and approved parallel sub-agents.
Local gates were checked per increment; remote CI did not stop unrelated
implementation in this batch and has now passed the final acceptance gate.
This supersedes instructions below to wait for P1.1 CI before starting P1.2.
Follow-up authorization on 2026-11-13 permits commit, push to `origin/master`,
and tracking/fixing the resulting CI. It does not authorize a tag or release.
Parent agent owns isolation,
execution reliability, integration and final verification; delegated work owns
observability, external tools, backend drills and regression tooling separately.

This is the canonical execution plan for the capability completion work after
v1.0. It translates the maintainer-supplied P0-P5 capability plan into testable
work packages. Keep the original P identifiers for traceability; their numbers
do not determine execution order.

The current repository remains the only implementation to maintain. Archived
implementations may inform a task, but are not runtime dependencies or a second
maintenance branch. Port behavior with tests, not directories or build outputs.

The Day 1-90 plans remain historical delivery records. Their completed
foundation tasks do not imply that the stronger guarantees below are complete.
Update this document when scope or status changes; other planning documents
link here instead of keeping a separate task list.

## Verified Starting Point

Repository audit date: 2026-11-13. Baseline commit: `4684931`.

| Area | Existing baseline | Remaining gap |
| --- | --- | --- |
| P0 Observability | Process-local metrics, structured logs, field-name redaction, OTel configuration, run usage/cost records. | Dashboards, alerts, dependency readiness, broader redaction coverage, bounded metrics aggregation, scoped cost views. |
| P1 Isolation | API keys, route permissions, Agent/Run scope, Approval scope derived from Run. | Knowledge/document/chunk/embedding/ingestion, memory, eval and operational resource scope; rate limiting. |
| P2 Reliability | Persisted runs/events, polling worker, lease repository, expired-lease recovery, approval resume. | Lease acquisition/renewal in the worker execution path, atomic claims, stale-owner write protection, concurrent/crash recovery guarantees. |
| P3 External tools | Registry, schema validation, timeout, policy, approval and audit primitives. | MCP transports/resources/prompts, metadata sanitization, OpenAPI generation and external-tool retry contracts. |
| P4 Backends | pgvector path/migration, object storage adapters, Redis queue adapter, backup guide. | Real-backend contract coverage, Redis runtime integration, restore/queue drills and cache benefit assessment. |
| P5 Regression | Credential-free eval/smoke gates, burst script, recorded model-response replay, some event assertions. | Golden timeline replay, opt-in live provider smoke, cost/latency trend reports and expanded gates. |

The audit ran 96 relevant existing tests successfully, with one existing
Starlette deprecation warning. This is baseline evidence, not acceptance of the
missing capabilities or a new full-release verification.

Historical baseline evidence anchors (the files now contain the hardening changes):

- [Object scope inventory](auth-rbac.md#object-scope).
- [Worker execution](../packages/kernel-runtime/src/kernel_runtime/worker.py):
  polls the database and invokes execution without acquiring a lease.
- [Storage repositories](../packages/kernel-storage/src/kernel_storage/repositories.py):
  lease methods exist, but run completion does not enforce ownership.
- [API](../apps/api/src/agent_kernel_api/main.py): health returns a static result;
  knowledge/eval queries lack workspace filtering.
- [Replay provider](../packages/kernel-providers/src/kernel_providers/replay.py):
  recorded model responses are not full runtime timeline replay.

## Delivery Order and Progress

Start with P1 isolation and P2 execution ownership because they affect data
access and duplicate side effects. P0 operational visibility follows. P5 tests
must accompany each change; the final P5 work consolidates them into release
gates. Pull real-backend tests from P4 forward whenever P1 or P2 needs them.

No new calendar deadline or version bump is implied by this plan. Track work
by the stable IDs below. Only the active task needs a detailed execution plan.

| Order | ID | Work package | Status |
| --- | --- | --- | --- |
| 1 | P1.1 | Knowledge/RAG workspace isolation, including `kb_search`. | Accepted; local and remote isolation/migration gates passed |
| 2 | P1.2 | Memory and eval ownership, repository/API isolation. | Accepted; local and remote contracts passed |
| 3 | P1.3 | Tool/audit/operational scope review, scoped summaries, rate-limit contract and enforcement. | Accepted; shared Redis/API and isolation contracts passed |
| 4 | P2.1 | Atomic run claims, execution lease lifecycle, fencing or equivalent stale-owner protection. | Accepted; PostgreSQL/SQLite concurrency and cancellation contracts passed |
| 5 | P2.2 | Approval decision/resume concurrency, crash recovery, side-effect replay boundaries. | Accepted; concurrency/recovery contracts passed |
| 6 | P0.1 | Readiness, metrics inventory/aggregation, log/trace redaction, cost attribution. | Accepted; readiness/OTel/metrics contracts passed; cost estimates are not billing |
| 7 | P0.2 | Grafana dashboard, Prometheus scrape/alert templates, operator instructions. | Accepted; native checks, live Grafana/scrape and local fault/recovery rehearsal passed |
| 8 | P3.1 | External-tool contract, metadata sanitizer, MCP stdio and fixture server. | Accepted; API/Worker integration and local/remote contracts passed |
| 9 | P3.2 | MCP Streamable HTTP, resources/prompts with policy checks. | Accepted; real-transport fixture contracts passed |
| 10 | P3.3 | OpenAPI tool generation, fixture and per-tool retry/idempotency policy. | Accepted; security/HTTP contracts passed |
| 11 | P4.1 | Consolidate pgvector contracts and Redis queue/rate-limit/coordination integration. | Accepted; real PostgreSQL/Redis contracts passed |
| 12 | P4.2 | Backup/restore and queue drills; documented Semantic Cache benefit assessment. | Accepted; local/remote drills passed; cache implementation remains explicitly deferred |
| 13 | P5.1 | Golden approval/tool/retry/fallback/recovery timelines and failure explanations. | Accepted; actual-runtime timeline gate passed locally and in CI |
| 14 | P5.2 | Opt-in live provider smoke, non-blocking cost/latency reports, full closure. | Accepted; tooling, local deployment and remote CI passed; paid live request not enabled |

P1.3 must state whether limits are process-local or shared. If a shared guarantee
is required, bring the Redis work forward; do not mark a multi-instance limit
complete based on an in-process implementation. Evaluate same-session
serialization in P2 and record its required behavior or explicit deferral.

## Batch Implementation Record

Date: 2026-11-13. Changes remain unreleased; the authorized commit/push and remote
CI verification are complete. Implementation is in `ced4a4b`, followed by CI
fixture corrections in `6c9fa92`; the latter is the verified implementation SHA.
The thirteen remaining work packages were implemented as one coordinated batch,
not thirteen independent claims of production readiness.

- P1.2/P1.3: migration `0016_scope_memory_evals`, trusted workspace propagation,
  source-run validation, scoped tool/events/usage, disabled-workspace and removed
  membership rejection, and shared Redis admission with 429/503 semantics.
- P2: migration `0017_unique_active_lease`, serialized claims, heartbeat,
  stale-owner fences for state/results/events/usage, idempotent approvals and
  exclusive resume. Canceled work is fenced before waiting for cleanup, even if
  a provider/tool suppresses cancellation. Database invalidation failure also
  revokes local write ownership. See [execution ownership](execution-ownership.md).
- P0: bounded metrics, seconds-based production histograms, dependency readiness,
  separate monitor authentication, redacted runtime spans with persisted trace
  IDs, 14 Grafana panels and 9 alerts. See [operations](observability-operations.md).
- P3: official MCP SDK stdio/Streamable HTTP, tools/resources/prompts, reviewed
  OpenAPI bindings, DNS-pinned HTTP transport and lifecycle registration in both
  API and Worker. External writes do not auto-retry. See [external tools](external-tools.md).
- P4: bounded Redis queue hints plus unconditional DB polling, real multi-client
  admission checks, native pgvector contracts, matched DB/object restore and
  queue-loss drills. See [backend operations](backend-operations.md).
- P5: seven actual-runtime golden scenarios, bounded opt-in live smoke, offline
  cost/latency comparison and a new HTTP deployment rehearsal. The Compose CI
  job now builds/starts API and Worker before testing, not only parsing YAML.
  See [behavior regression](behavior-regression.md).
- Security follow-up: audit-discovered MCP/certifi and Next.js dependency
  findings were addressed within existing major versions, with fresh audits
  and compatibility checks recorded in [dependency audit](dependency-audit.md).

The authoritative command/results and open-gate checklist are in
[hardening verification](hardening-verification.md). A missing remote CI run or
failed image download is not a passed gate. No paid live-model test was enabled.
Final local full-suite result: **566 passed, no skips**, with real PostgreSQL,
Redis, restore, native promtool, container HTTP and monitoring deployment checks
enabled. Ruff, mypy (194 files), release evals, Web type/build/browser checks and
updated dependency audits passed. Clean application images and live Grafana
passed on retry, including real alert firing/clearing and automatic Worker
process recovery after database outage. The Worker now has Compose restart
supervision. Remote Python, Web and Compose gates passed for the implementation
SHA linked above, closing P5.2. A separate maintainer compatibility/security
review and explicit authorization are still required before any release.

## Completed Increment Record: P1.1 Knowledge and RAG Isolation

Goal: an authenticated caller or run in workspace A cannot discover, read,
change, index or retrieve knowledge owned by workspace B.

Implementation scope:

- [x] Update the existing security and RAG specs with trusted workspace context,
  ownership derivation, denial behavior and legacy-data handling.
- [x] Add knowledge-base ownership through a new Alembic migration. Do not edit
  released migrations. Derive document/chunk/embedding/ingestion ownership
  through the knowledge base where practical.
- [x] Require explicit scope on authenticated repository/API operations,
  including direct child-resource lookups and all supported mutations.
- [x] Carry trusted run workspace context through API, CLI/worker execution and
  both explicit/native `kb_search` tool paths. Never trust a model-supplied
  workspace identifier or mutable global current-workspace state.
- [x] Check ownership before reading/writing object storage, embedding calls,
  indexing or retrieval. Scope results, citations and error responses too.
- [x] Keep legacy unowned data inaccessible to authenticated workspaces until
  an operator explicitly assigns ownership. Document a safe assignment path;
  never silently assign all existing data to the first caller.
- [x] Preserve the documented auth-disabled local SQLite/mock workflow. Local
  operator access must not be presented as a workspace-isolated public API.
- [x] Add cross-workspace repository, API and runtime tests and update the
  resource-scope matrix and upgrade instructions.

Primary code boundaries:

- `packages/kernel-core`: resource ownership models.
- `packages/kernel-storage`: migration, records and scoped queries.
- `packages/kernel-rag`: ingestion, retrieval, citations and `kb_search`.
- `packages/kernel-runtime` and `packages/kernel-tools`: trusted execution
  context plumbing; keep this narrowly scoped to the required boundary.
- `apps/api`, `apps/cli`, `apps/worker`: scope propagation and operator behavior.

Acceptance checklist:

- [x] Workspace A/B tests cover list/detail, create/upload, supported updates
  and deletes, ingest/chunk/embed/retrieve and direct child IDs. Do not add
  unsupported CRUD endpoints solely to satisfy a matrix.
- [x] Cross-workspace requests reveal no resource contents, citations or
  existence details and trigger no storage/provider side effects.
- [x] Forged knowledge-base IDs fail through both direct API retrieval and
  explicit/provider-native tool execution, including queued worker runs.
- [x] Role denial and workspace denial remain separate tested checks.
- [x] Legacy-data upgrades and fresh databases pass migration checks on SQLite
  and PostgreSQL; real pgvector retrieval tests verify workspace isolation.
- [x] Existing quickstart, RAG, approval and runtime regressions still pass.
- [x] Relevant local lint/type checks pass; commands/results recorded below.
- [x] Remote CI passes for the committed changes: run `43362548617` for
  `6c9fa92`, linked above; P1.1 is accepted with the full batch.

Use the existing auth, RAG integration, retrieval, `kb_search`, runtime worker,
provider-tool and migration suites as starting points. New tests should prove
denial and side-effect prevention, not merely the presence of `workspace_id`.

## P1.1 Implementation and Verification Record

Date: 2026-11-13. Historical increment checkpoint: no commit/push had yet been
performed at that point. The subsequent authorized batch commit/push and CI are
recorded above; no tag or release was performed.

Implemented:

- New migration `0015_scope_knowledge_bases`, domain/record/response ownership,
  scoped repositories for KBs and all child resources.
- All existing knowledge API routes derive workspace from the authenticated
  key. CLI JSON/upload requests accept `AGENT_KERNEL_API_KEY`.
- Immutable tool execution context is built from persisted Run ownership.
  Explicit/native tools, queued workers and approval resume share this path.
- Canonical document and parsed-artifact namespace checks prevent cross-KB
  source reads. Embedding references and citations validate parent consistency.
- Native tool errors now persist Run failure instead of leaving it running.
  Inaccessible KB errors are non-retryable.
- Specs, scope matrix, configuration and offline legacy assignment instructions
  updated. No language migration, new CRUD endpoints, memory/eval scoping or
  worker lease integration was included.

Local evidence:

| Command | Result |
| --- | --- |
| `AGENT_KERNEL_TEST_POSTGRES_URL=<temporary-test-db> .venv/bin/pytest -q --tb=short` | 352 passed, no skips; one existing Starlette/httpx deprecation warning. Without the opt-in variable: 350 passed, 2 skipped. |
| `DATABASE_URL=<temporary-test-db> .venv/bin/alembic upgrade head` | Fresh real PostgreSQL/pgvector upgrade to `0015_scope_knowledge_bases` passed. |
| PostgreSQL contract suite | 2/2 passed on `pgvector/pgvector:pg16`, covering fresh/legacy upgrades and scoped native vector search. Also passed in the full suite with public schema already migrated, matching CI setup. |
| `.venv/bin/pytest -q tests/unit/test_migrations.py` | 4 passed, including fresh SQLite and legacy KB/document preservation, explicit ownership assignment and downgrade/re-upgrade. |
| `.venv/bin/ruff check .` | Passed. |
| `.venv/bin/mypy .` | Passed, 141 source files. |
| `.venv/bin/agent-kernel eval report evals/rag-smoke.json` | 3/3 passed. |
| `.venv/bin/agent-kernel eval report evals/release-rag-gate.json` | 4/4 passed. |
| `npm run lint` | Passed. |
| `npm run build` | Passed. |
| `docker compose config --quiet` | Passed; configuration validation only, not a running-backend check. |
| `git diff --check` | Passed. |

Environment and remaining acceptance evidence:

- Initial Docker HTTP 500 errors were resolved after the maintainer restarted
  Docker Desktop. Verification used a temporary localhost-only pgvector
  container with tmpfs storage, not the project database. After tests, both
  public KB row count and remaining test-schema count were zero. The container
  was stopped and automatically removed.
- CI now supplies `AGENT_KERNEL_TEST_POSTGRES_URL` so the two real-backend
  contracts run rather than skip. It tests random disposable schemas, isolated
  Alembic history, native vector retrieval and fresh/legacy migrations.
- At this earlier checkpoint, the changed branch had not been pushed. The
  subsequent green batch CI linked above now supplies the missing evidence;
  historical baseline CI and local skips were not substituted for that gate.
- At this earlier checkpoint, P1.2 and operational scoping had not started.
  The later batch authorization above superseded the sequential CI wait; those
  implementations and their current acceptance evidence are recorded above.

## Acceptance for the Remaining Work

| Area | Required proof before closure |
| --- | --- |
| P1 | Every core resource has direct or derived ownership; A/B list/detail/mutation and tool-bypass tests pass; operational summaries and limits have explicit scope. Document self-hosted workspace semantics. |
| P2 | Concurrent processes cannot both claim the same runnable execution; expired owners cannot commit state, results or events; heartbeat/recovery races and approval retries are tested on PostgreSQL. External side effects need their own idempotency contract; database fencing alone is not exactly-once execution. |
| P0 | Readiness distinguishes required/optional dependencies; metrics have documented names, units, buckets and bounded low-cardinality storage; sensitive prompts/arguments/results/secrets are excluded or redacted across logs/traces. Cost attribution is workspace-authorized, not high-cardinality metrics labels. Dashboard queries and alerts are validated against actual exported metrics. |
| P3 | External calls pass the same policy/approval/audit checks as built-ins; untrusted metadata cannot set trusted policy; transport/process credentials and lifecycles have explicit boundaries; non-idempotent writes are not automatically retried. MCP and OpenAPI fixtures cover success, denial, timeout and failure. |
| P4 | Required backends fail explicitly; real pgvector tests cover dimensions, migrations and scoped retrieval; Redis roles and failure behavior are tested; a restore drill validates matching database/object data. |
| P5 | Default gates remain deterministic and credential-free; golden timelines catch ordering/state/recovery regressions; live tests are explicitly enabled and bounded, otherwise skipped; reports explain failed cases and release impact. |

## Deferred and Excluded Work

| Item | Decision and reconsideration trigger |
| --- | --- |
| Semantic Cache implementation | Deferred until measured repeated-request cost/latency justifies it; benefit assessment remains P4.2 work. |
| Milvus | Deferred until real pgvector scale, latency, retrieval or operational requirements justify another backend. |
| SQLite-to-Postgres data migration tool | Deferred until a concrete pilot-to-production migration requires it. This does not defer ordinary schema migrations. |
| Full Web administration UI | Deferred until stable operator workflows and user feedback establish the need. |
| Same-session serialization | Runs have no conversation/session entity; define identity and ordering before serializing across runs. Current fencing applies to each Run. |
| MCP OS sandbox, OAuth and arbitrary dynamic endpoints | Not provided by SDK transport support. Operators approve local process commands and fixed HTTP targets; real sandboxing/auth flows require a separate design. |
| Exactly-once external side effects | Not guaranteed by database leases. Use downstream idempotency and operator review of uncertain writes; no automatic replay. |
| Public hosted SaaS isolation, enterprise SSO/OIDC/SCIM, marketplace | Out of scope; require an explicit scope decision/ADR before implementation. |
| Legacy CLI/UI, generated build outputs | Do not port interfaces that duplicate the current API/CLI/Next.js product. |

Revisit only relevant deferred items each release cycle. Record the trigger,
scope, tests and acceptance criteria before changing a decision. Keep advanced
backends, telemetry and live provider tests opt-in; SQLite/mock first run stays
lightweight. Monitor endpoints must not become public by default.

## Working and Completion Rules

1. Start from git status and the relevant existing spec; record the active ID.
2. Add failing behavioral tests, implement the vertical path, and update its
   operator/upgrade documentation in the same task.
3. Record changed files, commands/results, limitations and the next ID when
   handing off. Mark a task blocked or partial when required evidence is absent.
4. Mark completion only after the acceptance checks pass. An adapter without
   execution-path integration is a foundation, not a completed capability.
5. Keep status here; update milestone summaries only when a workstream changes.
   Historical daily records are not new acceptance evidence.
6. Before release, run the full gates and a clean self-hosted rehearsal of
   upload/index/retrieve, agent execution, approval/resume and worker restart.
7. A release requires an explicit scope, compatibility review, current dependency
   review and green CI. This plan does not authorize a release or promise a date.

Closure means every required item has evidence and every deferred item has a
reason/trigger. Internal pilot readiness still requires a workload-specific
trial; it does not establish long-term operational maturity.

Next handoff prompt:

```text
Read the completed acceptance record in docs/capability-hardening-plan.md and
docs/hardening-verification.md. Preserve the Python backend and TypeScript Web.
Do not restart implementation from P1.1 or treat the Day 1-90 records as proof.
Check git status and any changes since verified implementation 6c9fa92 and
green CI 43362548617. P0-P5 is closed within its documented scope, not certified
for every workload. Scope the next real-workload pilot or release review with
the maintainer. Keep deferred items explicit. Live provider smoke is optional
and requires explicit credentials/budget. Do not change VPN/proxy settings,
create a tag or publish a release without new authorization.
```
