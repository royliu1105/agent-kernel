# Reference-Informed Follow-Up Plan

Status: **CF1 candidate CI passed; CF2 isolated API/CLI fixture rehearsal passed, overall gate open; deployment/pilot acceptance pending (2026-11-14)**.

The original authorization covered recording the [comparison](reference-project-comparison.md)
and this plan only. The maintainer subsequently authorized the minimal CF1 repair:
untrusted memory context, input capacity limits, old-checkpoint handling,
regression tests and documentation, followed by review, separate baseline/CF1
commits, push and CI tracking. Preserve current Docker data and do not update
its running environment. This does not authorize CF2-CF8 implementation, paid
requests, pilot admission, tag or release. Identifying a gap is not fixing it; existing passing tests are
not acceptance of a missing capability.

The subsequent continuation authorizes a disposable Docker API/CLI rehearsal
with authentication enabled and offline provider fixtures. Web authentication
remains unresolved and outside this step. See the
[workflow inventory](reviews/2026-11-14-cf2-workflow-inventory.md).
No business-code expansion, active-stack update, paid execution, user admission
or new commit/push is included.

The maintainer subsequently authorized the minimal rejection-terminal repair:
on resume of a rejected approval, atomically terminate its matching waiting
tool call and Run, add regression tests and update documentation. Full local
regression and isolated Docker verification passed; see the
[repair record](reviews/2026-11-14-approval-rejection-repair.md). This does not
close CF2 or authorize active Docker updates, historical data
backfills, commit/push or broader expired/canceled approval behavior changes.

Earlier continuation authorized baseline triage, read-only CF1 analysis and
temporary fixture observations. See the [CF1 review record](reviews/2026-11-14-cf1-memory-boundary.md).
The maintainer requested a demonstration at the learning checkpoint. That review
did not authorize a repair. The later explicit authorization above now governs
the minimal implementation. CF1 commit/push and CI tracking were explicitly
authorized and performed; that permission does not include the new CF2 changes.
Paid execution, active deployment and pilot admission remain excluded.

