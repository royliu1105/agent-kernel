# CF1 Maintainer Residual-Risk Disposition

Date: 2026-11-15. Status: **decision pending; no risk accepted on the
maintainer's behalf**. The [CF1-CF8 ledger](../reference-follow-up-plan.md) owns
CF1 status; the [pilot plan](../real-scenario-pilot-plan.md) owns PV2 status.

This consolidates the residual decisions from the
[version-1 memory contract](../specs/memory-context-safety.md),
[historical boundary review](2026-11-14-cf1-memory-boundary.md) and
[minimal repair verification](2026-11-14-cf1-minimal-repair.md).
It records no new security review, runtime verification or risk acceptance.
The historical SYSTEM-memory defect was repaired for the recorded candidate;
it is not presented below as an unfixed defect in that candidate.

## Evidence and Scope

Historical evidence: CF1 candidate `5952ba75f2adeca101b938a9402292811ea56afc`
passed all four jobs in [CI 43590573645](https://github.com/royliu1105/agent-kernel/actions/runs/43590573645).
The repair record distinguishes local regressions, mocked adapter transport,
deterministic model/tool fixtures and disposable deployment checks. Later
[PV2 evidence](../pilots/pv2-closure.md) records cbe8c42 /
CI 43674964968, including offline profile/approval controls. These are existing
records, not reruns or verification of the new Web implementation.

The frozen pilot admits CF1-bounded untrusted memory containing only reviewed,
non-sensitive preferences/fixtures, with no automatic extraction. Accepting that
scope, the task prompt, retrieval limits or provider no-training risk was not a
general CF1 risk waiver. There is no live paid-model injection/quality proof,
independent security audit or verification that the active Docker images contain
the approved repair. The bounded authenticated
[Web checks](../pilots/pv2-web-acceptance.md) passed on 6466aba / CI 43681752996;
that technical result is not risk acceptance.

In the list below, an existing mitigation is an implemented contract or a
documented operating restriction, as labeled. It is not evidence that the
intended deployment enforces every restriction. Each decision remains pending.

## Consolidated Decision List

| ID / exact residual risk | Consequence | Existing mitigation | Evidence versus unverified boundary | Maintainer decision required / status |
| --- | --- | --- | --- | --- |
| R01: Untrusted memory can still influence model behavior despite lower-priority placement. | Misleading answers or allowed-but-unwanted tool proposals remain possible; correct formatting does not make output safe. | Implemented fixed SYSTEM policy plus separate untrusted USER JSON; static tool policy, persisted approval and original arguments control execution. Frozen scope restricts memory to reviewed non-sensitive data. | Mocked OpenAI wire payload and deterministic deny/approve/reject/resume effect tests are recorded. Fixtures do not interpret malicious content like a live model; general injection resistance and live answer quality are unverified and belong to PV3. | Decide whether to proceed within this bounded trust model subject to PV3, or require a separately scoped restriction/fix. **Pending**. |
| R02: Memory is workspace-shared; caller-supplied scopes are filters, not per-user ACLs. | A member with memory-read permission can read another member's labeled memory in the same workspace; a `user:<id>` label does not create privacy. | Implemented authenticated workspace ownership, same-workspace source-Run checks and role permissions; documented non-sensitive/shared-workspace pilot restriction. | Role/workspace regressions cover the frozen cases. Per-user isolation is not implemented; bounded authenticated Web enforcement passed in CI; intended deployment role bindings remain unverified. | Decide whether workspace sharing is acceptable for the named pilot data/roles. If not, block the affected scope rather than promise per-user isolation. **Pending**. |
| R03: Operator can write memory and review approvals; approval is not independent two-person authorization. | One credential holder can influence context and approve the resulting proposal; approval does not establish independent review. | Backend permissions and persisted approval remain enforced; supervised serial maintainer submission is the frozen operating procedure. | Existing approval/RBAC fixtures demonstrate authorization and effect counts, not separation of duties or reviewer quality. No new submit-only role or two-person control is provided. | Decide whether this role overlap and supervised procedure are acceptable for the bounded pilot. **Pending**. |
| R04: Memory provenance/confidence are descriptive, not verified truth; exact-scope newest-first recall does not resolve stale or contradictory facts. | Wrong or incomplete evidence can yield misleading output even without an authorization bypass. | Implemented item/source IDs and memory-use metadata aid inspection; explicit bounded selection and the frozen domain-review/scoring procedure limit the claim. | Selection/provenance contracts are tested. Semantic relevance, truth, conflict resolution and live correctness are not established; no automatic consolidation/redaction pipeline is introduced. | Decide whether reviewed non-sensitive inputs plus manual evidence review are sufficient pending PV3 quality results. **Pending**. |
| R05: Deleting a memory row does not erase saved checkpoints, prior provider requests or backups. | Content may remain in retained history and be reused on a valid resume; deletion cannot be promised as retroactive erasure. | Implemented immutable version-1 resume snapshot; documented private evidence/retention rules and restricted non-sensitive data scope. | Deleted-row resume fixtures confirm snapshot persistence. Complete erasure, provider retention/training commitments and actual retention execution are unverified; separate scoped provider-risk acceptance is not CF1 acceptance. | Decide whether these retention semantics are acceptable and record applicable retention/deletion responsibility before admission; do not infer erasure. **Pending**. |
| R06: Unsafe legacy memory checkpoints fail closed and are not migrated or refetched. | Pending memory-bearing Runs may become unresumable; blindly creating a replacement can duplicate earlier external effects. | Implemented `unsupported_memory_checkpoint` / structural rejection before model/tool effects; valid legacy no-memory states remain compatible. Documented review of pending approvals/earlier effects before deliberately starting a new Run. | Compatibility and rejection fixtures are recorded. Inventory of the intended environment's old checkpoints/effects and its upgrade rehearsal are not established here. | Decide whether blocked legacy Runs and reviewed replacement, without automatic conversion/replay, are acceptable for deployment. **Pending**. |
| R07: Semantic memory limits apply after HTTP JSON parsing and are not a general denial-of-service defense. | Large request bodies can consume parser/proxy resources before semantic rejection; bounded recall alone does not prove ingress resilience. | Implemented 16 KiB content / 4 KiB metadata, depth 16 / 4096 visited values/keys, 1-8 scopes, 1-20 recall limit, 64 KiB envelope and one bounded query; history/token/runtime limits remain. | Boundary and query regressions establish those semantic limits. Deployment body-size controls and load/DoS resistance are not proven; the Web proxy adds bounded streamed bodies (256 KiB JSON / 9 MiB multipart), but direct API ingress and general load resistance remain separate. | Decide whether existing limits and restricted access suffice for the intended exposure or require a separately authorized deployment control. **Pending**. |
| R08: Existing invalid/oversized rows stay inspectable/deletable, but selecting them or an oversized aggregate fails the Run without truncation. | A task can fail until its selection/data is reviewed; retained data is not automatically repaired. | Runtime revalidation fails before provider/tool effects; API and repository writes validate new data; documented manual narrowing/replacement preserves deliberate selection. | Failure and byte-boundary fixtures are recorded. Current business-data suitability and cleanup are not verified or authorized here. | Decide whether explicit failure/manual remediation is acceptable; do not assume automatic cleanup or authorize deletion through this record. **Pending**. |
| R09: Checkpoint validation is structural/version-based, not cryptographic protection against database administrators. | A privileged database actor is outside the demonstrated integrity boundary; validated structure does not establish authentic history against that actor. | Implemented exact policy/envelope/version/provenance consistency checks; private runtime credentials and restricted operations are documented controls. | Forged/malformed/unsupported checkpoint fixtures are recorded. Resistance to privileged database tampering and deployment administrator controls are not certified. | Decide whether trusted database/operator administration is an acceptable assumption for this pilot. **Pending**. |
| R10: Omitting memory from an example, or relying on stored `Agent.memory_policy`, is not an enforced memory-disable boundary. | A purported memory-free pilot could still admit caller-selected memory or memory-bearing resume, invalidating the exclusion claim. | Explicit Run selection and bounded context are implemented. The current frozen scope admits bounded memory rather than claiming enforced exclusion. | Historical review found no execution enforcement of `Agent.memory_policy`; no subsequent exclusion proof is recorded. Crafted-request/resume exclusion has not been verified. | Decide on the admitted bounded-memory scope; any alternative exclusion needs actual access-path proof and cannot globally pass CF1. **Pending**. |
| R11: Candidate CI does not establish that the intended running environment uses the repair consistently. | Old or mixed API/Worker versions may retain old request/checkpoint behavior; auth-disabled localhost operation does not provide multi-user isolation. | Documented upgrade procedure: inspect pending approvals/effects, back up, stop old executors and replace API/Worker together; authenticated scoped operation is required for the admitted path. | Historical candidate CI/disposable deployment passed. Active Docker was not updated; intended-environment image/configuration/auth/upgrade verification remains pending. | Decide the acceptable deployment conditions separately from authorizing or performing deployment. Risk disposition cannot replace that verification. **Pending**. |

These decisions do not request a new memory engine, ACL system, sandbox, proxy
platform or general security certification. A required mitigation beyond the
authorized scope is a blocker to report and scope separately, not permission to
expand functionality. Missing evidence cannot be converted into an accepted risk
by the implementing or reviewing agent.

## Maintainer Decision Record

Only the maintainer may supply the disposition. For each R01-R11, record an
explicit scoped acceptance with conditions, rejection, or request for a separately
authorized mitigation. A grouped decision must name every covered ID and its
conditions; silence, a green CI or "finish PV2" is not acceptance.

| Required field | Current value |
| --- | --- |
| Decision maker / date / explicit instruction reference | Pending |
| Candidate SHA and intended environment/profile covered | Pending |
| R01-R11 individual or explicitly grouped disposition | Pending for every ID |
| Accepted restrictions, conditions, unresolved objections and responsible owner | Pending |
| Intended-environment verification reference | Pending; no active Docker update |
| New candidate regression / Web CI review | Bounded Web CI 43681752996 passed; no intended deployment acceptance |

Acceptance of a residual risk does not turn an unverified claim into evidence,
waive critical/high defects, authorize paid calls or deployment, or admit users.
This file does not solicit or perform those operations. No decision is prefilled.

## Relationship to the Two Open PV2 Items

The [Web acceptance record](../pilots/pv2-web-acceptance.md) defines technical
evidence for the first-run gate and CF2 full-workflow reconciliation. The main
agent can collect and review those results. It cannot make this maintainer
decision. The canonical second PV2 item therefore remains unchecked until both
reviewed CF2 evidence and explicit CF1 disposition for the admitted path exist.
Any applicable deployment-verification condition must remain visible, not be
silently satisfied by a historical or disposable CI run.

The request targets closure of both remaining items; this document prepares the
decision boundary without claiming either item complete. CF1 as a whole still
retains its intended-deployment verification gate, and PV3 live behavior and PV5
human-pilot requirements remain separate.
