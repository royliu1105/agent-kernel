# PV1 Offline Acceptance Harness Specification

Version: pv1-harness-spec-v1. Status: **offline components and API/Worker integration
implemented; isolated remote container checks passed; full PV2 open**.
This refines the existing [PV1 contract](pv1-2026-11-15-runbook-assistant.md) and
[operation sheet](pv1-offline-rehearsal.md); it is not another progress ledger.
The [evidence template](pv1-evidence-template.json) is an unpopulated record,
not executable configuration or proof. PV1 technical planning is finalized;
human fields remain at PV5. PV3-PV6 have not started. Current deployment evidence
and remaining gates are in the [PV2 record](pv2-closure.md); historical component
checkpoints below are not the latest aggregate status.
At preparation, provider transmission was pending with spending
authorization USD 0. The [later scoped authorization](pv1-authorization-2026-11-15.md)
allows the first USD 2 and specified operations without verifying DeepSeek's
no-training commitment. Inquiry submission is not assumed. This blank template
remains unpopulated/fail-closed, not a live authorization file.
The later [pv1-config-v1](pv1-2026-11-15-runbook-assistant.md#finalized-technical-profile)
finalizes intended profile bindings and budget. It does not implement this draft
or change the blank template's null effective values. Current work is offline only.

## Offline Implementation Status

The current instruction authorizes offline implementation/tests without waiting
for P1/P2 or dates. Original full-pilot sign-off and PV5 still require them. No environment,
pilot API/model call, current Docker update or production behavior change is
authorized in this step. Code: [fixture primitives](../../scripts/pv1_harness.py);
executable controls: [unit harness](../../tests/unit/test_pv1_harness.py).

Run with existing dependencies only:

```sh
.venv/bin/pytest -q tests/unit/test_pv1_harness.py
```

| Component | Current implementation boundary |
| --- | --- |
| Tool observation | Maintained OpenAPITool + GuardedTransport, with a synthetic pool below origin/path guards; tests block DNS/sockets |
| Journal | Per-executor fixture files, exclusive creation, serialized sticky failure state, fsync, sequences, typed body-free records, truncation/sequence rollback rejection, bounded reads |
| Reconciliation | Per-tool counts across supplied executor IDs; duplicate counts fail even with a truncated tail or late dispatch after close; missing evidence stays unknown |
| Budget | Serial in-memory generation ledger: five tasks, two attempts/task, USD 1.25 allocation, USD 0.25/task; unknown/invalid/over-reserved costs stop admission |
| Payload | Exact byte digest and DeepSeek-only check, tested with synthetic bodies only |
| Beyond this component checkpoint | Persisted approvals and API/Worker cases below now have remote PostgreSQL evidence; shared ledger/container wiring has a separate remote rehearsal, not live billing enforcement |

Observation pass is **not** a case-matrix pass: no database, real approval decision
or execution ownership was exercised. Threaded append tests are not process-crash
proof. A known persistence failure must be supplied to reconciliation through
failed_executors even if buffered bytes are readable. No live transport can be
selected by these fixture primitives; private _pool injection is confined to tests
and requires re-review if the maintained transport changes. Do not install this
partial harness in a live environment. Blank evidence templates remain unchanged.

Pre-review checkpoint on 2026-11-15: **35 fixture tests passed**, 211 with the
related regression suite; Ruff and mypy (241 files) passed. Review added four
regressions for empty/nonempty truncation, concurrent persistence failure and
late duplicate dispatch; **39 fixture tests passed** and **217 related offline
tests passed** after review. Ruff, workspace mypy (241 files) and explicit strict
mypy on the two new harness files passed. The 16 frozen material files are
byte-identical to the content baseline. Remote CI is checked against the eventual
submission SHA separately; these local results do not assert remote success.
Coverage is bounded:

| Spec control | Verified offline | Still not established |
| --- | --- | --- |
| known_dispatch / duplicate_dispatch | Real adapter + synthetic pool; correlated start/validated completion; duplicates fail | Live dispatch and database effect |
| missing_executor | Missing journal or unlisted journal prevents observation pass | Durable manifest/registration across API/Worker |
| journal_before_send | Directory/append fsync failure and missing tool binding block fixture delegation | All filesystem failure modes and process crashes |
| journal_after_send / crash_after_start | Missing completion/close or known failed executor stays unknown | Process death and restarted process recovery |
| incomplete_response | Malformed JSON, wrong identity, redirect, compressed/oversized response and HTTP error never pass | Actual network truncation/timeouts |
| binding_and_guards | Workspace/origin/path denial and fixed anonymous request shape; DNS/socket tripwires | Persisted approval and complete runtime binding |
| budget/payload checks | Limits, attempt/task slots, unknown charge reservation, exact digest/provider check | Automatic retry/resume/embedding wiring and durable cross-process ledger |

Do not copy these component successes into the blank runtime case-plan results.

## PV2 Offline Integration

Current authorization covers review/fixes, scoped commit/push after checks pass
and tracking that submission's CI. No paid or pilot request, local environment
creation or current Docker update. Remote disposable CI services may verify the
PostgreSQL cases. Production modules and frozen inputs/templates are unchanged.

Code: [fixture integration](../../scripts/pv2_offline_harness.py),
[offline tests](../../tests/unit/test_pv2_offline_harness.py),
[PostgreSQL approval cases](../../tests/integration/test_pv2_approval_observation.py).

| Item | Implementation and evidence boundary | Status |
| --- | --- | --- |
| Executor manifest | Case/config digest plus distinct API/Worker IDs; registration before admission; all registered journals required for observation | Fixture implemented |
| Shared admission | Locked append-only file, sequences, fsync, bounded reads, exclusive private creation; reopened instances share reservations | Fixture implemented |
| Replacement/crash | Child process exits after durable reservation; replacement cannot dispatch or close an unresolved window | Offline process test passed; not power-loss/container recovery proof |
| Generation | Maintained DeepSeek adapter uses exact serialized request allowlist before MockTransport; API/Worker-labeled replacements retain task/attempt limits | Fixture implemented; no real runtime bootstrap |
| Embedding | Maintained DashScope batching crosses the same shared ledger; second batch is denied when its allocation is exhausted | Fixture implemented; no ingestion or vector storage |
| Conservative cost | USD 1.25 generation, USD 0.10 embedding; unused USD 0.65 remains locked. Successful requests consume their full reservation, not observed cost | Admission-only; no invoice or real tariff enforcement claim |
| Changed request/unknown charges | Changed serialized body, bad/missing/excess usage or HTTP failure blocks; unresolved reserve prevents replacement/retry dispatch | Fixture implemented |
| Approval/run/tool reconciliation | Approve/reject, new service instance, repeated resume and independent fixture counts are asserted against repository states | Two PostgreSQL tests passed in CI 43671367900 and 43672700313 |
| Full runtime coverage | Six API/Worker in-process cases passed in CI 43672700313; effective container binding and stop/revoke use separate CI steps | See PV2 closure record; no inferred full-gate pass |

Reconciliation is observation-only, not a full approval verdict. Known failed
executors must still be supplied, even when buffered journal bytes are readable.
The manifest digest is a fixture declaration, not proof that a running process
installed hooks. No final journal-hash attestation, anti-tampering guarantee or
all-filesystem-failure durability guarantee is claimed. These helpers expose
only MockTransport and must not be installed as live billing enforcement.

Pre-review verification on 2026-11-15: 237 relevant offline tests passed (20 new PV2 cases
plus the preceding 217). Ruff/pre-commit passed; workspace mypy passed on 244
source files and explicit strict mypy passed on the two new offline harness files.
PostgreSQL test invocation produced **two setup errors**:
AGENT_KERNEL_TEST_POSTGRES_URL was intentionally absent; both bodies did not run.
This is blocked verification, not a skip/pass. No database connection or creation
was attempted. Full PV2 remains open. Exact offline command:

```sh
env -u AGENT_KERNEL_TEST_POSTGRES_URL -u OPENAI_API_KEY -u DEEPSEEK_API_KEY -u DASHSCOPE_API_KEY AGENT_KERNEL_LIVE_SMOKE=0 .venv/bin/pytest -q tests/unit/test_pv1_harness.py tests/unit/test_pv2_offline_harness.py tests/unit/test_docs_consistency.py tests/unit/test_pv1_offline_preparation.py tests/unit/test_pv1_materials.py tests/unit/test_pilot_providers.py tests/unit/test_model_router.py
```

Review found and reproduced an initialization durability defect: failed file or
directory fsync left a readable ledger that could accept work. Initialization now
holds the file lock, writes an incomplete state, and publishes the ready snapshot
only after file/directory sync; caught persistence failures leave a rejecting tail.
Four regressions cover file/directory/ready-marker failure and interruption before
ready. All 24 PV2 offline cases passed after repair. Approval tests now explicitly
check the requested/approved/rejected records and an empty pre-approval journal.
The full related offline suite passed 241 tests; workspace/explicit harness mypy
and pre-commit passed. Remote PostgreSQL evidence is not inferred from these results.
No power-loss durability or real runtime injection claim follows from these tests.

Backend command, for the authorized disposable remote CI context only:
`.venv/bin/pytest -q tests/integration/test_pv2_approval_observation.py`.
Do not substitute the active runtime database. Full safety acceptance additionally
requires the existing approval concurrency/recovery and API authorization suites.

## API and Worker Integration

2026-11-15 implementation checkpoint: production defaults remain unchanged.
The fixture provider in `scripts/pv2_runtime_fixture.py` is injected through
`create_app(execution_service=...)` and `QueuedRunWorker(execution_service=...)`.
These exercise the maintained ASGI routes, queue polling, execution service,
leases and PostgreSQL repositories, not a reimplemented execution loop. They do
not launch a host server, Worker daemon or container and do not contact a provider.

`tests/integration/test_pv2_api_worker.py` adds six cases:

- API creates/queues a Run; Worker reaches approval without executing the tool.
- A new API executor approves or rejects; repeated decisions are idempotent and
  repeated resume is rejected, with independent journal and persisted tool checks.
- Concurrent API resumes admit one winner and one conflict, with one tool call.
- A pre-dispatch provider failure exercises the real retry loop and then succeeds.
- A retryable error after reservation leaves uncertain charges; the real retry
  loop reaches the guard, which denies without a second downstream dispatch.
- API native continuation after tool execution obeys the same guard; an uncertain
  continuation leaves the observation unknown rather than claiming full success.

Run/model/original-task bindings are checked before reservation. The scripted
provider cannot delegate to a live provider. Admission denial is translated to
non-retryable `pv2_admission_denied`, so the runtime records failure normally.
Existing DeepSeek/DashScope wire-format fixture tests remain separate; this is
not proof of the frozen pilot prompt or deployed provider hook installation.
The API cases intentionally disable auth; authenticated A/B access and revoke
acceptance still require their existing security/deployment suites.

Local checkpoint: 246 related offline tests passed, including five new binding/
reservation tests. The six new PostgreSQL cases require the exact submitted CI
run; they have not been run against any local database. CI results must be read
from the matching commit, not inferred from test collection or earlier green runs.
Full PV2 remains open: container-wide instrumentation, effective config/prompt
attestation, operator stop/revoke and end-to-end deployment gates are not passed
by these in-process fixtures.

## Scope and Authorization

The preparation step permitted documentation and in-memory artifact tests only.
Its review authorized scoped commit/push and corresponding CI only. The later
authorization above governs current operations. No harness, OpenAPI operation
binding, environment or credential is created by this specification. Remote CI
disposable test services are not pilot setup.
See the [review record](../reviews/2026-11-15-pv1-harness-spec-review.md).

Later implementation must be harness-only, using the maintained adapter and
guarded transport. Do not add a connector, proxy service, production telemetry
API, new role, Web auth feature or data projection. If the required hooks cannot
be installed without business-code changes, report the blocker for a separate
decision; do not silently weaken coverage or broaden scope.

Keep three distinct scopes: implementation/isolated fixture setup, real anonymous
GitHub inspection, and provider transmission/paid calls. Existing scoped consent
is recorded in the authorization addendum; the current execution hold still applies.
Do not repeatedly ask for unchanged consent. Changed payloads or later paid batches
still require their specific decisions.
Fixture mode must not resolve or contact GitHub or providers. A real GitHub
inspection does not authorize sending its response to a model. Mock model
continuation is not a live provider result. Do not use paid models to orchestrate
fixture cases. Mode is explicit for each case, never inferred from a green test.

## Preflight and Coverage

Before a later case, freeze candidate SHA, dependency lock hash, image digests,
sanitized configuration hash, harness version/hash and operation definition hash.
Record private authorization references, workspace/principal/KB identities,
prompt/material versions and hashes. No secret value or reusable authentication
header belongs in this form. Hash only sanitized configuration, not credentials.

PV1 freezes the intended specification and verification method. Actual image,
configuration, hook and request evidence is collected in separately authorized
PV2 execution; do not require executed PV2 evidence to sign off PV1.

The budget worksheet's per-attempt checks are not implemented by serial operator
admission. Runtime provider retries and tool continuation are automatic. Before
paid execution, verify harness-side pre-dispatch coverage of every generation and
embedding attempt across API, Worker and replacement executors. Reject missing
reservation, unknown prior charges or an unapproved changed tool body before the
next provider request; guard denial must be non-retryable. Fixture controls must
exercise initial, retry and resumed calls, with zero downstream provider dispatch
on denial and one on valid admission. No live request is needed for those controls.
If existing injection hooks are insufficient, report the implementation blocker;
do not fall back to log watching or silently change production code. These remain
unimplemented PV2 obligations, not controls passed by this specification.

Preflight must reject unresolved run_attempt, API version, tool timeout or scope
bindings for a real query. Do not guess run_attempt=1. Preserve the accepted
single run/SHA, constant exclude_pull_requests=true, anonymous access, explicit
approval, no retries/fallback, 32768-byte HTTP and 65536-byte result caps.
pv1-config-v1 now fixes timeout 10000 ms and API version 2022-11-28; the previously
inspected attempt is 1. The template retains null effective observations until
PV2 checks them. Planned values are not measured configuration or fresh responses.

List every participating API and Worker process, including replacements, in the
case manifest with distinct executor IDs. API resume executes tools too. Each
executor must attest the same approved bindings and installed observation hooks
before it can receive work. A planned replacement executor is allowed only after
its distinct identity and hook/configuration attestation are durably added to the
manifest, before it receives work. Preserve its predecessor's journal and counters;
do not reset per-tool-call totals. Unregistered or uninstrumented executors
invalidate coverage; they must not silently join. Record start/end UTC markers and final journal
sequence/count for each executor, then reconcile against this manifest.

Quiesce the isolated case before closing its window: no in-flight dispatch or
unaccounted executor may remain. Never stop or inspect the active local stack.
Manual gh/browser refreshes and unrelated requests are excluded from the window.
Intentional response inspection is a separate authorized record, not part of a
before-approval zero-count case. Participant admission uses the finalized supervised,
serial maintainer procedure, not a new role or a claimed submitter/approver split.
Its effective behavior remains to be checked during PV2.

## Dispatch and Response Evidence

Source boundaries: [guarded HTTP client](../../packages/kernel-tools/src/kernel_tools/external/http.py)
and [OpenAPI adapter](../../packages/kernel-tools/src/kernel_tools/external/openapi.py).
The proposed observer records a durable dispatch-start immediately before
delegating an admitted request to the guarded transport's underlying pool, after
origin/path validation. It must preserve the pinned DNS/TLS path, retries=0,
no redirects, trust_env=false, response bounds and compression rejection.
Replacing the guarded transport with a generic HTTP client is forbidden.

Bind trusted case/run/tool_call/executor IDs out of band, never from model
arguments or response JSON. A missing binding blocks dispatch. The future hook
strategy and coverage must be demonstrated in fixture controls before real use;
this document does not claim an existing observer injection API.

Minimum journal protocol:

1. Create the manifest and case-open marker before accepting work. Give each
   executor its own append-only journal outside its process/container lifecycle,
   retained across restarts. Serialize writes within that journal; assign
   monotonically increasing sequence numbers and globally unique attempt IDs.
2. Persist a dispatch-start before delegation. Flush language/runtime buffers
   and confirm fsync (or equivalent durable-store acknowledgement), including
   directory durability when creating journal/manifest files. Journal initialization
   or pre-dispatch persistence failure prevents the call. No buffered-only record
   counts as durable evidence. Apply the same durability rule to manifest updates,
   completion/error records and close markers; test failure at each boundary.
3. Correlate headers, body consumption and adapter validation with the same
   attempt. Headers alone are not a complete response. Record HTTP status and a
   bounded GitHub request ID if present, body_complete, validation outcome and
   controlled error code. Never log arbitrary exception text or response bodies.
4. Persist completion/error and executor-close markers. Missing completion after
   start, a sequence gap, lost journal or missing close marker leaves evidence
   unknown/incomplete. Stop further dispatches; do not repair history by replay.
5. Reconcile all executor journals with the manifest, persisted approval/tool/run
   records and effective request captures. Retain original failed attempts and
   reruns separately; never retain only the winning executor or best attempt.

Journal event names are case_open, dispatch_start, response_headers,
response_validated, dispatch_error and case_close. UTC timestamps use ISO 8601;
per-executor sequence numbers, not wall-clock ordering, establish local order.
Correlate cross-process events by trusted IDs, never timestamps alone. Lifecycle
markers have no attempt ID; request events must have one. Allow only bounded
ASCII GitHub request IDs (at most 128 characters); discard invalid values rather
than recording arbitrary headers. Error codes are a closed vocabulary: guard,
journal, transport, timeout, http_status, body_limit, malformed_response,
identity_mismatch, result_limit or unknown. No free-form exception is allowed.
An unwritable journal cannot reliably log its own failure: retain the start if
present and record the harness failure separately; never manufacture completion.

A start record counts a conservative dispatch attempt at our boundary. A crash
between that record and delegation cannot prove delivery or absence of a call.
DNS/TLS/timeout errors do not prove GitHub processed anything. Completed body
consumption still needs JSON/identity/result validation. The adapter does not
project fields or enforce the proposed report allowlist; inspect the full bounded
payload privately under separate permission, never just its displayed fields.
This evidence is not GitHub server logs or global exactly-once.

## Fixture Controls Before Real Queries

The offline subset above exercises these controls, but does not complete the
whole matrix or all durability boundaries. In particular, actual initialization/
flush/close crash recovery and cross-process manifest coverage remain open. Use
separate case IDs/journals; synthetic requests must never enter live-case totals.

| Control ID | Required observation |
| --- | --- |
| known_dispatch | One known synthetic delegation produces one correlated start/completion |
| duplicate_dispatch | Two synthetic delegations for one tool call are counted as two and fail its one-call predicate |
| missing_executor | An uninstrumented API/Worker or replacement fails setup/admission |
| journal_before_send | Injected init/append/flush failure results in no delegation |
| journal_after_send | Completion-record failure stops further calls and leaves unknown, not success |
| crash_after_start | Start without completion remains unknown; no automatic replay |
| incomplete_response | Headers with truncated/oversized/malformed body cannot yield valid response evidence |
| binding_and_guards | Missing trusted IDs blocks dispatch; guard failures and redirects do not bypass policy; no network in fixture mode |

Future tests must also exercise concurrent journal writes/restarts and verify no
lost/duplicate sequence numbers or truncated records can pass reconciliation.
Tests of form structure alone do not implement or pass these controls.

## Case Matrix and Verdicts

The six groups in the request template remain unchanged. Expand approved
continuation with a separate second-legitimate-call record, as already required
by the contract; this is not an extra feature or frozen RAG question.

| Case ID | Expected dispatch starts per tool_call_id | Additional pass predicate |
| --- | --- | --- |
| before_approval | 0 | Full covered window; run/tool waiting; no successful lookup result |
| reject_then_resume | 0 | Matching rejected approval; run failed/approval_rejected; tool denied |
| approve_then_resume | 1 | Matching approval; one complete validated response and persisted result/events |
| duplicate_concurrent_resume | 1 total | Count across original and repeated/concurrent resumes, not one fresh count per resume |
| new_executor_resume | 1 total | Shared prior journal/counters retained; completed earlier calls not replayed |
| second_legitimate_approved_call | 1 for the second ID | Distinct persisted tool_call_id and matching approval; first ID still counted separately |
| observer_failure_or_timeout | No preset successful count | Fault-specific disposition; no replay, failed/unknown tool outcome retained |

Keep behavior, observation coverage and overall case verdict separate. Verdicts:
not_run (no execution), blocked (preflight/permission missing), pass (every
predicate has evidence), fail (observed violation), unknown (insufficient or
ambiguous evidence). A duplicate/unauthorized dispatch is fail even if later
observation is incomplete. A complete covered empty window may establish zero;
an empty/missing journal alone cannot. Unknown values are null, never zero.

For injected faults, a fixture control can pass because the expected safe failure
was observed while the tool outcome remains failed/unknown. This does not pass
the live approved-success case. Live timeouts/rate limits remain failed/unknown
attempts, not successful lookups. Keep control verdicts out of live success totals.

## Evidence Form and Review

Copy the evidence template only during later authorized preparation/execution;
this checked-in template must stay unpopulated. Each case record uses the common
record_shape, with its own evidence_class (fixture, live or human_pilot), IDs,
window, per-executor manifest, journal references/hashes, observed counts,
response identity, persisted-state evidence and review decision. Expected counts
live in case_plan, never in the observed field. Compare ID/SHA/run_attempt to the
frozen target; mismatches are inconclusive, not permission to select latest.

Capture actual composed initial/resumed messages, tools, model route and effective
limits/counters privately, not only the prompt file hash. The form links those
captures separately from the journal, which contains no bodies, credentials or
arbitrary headers. Reviewer scoring/gold answers must not enter model context.
Artifact references have a digest, evidence kind and private access classification;
raw artifacts are never attached to the public template or committed by default.

Retain private originals under the accepted 30-day rule; exact collection/deletion
dates and incident contact remain pending. Publish only reviewed sanitized
summaries/references. A case reviewer records rationale, missing evidence and
remaining gates. Maintainer roles may overlap, but do not claim independent
review or two independent participants merely because form fields exist.

Learning checkpoint: demonstrate why approved is not executed, why null is not
zero, and why one executor's count is insufficient. Ask the maintainer to trace
one future case from approval through dispatch to persisted result; no learning
sign-off is claimed now. The [pilot learning guide](../pilot-learning-guide.md)
continues to govern this mechanism.