The subsequent maintainer instruction authorized review of the CF2 rehearsal and
rejection repair, then commit/push and exact-candidate CI tracking once review
passes. See the [review record](reviews/2026-11-14-approval-rejection-repair.md#pre-commit-review).
This supersedes only the earlier commit/push exclusion for these changes;
active Docker updates, historical backfills, paid calls and pilot admission
remain outside the authorization.

The 2026-11-15 instruction starts PV1 contract preparation only; see the
[draft record](pilots/pv1-2026-11-15-runbook-assistant.md). It does not authorize
CF3-CF8, provider compatibility changes, active Docker updates, paid calls,
user admission or a new commit/push. The resource configuration was inspected
read-only at the maintainer's request; credentials were not copied or displayed.

The later 2026-11-15 instruction explicitly authorizes the bounded
[DeepSeek/Alibaba compatibility repair](specs/pilot-provider-compatibility.md),
tests and docs. This supersedes only the provider-compatibility exclusion above.
Budget stays USD 10; paid calls, active Docker updates and broader CF work remain
excluded. Commit/push were excluded at that implementation checkpoint.
This exception does not close CF1/CF2 or PV1.

The subsequent maintainer request authorizes review of PV1 documentation and
the compatibility changes, then commit/push and exact-candidate CI tracking
after the review passes. The [review record](reviews/2026-11-15-pv1-provider-review.md)
owns that evidence. It does not authorize active Docker updates, paid calls,
pilot admission or a release.

## Authority and Relationship to Existing Work

- [PV1-PV6](real-scenario-pilot-plan.md) remains the sole pilot task/status
  ledger, with its frozen scenario, 30-question quality set, authorization,
  budget, user-observation and go/no-go rules. PV1 preparation is in progress;
  PV2-PV6 have not started. Required PV1 decisions remain unresolved.
- This document alone owns CF1-CF8 statuses. CF1/CF2 are bounded pilot-entry
  follow-ups; CF3-CF8 are deferred/conditional proposals, not a second active
  foundation phase. Link evidence between ledgers; never count one as the other.
- [R1-R10/N1-N5](capability-hardening-plan.md) retain their historical scoped
  acceptance. The broader product gaps here do not erase that evidence or mean
  their narrower guarantees were never implemented. Conversely, those green
  tests do not close the new findings.
- [O1-O5](observability-completion-plan.md) retains ownership of observability
  and external-inbox gates. Do not duplicate that work or mark real SMTP receipt
  passed because Mailpit works.
- Keep Python + TypeScript, PostgreSQL-only and Docker-only operation. Use
  disposable databases for tests; preserve the active runtime's data/credentials.
  `resource/` stays read-only and outside maintained build contexts.
- The maintainer owns scope decisions. Assign an implementer and reviewer
  before starting each authorized task. CF1 implementation and code review: Codex;
  deployment/pilot residual-risk disposition: maintainer, pending. The code
  review is not an independent security audit. Codex also implements/reviews the
  selected CF2 rehearsal; maintainer risk disposition remains pending. CF3-CF8
  have not been assigned.
  Follow the [learning guide](pilot-learning-guide.md) for tradeoff, failure
  diagnosis and assertion exercises, without claiming learner mastery from CI.

Priorities are gate order, not new day numbers or promised dates. No new calendar
deadline or extension to the old Day 1-90 plan is implied.

## Priority and Progress

`Not started` means no implementation/acceptance work has begun. `Deferred`
means intentionally outside the current pilot. `Conditional` means a measured
need and separate scope decision are required. None means complete.

| ID | Priority | Delivery | Prerequisite / pilot relationship | Current status | Acceptance evidence |
| --- | --- | --- | --- | --- | --- |
| CF1 | P0: safety gate | Memory/context trust-boundary review, minimal repair if required and adversarial regressions | CUR-1; disposition required before PV2 passes and before memory-bearing live/user admission | In progress: code review/local verification/candidate CI passed; deployment and risk disposition pending | [Repair verification](reviews/2026-11-14-cf1-minimal-repair.md): local 1146 passed, 35 optional skips; candidate `5952ba7` CI passed; not active-local deployment/pilot acceptance |
| CF2 | P0: pilot-entry gate | Verified live/preview workflow map and reproducible prompt/config provenance | CUR-2; freeze assumptions in PV1, verify actual workflow in PV2 | In progress: isolated authenticated API/CLI + offline request provenance passed; Web auth/pilot profile/review open | [Rehearsal evidence](reviews/2026-11-14-cf2-workflow-inventory.md#docker-rehearsal-evidence); synthetic corpus/mock embeddings, not live quality or PV2 acceptance |
| CF3 | P1: reproducibility | Effective prompt-version binding to Run/checkpoint/eval | After PV6 prioritization or explicit earlier scope approval; CF1 context contract | Deferred; not started | None |
| CF4 | P1: product journey | Scoped session/task submission and resumable streaming Web flow | After pilot evidence/scope approval; CF3 or an explicitly approved equivalent provenance contract | Deferred; not started | None |
| CF5 | P2: memory effectiveness | Bounded summaries, semantic recall and controlled memory lifecycle | CF1 and CF3; pilot must identify a memory-specific need | Deferred; not started | None |
| CF6 | P2: regression learning | Reviewed failure-to-eval-case workflow | Existing eval infrastructure plus actual failures with authorized evidence | Deferred; not started | None |
| CF7 | P2: orchestration | Durable multi-agent DAG and scoped handoff | Single-agent baseline measured; approved task demonstrably needs decomposition; CF3 | Deferred; not started | None |
| CF8 | P3: retrieval optimization | Evaluate hybrid retrieval/RRF and optional reranking | PV3 baseline identifies retrieval, not synthesis, as the limiting factor | Conditional; not started | None |

P0 is a planning priority, not a claim that every item is a reproduced critical
vulnerability. Reference-only REF findings are adoption restrictions, not tasks
to fix the unmaintained copy. No reference implementation is imported implicitly.

## Pilot Gate Integration

1. PV1 may start with CF1/CF2 open: assign owners, select the actual scenario,
   name exposed surfaces, decide whether memory is used and freeze evidence rules.
   This is planning, not permission for paid calls or user admission.
2. PV2 cannot pass without CF1 disposition for the admitted path and CF2
   workflow evidence. A critical/high defect requires a separately authorized
   minimal repair and regression. Mere untrusted-text delimiters do not prove safety.
3. If memory is excluded, prove that the actual admitted access path cannot
   enable it, including crafted requests and resume. Omitting `input.memory`
   from a sample request is not enforcement. Record the restricted scope,
   checks and reviewer; CF1 remains deferred for memory-enabled operation, not
   globally passed. If exclusion cannot be enforced, the relevant gate is blocked.
4. Continue PV3/PV4 on the same frozen candidate only after their prerequisites.
   CF1/CF2 evidence is not a replacement for live quality, recovery or capacity
   measurements. Do not add a chat UI, RRF or a new orchestrator to make a trial pass.
5. PV5 retains its independent-user/task/day requirements. At PV6, classify
   observed failures and select justified CF3-CF8 work. A failed pilot can still
   inform a new scope decision; it cannot be relabeled successful by adding features.

The existing pilot uses API/CLI submission and the supported Workbench views.
CF4 is not a prerequisite for that agreed workflow. If participants require a
chat-only workflow, record a separate scope decision and new acceptance baseline.

### CF1: Memory and Context Trust Boundary

Original gap: `_request_from_run` injected stored memory as SYSTEM content;
existing isolation tests did not establish the instruction boundary. The minimal
repair separates fixed policy from bounded untrusted data and validates saved
context. See the [version-1 contract](specs/memory-context-safety.md). Labeling is
not an authorization mechanism or a live-model safety guarantee.

- [x] Trace memory writers, request permissions, retrieval, prompt placement,
  tool policy and checkpoint/resume; document the admitted trust model.
- [x] Reproduce boundary behavior with adversarial fixtures, then implement only
  the minimal authorized repair. Keep source/provenance and bounded context;
  do not add automatic extraction, a new policy engine or a general sandbox.
- [x] Cover instruction-like memories, forged delimiters, external tool results,
  oversized context, workspace mismatch, approval rejection and resume.
- [x] Verify disallowed or unapproved tool calls are blocked independently of
  what the model says; inspect downstream invocation counters and audit records.
- [x] Complete broad local verification: full Python suite, release evals,
  lint/typecheck, docs and temporary-test-database cleanup.
- [x] Complete code review and repair the reproduced validation-response issue;
  no remaining blocking finding in the reviewed CF1 scope.
- [x] Record candidate `5952ba7` and its exact-revision CI: all four jobs passed.
- [ ] Record maintainer residual-risk disposition for deployment/pilot admission.
- [ ] Verify the approved implementation in the intended deployed environment.

Checked items above mean implementation, review and scoped local/CI verification,
not CF1 accepted. Commit/push and CI tracking are authorized; active local
deployment and pilot admission are not.

Acceptance: unit/request-capture tests establish data placement and bounds;
actual runtime tests show no unauthorized data access or tool side effect, no
cross-workspace content and no approval bypass in the frozen cases. Scoped
PostgreSQL/continuation regressions pass. Prompt wording alone is insufficient;
live injection behavior still belongs to PV3. Existing tests passing before this
work do not close CUR-1. Review the residual risk before admitting memory-bearing tasks.

The [initial review](reviews/2026-11-14-cf1-memory-boundary.md) preserves the
pre-repair evidence. The [repair record](reviews/2026-11-14-cf1-minimal-repair.md)
owns new verification details and remaining gates; neither is PV acceptance.

### CF2: Truthful Workflow and Pilot Provenance

Current gap: preview and live surfaces coexist, and the PromptRegistry is not
bound to effective runtime requests. A supported API/CLI route can still serve
the pilot without pretending that all Web views or prompt automation are complete.

The [source inventory](reviews/2026-11-14-cf2-workflow-inventory.md) identifies
the real entry points and evidence limits. In particular, Web decisions do not
resume Runs, live lookup does not render full answers, and Web proxies do not
carry API credentials. Authenticated Web therefore remains an unresolved path,
not a passed RBAC journey. Do not disable auth or add a shared admin key to pass.

- [x] Record source-confirmed API/CLI/Web paths and distinguish existing fixture,
  deployment and live-model evidence. This is preparation, not path acceptance.

- [x] Enumerate the selected steps: upload/ingest, submit, inspect, approve,
  resume, inspect citations and stop. Record actual command/route/UI entry point,
  role and expected persisted records; explicitly label fixture-only controls.
- [ ] Rehearse that exact path from a clean Docker setup with disposable data;
  use actual API/Worker/Web responses, not intercepted browser fixtures.
  The selected API/CLI-only path passed with real API/Worker/MCP/PostgreSQL and
  offline provider transport. Authenticated Web remains excluded/unverified.
- [ ] Freeze a manual prompt/configuration revision and content hashes in the
  restricted pilot record. Verify the effective request at the provider boundary,
  including memory, tool schema and continuation; sanitized public evidence must
  not contain private prompts or documents.
  Manual fixture revision `cf2-api-cli-offline-v1` is verified; the actual pilot
  corpus/model/profile and maintainer review are not yet frozen or accepted.
- [ ] Correct only workflow-blocking instructions once verified. If required
  behavior is absent, record a blocker and request a scope decision, not a mock UI.
  Rehearsal instructions and the minimal rejection terminal-status repair are
  locally verified: rejected resume atomically denies the tool and fails the Run
  without execution; see the [repair record](reviews/2026-11-14-approval-rejection-repair.md).
  The active runtime is not updated. Web-auth/pilot-profile gaps keep this item
  open; broader expired/canceled handling is outside this repair.

Acceptance: the run ID, citations, approval and timeline agree across API/CLI,
Workbench and persisted records; no fixture is counted as live. A reviewer can
identify the exact effective prompt/config revision for each sampled run and
resume without assuming CF3 exists. Missing evidence blocks PV2. Independent
onboarding and usefulness remain PV5 gates, not this scripted rehearsal.

### CF3: Effective Prompt Versioning

Current gap: an immutable in-memory registry is not a versioned execution contract.
Borrow reference templates/manifest ideas, not its failed-reload behavior.

- [ ] Define template identity, content hash, variables/schema and restricted
  effective prompt snapshot; select the version at the runtime entry point.
- [ ] Bind that selection to Run/checkpoint and eval provenance; define behavior
  for old records lacking a snapshot without inventing historical content.
- [ ] Keep existing runs/resumes pinned when the active version changes; make
  a new version apply only according to the explicit new-run contract.
- [ ] Test unknown versions, malformed variables, rollback and failed load. If
  reload is needed, validate a new immutable snapshot before atomic replacement.

Acceptance: integration tests capture the effective provider request before and
after approval/restart and prove version stability; new runs use the selected
new version. Failed loading leaves the previous snapshot usable. Migration,
privacy, eval comparison and affected runtime gates pass. Canary deployment and
a visual prompt editor are not required for this first increment.

### CF4: Session, Submission and Streaming Journey

Current gap: no complete live chat/task-creation Web workflow and no streaming
provider contract. Borrow event/fragment assembly behavior, not the reference's
post-send output filtering or client-side privileged credential handling.

- [ ] Define workspace-scoped session/turn/run ownership, concurrent submission,
  idempotency, cancel/disconnect semantics and the minimum live UI journey.
- [ ] Add a provider streaming contract with fragmented tool-call assembly,
  usage accounting and explicit partial-stream failure semantics. Keep the
  non-streaming fallback truthful; never retry a delivered stream invisibly.
- [ ] Prefer one persisted SSE event contract with sequence/cursor replay,
  bounded backlog/backpressure and reauthorization on reconnect. Do not add both
  SSE and WS without a concrete need; event persistence must not imply exactly-once transport.
- [ ] Decide which content may be streamed before policy checks and which must
  be buffered/redacted; test that forbidden bytes never reach the client.
- [ ] Verify real browser submission, refresh/reconnect, cancel, approve/reject,
  repeated resume and citations against the isolated Docker stack.

Acceptance: the chosen browser journey uses no mocked business responses;
duplicate submissions/reconnects do not cause duplicate effects; event replay
has no unexplained gaps and clients deduplicate by stable IDs. Cross-workspace
stream/list access is denied, secrets do not appear in events and partial output
has an explicit terminal state. Provider contract, API and Playwright tests pass;
authorized live streaming checks remain distinct from fixtures.

### CF5: Controlled Memory Lifecycle

Current gap: scoped persistent records are not automatic conversational memory.
Reference summaries, semantic retrieval, TTL and provenance are useful patterns.

- [ ] Establish a measured baseline for long conversations and recall before
  introducing token windows/summaries or semantic ranking.
- [ ] Preserve approvals, tool results and unresolved commitments during context
  compaction; retain auditable provenance and bounded token/storage cost.
- [ ] Add source/version, expiry, deletion and correction rules. Keep inferred
  memories as reviewable candidates; no default automatic promotion to trusted instructions.
- [ ] Test contradictory facts, stale/deleted records, malicious instructions,
  user/workspace boundaries and extraction/embedding failure.

Acceptance: a frozen dataset shows improvement against the recency baseline at
predeclared quality/cost thresholds; exact thresholds are chosen before outputs
are inspected. Deleted/expired/out-of-scope records cannot be recalled, extraction
failure does not fail a successful task, and required execution context survives
compaction. Unit, PostgreSQL integration and behavior eval evidence are required.

### CF6: Failure-to-Eval Feedback

Current gap: persisted evals exist, but no reviewed failure-to-case drafting workflow.
Reference feedback reports are not model training or proof of autonomous learning.

- [ ] Classify authorized failures into retrieval, synthesis, policy, tool,
  infrastructure and usability causes; redact private evidence.
- [ ] Draft a case with provenance, expected outcome and review status; require
  human approval before adding it to a versioned dataset.
- [ ] Rerun the actual maintained runtime and compare outcomes, usage and
  latency against a pinned baseline; separate this from scoring saved traces.
- [ ] Test duplicate drafts, missing evidence, incompatible revisions and
  attempted private-data export. Do not automatically rewrite prompts or memories.

Acceptance: at least one authorized reproduced defect yields a reviewed case
that fails against the known-bad behavior and passes after its fix. Negative
cases demonstrate no silent dataset promotion or secret disclosure. Review,
dataset/model/prompt revisions and regression results remain attributable.

### CF7: Durable Multi-Agent Orchestration

Current gap: Run state transitions are not a workflow graph. Reference role/DAG
patterns are useful, but copying an in-memory blackboard does not add durability.

- [ ] Identify a task for which decomposition improves the measured single-agent
  baseline; define a bounded graph and typed handoff before adding roles.
- [ ] Persist node/edge state, dependencies, ownership, artifact references and
  parent/child budgets; restrict each role's tools and workspace context.
- [ ] Specify graph cancellation, failure propagation, approval waits and restart
  recovery; explicitly handle unknown external effects without blind replay.
- [ ] Test dependency cycles, concurrent claims, repeated handoff/resume,
  partial completion, process loss and stale-worker writes.

Acceptance: a restarted executor reconstructs the exercised graph and resumes
eligible work without rerunning completed effects; multiple approvals preserve
node state and aggregate limits. Fault-injection and PostgreSQL concurrency tests
prove the scoped guarantees. Live task benefit/cost must meet predeclared goals.
Do not claim general exactly-once effects or support arbitrary untrusted agents.

### CF8: Evidence-Gated Retrieval Improvements

Current gap: no complete hybrid lexical/vector retrieval and RRF pipeline was
found in either project. Confidence-weighted similarity is not RRF.

- [ ] Use PV3 failures to separate retrieval misses from generation/citation
  errors; freeze source passages, corpus revision and baseline metrics.
- [ ] Only if justified, compare vector-only with lexical/vector fusion and
  optional reranking using the existing PostgreSQL backend first.
- [ ] Preserve permission filtering before result exposure, stable chunk IDs,
  citation lineage, deterministic tie handling and retrieval deadlines.
- [ ] Measure no-hit behavior, deletion/reindex freshness, cross-workspace
  requests, recall/ranking quality, latency and additional cost.

Acceptance: predeclared retrieval and downstream answer/citation gates improve
without safety regressions or exceeding agreed latency/cost. If no measured need
or benefit exists, record a deferred/declined scope decision, not a completed
implementation. Adding another vector database is not part of this task.

## Acceptance and Change Control

Before starting a task, record authorization, owner/reviewer, dependency scope,
candidate SHA, configuration fingerprint, risks, test commands and expected
assertions. Preserve existing user changes; do not change business code during
this documentation-only request.

Use `Not started`, `In progress`, `Blocked`, `Failed`, `Passed`, `Deferred` or
`Conditional`. Update this ledger as evidence arrives, not in advance. A task
can be passed only when every in-scope acceptance criterion has a reviewed
record. If a task needs to be split, retain its original criteria and mark the
remaining part open; do not silently shrink the definition of done.

For an implemented change, require focused regression, lint/types, affected
integration/behavior/browser tests, migration/restore checks where applicable,
updated operator docs and exact-candidate CI before final acceptance. Local
success while remote CI is unavailable remains local-only, not `Passed`.
Planning/inspection tasks need reproducible workflow/evidence checks rather
than invented code changes. All skips need scope and disposition.

Record evidence with the task section when work begins, using:

```text
CF ID / status / authorized scope and reference:
Owner / reviewer / candidate SHA / config and dataset revision:
Baseline behavior / chosen tradeoff / accepted exclusions:
Commands / expected assertions / actual results / skips and failures:
Evidence kind (inspection, fixture, live, human_pilot) / sanitized artifact links:
Local gates / exact-candidate CI / applicable pilot reruns:
Remaining blockers / residual risk / reviewer decision:
Learning exercise / maintainer's contribution / assistance / next task:
```

Do not embed a second CF ledger in README, roadmap, old daily plans or the pilot
record. Link to this one. PV states still change only in their own ledger.
Model/prompt/retrieval/runtime changes repeat the pilot's required PV3 cohort;
safety/storage changes also repeat relevant PV2/PV4 checks. Never merge results
across changed candidates or substitute the 2026-11-14 comparison test counts.

Not authorized or required for parity: TypeScript backend migration, SQLite
compatibility, more vector databases, general shell/browser sandbox, semantic
answer caching, all-provider streaming parity, automatic prompt optimization,
microservices, Kubernetes or a new release. If a real scenario requires any of
these, stop at the relevant boundary and request its own scoped decision.
