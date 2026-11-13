# Post-v1.0 Capability Hardening Plan

## Status and Authority

Status: **R1-R10 remediation and N1-N5 bounded-execution follow-up accepted
within documented scope; locally and remotely verified; unreleased (2026-11-14)**.
Reopened after independent audit; the previous blanket
acceptance was withdrawn. Historical implementation commit
`6c9fa92ddc0660c1cfe40453d5f42ad0ed791c51` passed
[CI 43362548617](https://github.com/royliu1105/agent-kernel/actions/runs/43362548617),
but those tests did not establish every original requirement. Confirmed security,
integration and scope gaps below now have repairs, local verification and green
[CI 43375236175](https://github.com/royliu1105/agent-kernel/actions/runs/43375236175)
for implementation `d65e833af7f59583c6830a8d1a710e00b02ffc1e`. A separate
requirement-by-requirement scope review found no remaining required blocker.
Acceptance applies only to the documented self-hosted scope and explicit limits;
it is not production certification or evidence that deferred capabilities exist.
Retain the Python backend and TypeScript Web stack. This is not a new release.

## Active Follow-Up: Bounded Agent Execution

Authorized after the scoped R1-R10 closure: first correct current operator docs,
then implement bounded multi-round execution, persisted approval continuation and
retry backoff. Historical acceptance of `d65e833` does not accept this new work.
Follow-up authorization (2026-11-14): correct README, historical phase status
and v1.0 publication records, then commit this batch, push to `origin/master`
and track/fix its CI. This does not authorize paid provider calls, a new tag or
a release. N5 was kept pending until the pushed implementation's own CI passed;
its exact-commit evidence is recorded below.

| ID | Required delivery | Implementation | Verification |
| --- | --- | --- | --- |
| N1 | Reconcile current production/security guides with actual monitoring auth, Worker metrics, object scope and embedding selection; preserve versioned release history. | Accepted within scope | Local and remote docs/configuration regressions passed; historical release records preserved |
| N2 | Bounded native model/tool rounds and serial multi-call batches; validate call IDs/history, enforce configured budgets, record usage and preserve lease fencing. | Accepted within scope | Local and remote round/batch/budget/ID/timeout/usage regressions passed |
| N3 | Internal durable checkpoint, migration and approval continuation after reopening storage/new executor; repeated approvals, rejection, missing/invalid state, cross-workspace access and concurrent resume covered. | Accepted within scope | Local and remote SQLite/PostgreSQL migrations, concurrent/repeated resume and Worker-to-default-API wire/scope contracts passed |
| N4 | Cancellable capped exponential backoff with jitter and safe Retry-After parsing; apply only to eligible provider/read-only tool retries without write replay or unsafe model fallback. | Accepted within scope | Local and remote delay/parser/runtime cancellation/lease contracts passed; fallback cooldown bypass repaired and regression-tested |
| N5 | Focused regressions, SQLite/PostgreSQL migrations/ownership, full local gates, evals and disposable deployment checks; separately record remote CI when authorized. | Accepted within scope | Local evidence below; CI 43466834113 for cb25484 passed all three jobs, including 1104 main + 1 restore + 4 separately executed deployment cases |

Design/acceptance contract: [bounded native execution](specs/bounded-native-execution.md).
Update each row only after its evidence exists. Real-provider quality, deployment
capacity, S3 restore and a new release remain separate gates, not silently completed.

### N1-N5 Local Verification (2026-11-13)

At this local checkpoint, the follow-up was uncommitted on `d00af5f`; the evidence
does not come from the historical R1-R10 CI run. The results below establish
local verification only. The subsequent commit/push authorization above does
not itself establish a green current CI or authorize release acceptance.

| Gate | Result |
| --- | --- |
| `ruff check .` / `mypy .` | Passed; 218 typechecked source files |
| Changed/new Python format checks / `git diff --check` | Passed; 30 Python files checked |
| Main Python suite with disposable PostgreSQL, Redis and promtool | 1078 passed, zero skipped; only the separately executed restore/deployment files excluded |
| Guarded real PostgreSQL backup/restore | 1 passed; nonempty private checkpoint, usage rows, vectors and matching local objects preserved |
| Final rebuilt Compose HTTP + monitoring contracts | 4 passed; API/Worker/Redis/PG, MCP approval, scrape/auth, Grafana, alert firing/clearing and Worker restart |
| Container Alembic revision | `0019_execution_checkpoint (head)` |
| `make release-eval` | RAG 3/3 + 4/4, tool eval tests 2/2, continuation/backoff/wire/deadline 71/71 SQLite cases, timelines 7/7 |
| PostgreSQL continuation cases omitted by the cheap eval subset | 13 intentionally deselected there; executed successfully by the full backend suite, not silently skipped |
| Web typecheck / production build / Playwright | Passed / passed / 2 passed; no Web source changes |
| Remote CI / paid provider smoke at this checkpoint | Not executed at the 2026-11-13 local checkpoint; CI was subsequently authorized on 2026-11-14, paid smoke remains outside scope |

All disposable containers, the Compose network/test volumes and the temporary
monitoring token file were removed after verification. Existing unrelated
containers and repository source data were not deleted; built images remain.

The optional whole-repository format probe also found six pre-existing,
unmodified files that would be reformatted. They were left untouched to avoid
unrelated churn; full Ruff lint passes, and all files changed in this work pass
format checking. This is not a claim that the whole repository is format-clean.

Regression anchors: `test_bounded_native_execution.py`,
`test_execution_checkpoint_storage.py`, `test_native_continuation_wire.py`,
`test_runtime_backoff.py`, `test_execution_budget_edges.py`,
`test_execution_limits.py`, `test_retry_delay.py`, `test_provider_retry_after.py`
and the expanded CLI/docs/restore tests. Independent review reproduced and then
verified fixes for cancellation-resistant deadline waits, cooldown bypass during
initial fallback and lost usage at the active-time boundary. Entry-point review
also fixed the default API's missing model router and CLI resume's 10-second wait.

Explicit remaining boundaries:

- Native batches are serial, not parallel/streaming or an atomic external transaction.
- Approval resume is a bounded synchronous HTTP segment; approval alone does not
  enqueue it. Background queued resume remains separate work.
- Unknown effects after a crash/timeout require review, never automatic write replay.
- In-process cancellation cannot force-kill arbitrary adapter code; late results
  are discarded and the run/lease ends, but process isolation remains necessary
  for untrusted adapters.
- Observed usage/cost ceilings are not guaranteed billing caps; the built-in
  OpenAI adapter reports zero estimated cost without a pricing implementation.
- Paid live-model quality, production capacity, S3 restore and new release work
  retain their separate validation/authorization requirements.

### Publication-Status Reconciliation (2026-11-14)

- Verified the existing v1.0.0 release metadata/body, annotated tag target and
  successful release-commit CI. Evidence is in the
  [v1.0 checklist](v1-release-checklist.md); no tag or release was changed.
- Corrected README, roadmap, plan/index status and historical phase banners.
  Historical test counts/limitations remain snapshots; unreconstructed
  pre-tag process checks are explicitly unchecked, not invented.
- Added 26 publication/status regressions: docs consistency now passes 55
  cases. The focused docs/limits/backoff/provider/CLI/migration run passed 268
  cases; these overlap the earlier suite and are not an additional full run.
- Reran Ruff, mypy (218 source files), `git diff --check` and `make release-eval`:
  all passed. The cheap eval subset still intentionally deselects 13 PostgreSQL
  cases; backend/deployment evidence remains the separate local record above
  until the new remote CI gate runs.
- At the pre-push checkpoint, remote acceptance was still pending. The completed
  exact-commit verification is recorded separately below.

### N1-N5 Remote Acceptance (2026-11-14)

Implementation: `cb25484d3a6671da135b55e6cbae60542f90e33f`, pushed to
`origin/master`. [CI 43466834113](https://github.com/royliu1105/agent-kernel/actions/runs/43466834113)
completed successfully; Python, Web and Compose all passed on the first run,
without CI-only repairs, weakened assertions or waived failures.

| Remote gate | Verified result |
| --- | --- |
| Python lint/types and fresh SQLite/PostgreSQL migrations | Passed |
| Main Python suite with PostgreSQL, Redis and promtool | 1104 passed, 4 deployment cases skipped here and executed in Compose below |
| Guarded PostgreSQL backup/restore | 1 passed, including the private execution checkpoint |
| Compose HTTP / monitoring deployment | 1 passed / 3 passed; temporary deployment removed |
| Release eval | RAG 3/3 + 4/4, tool eval 2/2, bounded execution 71 passed with 13 PostgreSQL cases intentionally deselected in this cheap subset, timelines 7/7 |
| Web install, typecheck, build and Chromium smoke | Passed; 2 Playwright cases passed |

The main suite's four skips are exactly `test_self_hosted_hardening.py` (1)
and `test_monitoring_deployment.py` (3), not missing acceptance: the Compose job
ran all four against its actual deployment. Across the separate Python gates,
1109 distinct cases passed. Cheap-eval reruns are not added to this total.
The 26-case increase over the earlier 1083-case local record is the added
publication/status regression coverage.

N1-N5 is accepted only within the documented execution/security boundaries.
The serial batch, synchronous resume, unknown external-effect, cancellation,
billing, paid-provider and deployment-capacity limits above still apply.
GitHub reported non-blocking Action Node.js runtime and runner-image notices;
upgrading those dependencies is separate maintenance, not a bypass of this gate.
No tag, release, paid model call or production-capacity certification was made.
The documentation-only evidence commit following this implementation must also
pass its own CI; it does not alter the verified implementation's source code.

Batch execution authorization (2026-11-13): the maintainer requested continuous
implementation of the remaining 13 packages and approved parallel sub-agents.
Local gates were checked per increment; remote CI did not stop unrelated
implementation in this batch. Its historical green run is not final acceptance
of the reopened work.
This supersedes instructions below to wait for P1.1 CI before starting P1.2.
Historical follow-up authorization on 2026-11-13 permitted the first batch's
commit, push to `origin/master`, and CI tracking/fixes. The maintainer separately
authorized commit/push and CI tracking for the R1-R10 remediation ending at
`d65e833`, after its local gates passed. N1-N5 has its own 2026-11-14 authorization
recorded above. No new tag or release is authorized.
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
| 2 | P1.2 | Memory and eval ownership, repository/API isolation. | Accepted within scope; local/current-CI ownership contracts passed |
| 3 | P1.3 | Tool/audit/operational scope review, scoped summaries, rate-limit contract and enforcement. | Accepted within scope; three quota dimensions and authorized summaries verified |
| 4 | P2.1 | Atomic run claims, execution lease lifecycle, fencing or equivalent stale-owner protection. | Accepted within scope; ownership and blocking-tool integration verified |
| 5 | P2.2 | Approval decision/resume concurrency, crash recovery, side-effect replay boundaries. | Accepted within scope; not exactly-once external effects |
| 6 | P0.1 | Readiness, metrics inventory/aggregation, log/trace redaction, cost attribution. | Accepted within scope; entry-point privacy, configured backends and attribution verified |
| 7 | P0.2 | Grafana dashboard, Prometheus scrape/alert templates, operator instructions. | Accepted within scope; 24 panels/15 rules and actual deployment verified |
| 8 | P3.1 | External-tool contract, metadata sanitizer, MCP stdio and fixture server. | Accepted within scope; SDK logging and independent deadlines verified |
| 9 | P3.2 | MCP Streamable HTTP, resources/prompts with policy checks. | Accepted within scope; single-send/failure/cancellation/reconnect contracts verified |
| 10 | P3.3 | OpenAPI tool generation, fixture and per-tool retry/idempotency policy. | Accepted within scope; binding approval/denial, retry policy and audit verified |
| 11 | P4.1 | Consolidate pgvector contracts and Redis queue/rate-limit/coordination integration. | Accepted within scope; real-backend and runtime integration gates passed |
| 12 | P4.2 | Backup/restore and queue drills; documented Semantic Cache benefit assessment. | Accepted within scope; queue fallback and DB/local-object/usage restore verified; cache implementation deferred |
| 13 | P5.1 | Golden approval/tool/retry/fallback/recovery timelines and failure explanations. | Accepted within scope; wire-contract, reasoning, retry and timeline mutations verified |
| 14 | P5.2 | Opt-in live provider smoke, non-blocking cost/latency reports, full closure. | Accepted within scope; local/current-CI gates and scope review passed; paid live smoke not executed |

The 13 remaining packages are orders 2-14; P1.1 was completed earlier and its
regressions remain part of the full gate. See the per-package evidence and
limitations in [final scope review](hardening-verification.md#final-scope-review).

P1.3 must state whether limits are process-local or shared. If a shared guarantee
is required, bring the Redis work forward; do not mark a multi-instance limit
complete based on an in-process implementation. Evaluate same-session
serialization in P2 and record its required behavior or explicit deferral.

## Reopened Remediation Ledger

Audit baseline: `1efc174`. Priority denotes repair order, not package numbering.
User authorization: update status first, implement repairs, fill original scope
gaps, and verify each item. No new tag/release is authorized.

| Fix | Priority / packages | Required behavior and regression evidence | Current state |
| --- | --- | --- | --- |
| R1 | High / P0.1, P3.1 | Install safe logging at API/Worker entry points; SQL exceptions and MCP SDK malformed responses must not disclose prompts, parameters, results or secrets. Test actual configured log paths. | Verified locally and in current CI; default Uvicorn/Worker and SDK diagnostic regressions passed |
| R2 | High / P3.2 | No hidden redirect resend of external writes; HTTP failures are bounded tool failures, not owner/lifespan cancellation. Test actual SDK transport and later calls after failure. | Verified locally and in current CI; SDK transport, queue cancellation and reconnect regressions passed |
| R3 | High / P5.1 | Serialize native OpenAI tool calls/results with call IDs; map transient errors into bounded retry/fallback; contract fixtures reject invalid wire requests. Existing adapter defects, not introduced by the batch. | Verified locally and in current CI; actual-adapter wire/reasoning/retry and mutation tests passed |
| R4 | Medium / P2.1 | Built-in retrieval cannot block event-loop timeouts/lease heartbeat; timed-out work cannot persist late run effects. Test real tool/runtime integration. | Verified locally and in current CI; three reproductions failed before repair and passed afterward |
| R5 | Medium / P1.3 | Independently configured workspace, principal and API-key shared quotas; isolation, atomic admission, Retry-After and backend-failure contracts. | Verified locally and in current CI; real Redis/API, malformed-counter and no-partial-charge contracts passed |
| R6 | Medium / P0.1 | Configured pgvector/provider/local storage readiness; retrieval errors and kb_search instrumentation; API/runtime/eval metrics; authorized workspace/run/user/model cost attribution. | Verified locally and in current CI; 0018 migration, scoped ledger/API and real embedding composition passed |
| R7 | Medium / P0.2 | Export and validate queue backlog/wait, approval wait and cost alert signals; native Prometheus rules/queries and documented operational limits. | Verified locally and in current CI; 24 panels, 15 alerts, native firing and live deployment checks passed |
| R8 | Medium / P3.1, P3.3 | Discovery timeout must not cap configured tool timeout; independent per-tool approval setting passes policy/audit in API and Worker. | Verified locally and in current CI; stdio/HTTP tools/resources/prompts and OpenAPI policy regressions passed |
| R9 | Medium / P4.2 | Real Redis fault drill must attach the faulty queue, observe fallback and complete via DB polling; retain guarded restore and explicit cache deferral. | Verified locally and in current CI; actual queue failure, three recovered runs and DB/local-object/usage restore passed |
| R10 | Closure / P5.1, P5.2 | Strengthen provider/timeline assertions, update all gate instructions, rerun full local/backend/deployment checks; record current remote CI separately. | Local 746 passed/no skips; current CI reconciles all 746 cases; lint/types/Web/evals/deployment and final scope review passed |

Initial audit evidence: 99 focused isolation/ownership/migration tests passed
against fresh real PostgreSQL. Additional probes reproduced default-log secret
leakage, MCP 307/308 duplicate sends, HTTP 500 lifespan cancellation and blocking
kb_search deadlines/heartbeat. Passing existing tests did not negate these bugs.
No remediation is accepted solely because it has been implemented.

Additional integration finding within R6: the existing real embedding adapter
was not selected by API/Worker composition. Explicit
`AGENT_KERNEL_EMBEDDING_PROVIDER=mock|openai` now wires indexing, retrieval and
`kb_search` consistently; default remains credential-free mock. A failing
embedding request restores the document's prior indexable state. Tests mock only
the HTTP transport, not the selected adapter. No paid request was executed.

Evidence map and exact limitations are maintained in
[hardening verification](hardening-verification.md#remediation-verification).

## Batch Implementation Record

Historical evidence below describes the first implementation, not acceptance of
the audited gaps. The current remediation ledger takes precedence.

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
SHA linked above. The subsequent audit reopened P5.2. A separate maintainer compatibility/security
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
4. Track implementation, focused local verification, full local verification,
   and remote verification separately. Mark acceptance only after every required
   check has evidence for the current code. A historical green SHA does not
   accept later changes. An adapter without execution-path integration is a
   foundation, not a completed capability.
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
Read the remediation ledger in docs/capability-hardening-plan.md and
docs/hardening-verification.md. Preserve the Python backend and TypeScript Web.
Do not restart implementation from P1.1 or treat the Day 1-90 records as proof.
Check git status and the per-fix evidence. R1-R10 are accepted within documented
scope for implementation d65e833, verified by CI 43375236175 and final scope
review. Do not restart completed work or infer that deferred capabilities exist.
Keep local, remote and live-provider evidence distinct. Any code changes after
the verified implementation need their own regression evidence. Choose the next
scope with the maintainer; live provider smoke needs explicit credentials/budget.
Do not change VPN/proxy settings, create a tag or publish a release without new
authorization. Scope acceptance is not release approval or production certification.
```
