# CF1 Maintainer Residual-Risk Disposition

Date: **2026-11-22**. Status: **maintainer disposition recorded for the
bounded pilot / intended local Docker path**. The
[CF1-CF8 ledger](../reference-follow-up-plan.md) owns CF1 status; the
[pilot plan](../real-scenario-pilot-plan.md) owns PV2 status.

This consolidates the residual decisions from the
[version-1 memory contract](../specs/memory-context-safety.md),
[historical boundary review](2026-11-14-cf1-memory-boundary.md) and
[minimal repair verification](2026-11-14-cf1-minimal-repair.md).
The historical SYSTEM-memory defect was repaired for the recorded candidate;
it is not presented below as an unfixed defect in that candidate.

## Evidence and Scope

Historical evidence: CF1 candidate `5952ba75f2adeca101b938a9402292811ea56afc`
passed all four jobs in [CI 43590573645](https://github.com/royliu1105/agent-kernel/actions/runs/43590573645).
The repair record distinguishes local regressions, mocked adapter transport,
deterministic model/tool fixtures and disposable deployment checks. Later
[PV2 evidence](../pilots/pv2-closure.md) records cbe8c42 /
CI 43674964968, including offline profile/approval controls. The bounded
authenticated [Web checks](../pilots/pv2-web-acceptance.md) passed on 6466aba /
CI 43681752996.

The frozen pilot admits CF1-bounded untrusted memory containing only reviewed,
non-sensitive preferences/fixtures, with no automatic extraction. Accepting that
scope is not a general CF1 risk waiver for arbitrary memory content, retrieval
limits, or provider no-training risk. There is still no independent security
audit and no general live-model injection immunity claim; live answer quality
and adversarial injection against a paid model remain PV3.

Intended-environment check (2026-11-22, maintainer-authorized): running
`agent-kernel-local` API and Worker both import
`MEMORY_CONTEXT_VERSION == 1` and construct requests with fixed
`MEMORY_CONTEXT_POLICY` plus a separate USER message marked `trust=untrusted`.
Host regressions
`tests/unit/test_memory_context_contract.py` and
`tests/integration/test_memory_context_security.py` passed **44** on disposable
PostgreSQL. This verifies the active local images contain the repair; it does
not authorize shared-user admission or unpaid→paid profile switching by itself.

## Consolidated Decision List

| ID / exact residual risk | Consequence | Existing mitigation | Evidence versus unverified boundary | Maintainer decision / status |
| --- | --- | --- | --- | --- |
| R01: Untrusted memory can still influence model behavior despite lower-priority placement. | Misleading answers or allowed-but-unwanted tool proposals remain possible; correct formatting does not make output safe. | Implemented fixed SYSTEM policy plus separate untrusted USER JSON; static tool policy, persisted approval and original arguments control execution. Frozen scope restricts memory to reviewed non-sensitive data. | Mocked OpenAI wire payload and deterministic deny/approve/reject/resume effect tests are recorded. Fixtures do not interpret malicious content like a live model; general injection resistance and live answer quality are unverified and belong to PV3. | **Accept (scoped).** Proceed under the bounded trust model. Tool policy + persisted approval remain the execution control. Live injection/quality evidence stays PV3; do not claim models ignore malicious text. |
| R02: Memory is workspace-shared; caller-supplied scopes are filters, not per-user ACLs. | A member with memory-read permission can read another member's labeled memory in the same workspace; a `user:<id>` label does not create privacy. | Implemented authenticated workspace ownership, same-workspace source-Run checks and role permissions; documented non-sensitive/shared-workspace pilot restriction. | Role/workspace regressions cover the frozen cases. Per-user isolation is not implemented. | **Accept (scoped).** Workspace sharing is acceptable for the named pilot data/roles. Do not advertise per-user memory privacy. |
| R03: Operator can write memory and review approvals; approval is not independent two-person authorization. | One credential holder can influence context and approve the resulting proposal; approval does not establish independent review. | Backend permissions and persisted approval remain enforced; supervised serial maintainer submission is the frozen operating procedure. | Existing approval/RBAC fixtures demonstrate authorization and effect counts, not separation of duties. | **Accept (scoped).** Role overlap + supervised serial maintainer procedure are acceptable for the bounded single-operator pilot. Two-person control is out of scope. |
| R04: Memory provenance/confidence are descriptive, not verified truth; exact-scope newest-first recall does not resolve stale or contradictory facts. | Wrong or incomplete evidence can yield misleading output even without an authorization bypass. | Implemented item/source IDs and memory-use metadata aid inspection; explicit bounded selection and the frozen domain-review/scoring procedure limit the claim. | Selection/provenance contracts are tested. Semantic relevance and live correctness are not established. | **Accept (scoped).** Reviewed non-sensitive inputs plus manual evidence review are sufficient pending PV3 quality results. |
| R05: Deleting a memory row does not erase saved checkpoints, prior provider requests or backups. | Content may remain in retained history and be reused on a valid resume; deletion cannot be promised as retroactive erasure. | Implemented immutable version-1 resume snapshot; documented private evidence/retention rules and restricted non-sensitive data scope. | Deleted-row resume fixtures confirm snapshot persistence. Provider retention/training commitments are separate. | **Accept (scoped).** Retention semantics are acceptable. Maintainer owns retention/deletion responsibility for pilot data; do not infer erasure. |
| R06: Unsafe legacy memory checkpoints fail closed and are not migrated or refetched. | Pending memory-bearing Runs may become unresumable; blindly creating a replacement can duplicate earlier external effects. | Implemented `unsupported_memory_checkpoint` / structural rejection before model/tool effects; valid legacy no-memory states remain compatible. | Compatibility and rejection fixtures are recorded. | **Accept (scoped).** Blocked legacy Runs and reviewed replacement, without automatic conversion/replay, are acceptable. |
| R07: Semantic memory limits apply after HTTP JSON parsing and are not a general denial-of-service defense. | Large request bodies can consume parser/proxy resources before semantic rejection. | Implemented content/metadata/depth/scope/recall/envelope bounds; Web proxy adds streamed body limits. | Boundary regressions establish semantic limits. Direct API ingress load resistance remains separate. | **Accept (scoped)** for authenticated, restricted local/pilot exposure. Public or multi-tenant exposure needs a separately authorized ingress/DoS control. |
| R08: Existing invalid/oversized rows stay inspectable/deletable, but selecting them or an oversized aggregate fails the Run without truncation. | A task can fail until its selection/data is reviewed; retained data is not automatically repaired. | Runtime revalidation fails before provider/tool effects; API and repository writes validate new data. | Failure and byte-boundary fixtures are recorded. | **Accept (scoped).** Explicit failure + manual remediation are acceptable; no automatic cleanup authorized by this record. |
| R09: Checkpoint validation is structural/version-based, not cryptographic protection against database administrators. | A privileged database actor is outside the demonstrated integrity boundary. | Implemented exact policy/envelope/version/provenance consistency checks; private runtime credentials and restricted operations are documented. | Forged/malformed/unsupported checkpoint fixtures are recorded. | **Accept (scoped).** Trusted database/operator administration is an acceptable assumption for this pilot. |
| R10: Omitting memory from an example, or relying on stored `Agent.memory_policy`, is not an enforced memory-disable boundary. | A purported memory-free pilot could still admit caller-selected memory or memory-bearing resume. | Explicit Run selection and bounded context are implemented. The frozen scope admits bounded memory. | Historical review found no execution enforcement of `Agent.memory_policy`. | **Accept (scoped)** the admitted bounded-memory path. Any memory-free claim needs separate access-path proof and is not granted here. |
| R11: Candidate CI does not establish that the intended running environment uses the repair consistently. | Old or mixed API/Worker versions may retain old request/checkpoint behavior; auth-disabled localhost operation does not provide multi-user isolation. | Documented upgrade procedure; authenticated scoped operation required for the admitted path. | 2026-11-22 intended local Docker check: API+Worker expose v1 untrusted boundary; 44 host CF1 regressions passed. | **Accept (scoped)** under these conditions: API and Worker replaced together from a revision that includes the CF1 repair; authenticated operation for the admitted path; re-verify after any image rebuild before memory-bearing paid or multi-user use. Disposition does not replace that re-verification. |

These decisions do not request a new memory engine, ACL system, sandbox, proxy
platform or general security certification. A required mitigation beyond the
authorized scope remains a blocker to report and scope separately.

## Maintainer Decision Record

| Required field | Current value |
| --- | --- |
| Decision maker / date / explicit instruction reference | Maintainer (`royliu1105`), 2026-11-22, chat instruction to complete CF1 residual-risk disposition for the bounded pilot path |
| Candidate SHA and intended environment/profile covered | Repair candidate `5952ba75f2adeca101b938a9402292811ea56afc`; intended environment = local Docker Compose project `agent-kernel-local` (authenticated, single-operator). Current tree at disposition time includes that repair lineage (HEAD recorded in the verification note below). |
| R01-R11 individual or explicitly grouped disposition | All eleven IDs: **scoped accept** with the conditions in the table above |
| Accepted restrictions, conditions, unresolved objections and responsible owner | Restrictions: reviewed non-sensitive memory only; no per-user ACL claim; no live-injection immunity claim; no erasure promise; no memory-free claim via `Agent.memory_policy`; auth required for admitted path. Unresolved: PV3 live quality/injection; public ingress/DoS; shared-user admission. Owner: maintainer |
| Intended-environment verification reference | 2026-11-22: `docker exec` on `agent-kernel-local-api-1` / `worker-1` confirmed `MEMORY_CONTEXT_VERSION=1` and untrusted request construction; disposable-DB pytest **44 passed** for memory contract/security suites |
| New candidate regression / Web CI review | Historical Web CI 43681752996 remains technical evidence only; this disposition adds maintainer acceptance for the bounded path, not a new CI run |

Acceptance of these residual risks does **not** waive critical/high defects,
authorize arbitrary paid spend, admit independent users, or close PV3–PV6.
Paid DeepSeek + GitHub approve→resume was separately authorized and observed
successful the same day (see [local paid experience](../local-paid-experience.md));
that observation is not a CF1 waiver expansion.

## Relationship to the Two Open PV2 Items

With this disposition recorded, the CF1 half of the composite PV2 gate is
satisfied for the admitted bounded path. CF2 bounded offline workflow/provenance
and authenticated Web evidence already exist in the PV2 records. Full PV2
checkbox closure is owned by the [pilot plan](../real-scenario-pilot-plan.md)
and [PV2 closure record](../pilots/pv2-closure.md); this file does not silently
relabel those ledgers. PV3 live behavior and PV5 human-pilot requirements remain
separate.
