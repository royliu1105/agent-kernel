# PV2 Authenticated Web Acceptance

Date: 2026-11-15. Status: **implementation candidate; exact-candidate remote
container/browser verification pending**.

This is the evidence checklist for the remaining authenticated Web/first-run
portion of [PV2](../real-scenario-pilot-plan.md#pv2-rehearse-the-existing-workflow-without-paid-calls),
not a second pilot ledger. The [PV2 closure record](pv2-closure.md) retains the
five previously checked items and their historical evidence. No new pass,
deployment, paid-model proof or full PV2 completion is recorded here.

## Bounded Implementation Contract

The candidate implements an in-memory workspace API key, a Bearer proxy
bridge and actual UI actions for agent creation, KB creation/upload/ingest/chunk/
index, Run creation/queueing, approval/rejection, explicit resume, output inspection
and logout. It also provides scoped identity/agent discovery and bound approval
tool details without raw provider payloads. Backend authorization remains authoritative on
every request; hiding a button or displaying a workspace label is not RBAC.

The browser key is transient user-supplied access, not a shared privileged key
bundled with the app or a proxy default. In-memory storage is not protection from
malicious same-origin script. Logout clears browser credentials and protected
view state; it must not be described as backend key revocation, cancellation of
an in-flight request, stopping a queued Run or deletion of retained evidence.
Server-side revocation and stopping new work retain their separate existing
operator controls and evidence in the closure record.

This bounded workflow does not add chat, streaming, sessions, a new identity/role
system, queued approval resume, automatic memory or CF3-CF8 functionality.
Preview-only surfaces must remain distinguishable from actual persisted results.
The earlier [CF2 inventory](../reviews/2026-11-14-cf2-workflow-inventory.md) records
the pre-implementation limitations; it is not proof that this new path works.

## Pending Check Matrix

Every row below is **Pending**. Assertions describe required observations, not
tests already run. Main-agent CI must record actual case names/results and any
gaps; omitted or skipped cases do not pass by association with a green job.

| ID | Check and required observation | Status |
| --- | --- | --- |
| W01 | Clean exact-candidate checkout builds an isolated remote Docker stack with fresh disposable PostgreSQL/Redis/object data; migrations, API/Worker/Web readiness and scoped credentials are verified. Record owned project/configuration identity and cleanup. Private monitoring remains covered by the separate observability job. | Pending |
| W02 | Enter a workspace API key through the UI and obtain actual authenticated backend data. Verify the key remains in memory, not local/session storage, cookies, URLs, bundled configuration, logs or published artifacts; no ambient/shared-admin fallback. Refresh requires credentials again. | Pending |
| W03 | The Web proxy forwards the supplied Bearer credential for every exercised read/write/upload/decision/resume route. Missing, invalid and revoked credentials are denied by the backend with no protected data or mutation; errors do not expose credentials. | Pending |
| W04 | Exercise backend per-request RBAC through Web requests: operator-A's allowed actions succeed, viewer writes/decisions/resume are denied, and workspace-B cannot read or mutate A's resources using A's IDs. Denials hold for crafted requests, not just disabled UI controls. | Pending |
| W05 | Create an agent in the actual UI; reconcile the returned ID and selected configuration with persisted backend records. Do not use a preview agent or pre-created fixture as evidence of UI creation. | Pending |
| W06 | Create a KB, upload an approved disposable document, ingest it, inspect chunks and index it using actual UI actions. Reconcile document/chunk/index status and source identifiers with backend records; failures stay visible and do not appear ready. | Pending |
| W07 | Create and queue a Run from the UI with the created agent/KB, recorded synthetic task and frozen system prompt. Observe persisted queued/Worker progression and the real returned Run ID; no intercepted business response or canned browser timeline. | Pending |
| W08 | Inspect the actual pending approval and bound tool arguments. Approve and explicitly resume; a decision alone causes no tool execution. Reconcile decision, Run, tool record, events and independent invocation evidence: zero before approval, one after the approved resume. | Pending |
| W09 | Reject and resume a separate Run: terminal rejection and zero tool effects agree. Repeated decisions/resume and overlapping resume attempts must not create duplicate effects; retain linkage to the existing API/Worker cases and identify which cases the browser actually exercises. | Pending |
| W10 | Inspect final output, citations and persisted timeline in the UI for the same Run. Match displayed content/source IDs to actual backend output, not retrieval snippets or preview answers. A fixture-generated answer is labeled fixture evidence, not live answer quality. | Pending |
| W11 | Logout clears the in-memory key and protected view state; subsequent protected operations require credentials and do not reuse the previous key. Switching keys does not retain the previous workspace's displayed records. Record that logout does not revoke the key or cancel existing work. | Pending |
| W12 | Review the exact Web first-run/operator instructions against the tested journey, including separate approval/resume, denied/error states, preview boundaries and logout semantics. Verify effective initial/resumed prompt and configuration provenance for the candidate, or explicitly retain the unverified binding as a blocker. | Pending |

The frozen PV1 model/embedding IDs, limits, prompt and corpus remain unchanged.
The real Docker fixture-provider/browser rehearsal is implemented for remote CI:
actual Web/API/Worker/database traffic, with synthetic provider responses and
disposable credentials/data. No browser response interception may replace the
business path. Any profile difference must be recorded; a generic fixture
provider pass cannot attest the frozen paid-profile bindings by itself. This Web
fixture uses `openai:cf2-offline`, mock embeddings, one synthetic document and an
eight-model-call ceiling for the three-call search/approval/answer journey.
The frozen two-call DeepSeek/DashScope profile is verified separately by
`--pv2-profile`; no fixture configuration is presented as a paid execution.
The [first-use guide](../web-first-use.md) records actual operations and limits.

## Evidence Handoff

The first candidate `fa503db`, CI 43680474418, failed before its first browser
API request: Docker Engine did not expose the published port on an internal-only
network (`ECONNREFUSED`). This is a harness failure, not passed Web acceptance.
The correction gives only the Web proxy a second, loopback-published ingress
bridge. API/Worker/PostgreSQL/Redis remain on the internal network; runtime checks
reject any non-Web container attached to ingress. No local Docker was touched.

The next candidate `d2f23dd`, CI 43680741562, reached UI upload/index/retrieval,
approved execution and independent single-effect readback, then timed out locating
the populated System prompt field for the rejection case. Full acceptance remained
failed. The correction supplies stable explicit textarea accessible names and
a bounded action timeout; the full journey must pass again, not only its tail.

Candidate `ccf050e`, CI 43681268158, passed the complete browser case in 24.1s,
including rejection, logout and revocation. Evidence sealing then failed reading
a root-owned `effects.jsonl`: the earlier browser handoff had made credentials
readable, so the final ownership check incorrectly skipped newer journals.
The correction reclaims all files in the guarded owned mount at every handoff,
preserving private modes. The unit regression explicitly starts with readable
credentials. The overall Web gate remains pending a successful sealed rerun.

Populate only from observed results. Local checks may run static/fixture units;
database, containers and actual browser execution remain remote-CI-only.

| Evidence field | Current value |
| --- | --- |
| Web implementation candidate SHA / dependency and configuration fingerprints | Pending |
| Exact-candidate remote CI URL / jobs / timestamp | Pending |
| Real Docker fixture-provider and browser case results, failures and skips | Pending |
| Sanitized case-to-Run/approval/tool/event/observer references | Pending |
| Effective prompt hash, corpus revision, model/embedding configuration and initial/resumed request checks | Pending |
| Credential/artifact redaction review and owned-resource cleanup result | Pending |
| Main-agent review of each W01-W12 outcome and remaining gaps | Pending |

Keep keys, raw requests, documents, checkpoints and private tool output out of
public logs, screenshots, browser traces and reports. Use sanitized references
and aggregates; never publish credential-bearing storage/network captures.
Historical cbe8c42 / CI 43674964968 evidence remains valid only for its recorded
scope and cannot be relabeled as this Web candidate's acceptance.

## Closure Boundary

- The first unchecked PV2 item can close only after reviewed exact-candidate
  evidence covers the full first-run and authenticated Web requirements above.
- The second unchecked PV2 item also requires CF2 actual workflow/provenance
  reconciliation and the maintainer's explicit
  [CF1 residual-risk disposition](../reviews/cf1-risk-disposition.md).
  CI cannot make that human decision, even when all technical checks pass.
- Intended-environment CF1 deployment verification remains distinct from a
  disposable CI deployment. The active Docker environment is not updated or
  certified by this work. PV3 live/paid behavior and PV5 independent-user evidence
  remain separate, unstarted gates.

Both remaining PV2 items are targeted for closure, but neither is closed here.
No new checks are checked off, and no maintainer acceptance is inferred.
