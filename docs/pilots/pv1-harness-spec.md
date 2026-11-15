# PV1 Offline Acceptance Harness Specification

Version: pv1-harness-spec-v1. Status: **draft, not implemented or executed**.
This refines the existing [PV1 contract](pv1-2026-11-15-runbook-assistant.md) and
[operation sheet](pv1-offline-rehearsal.md); it is not another progress ledger.
The [evidence template](pv1-evidence-template.json) is an unpopulated record,
not executable configuration or proof. PV1 remains in progress; PV2-PV6 have not
started. At preparation, provider transmission was pending with spending
authorization USD 0. The [later scoped authorization](pv1-authorization-2026-11-15.md)
allows the first USD 2 and specified operations without verifying DeepSeek's
no-training commitment. Inquiry submission is not assumed. This blank template
remains unpopulated/fail-closed, not a live authorization file.

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

Three distinct later permissions are needed: implementation/isolated fixture
setup, real anonymous GitHub inspection, and provider transmission/paid calls.
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

Preflight must reject unresolved run_attempt, API version, tool timeout or scope
bindings for a real query. Do not guess run_attempt=1. Preserve the accepted
single run/SHA, constant exclude_pull_requests=true, anonymous access, explicit
approval, no retries/fallback, 32768-byte HTTP and 65536-byte result caps.
The template preserves the proposed 10000 ms timeout separately from the still
unknown effective value. It does not select an API version on the user's behalf.

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
before-approval zero-count case. Participant admission remains supervised and
pending, not enforced by a new role or a claimed submitter/approver split.

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

These are future tests, not checks performed in this documentation step. Use
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
