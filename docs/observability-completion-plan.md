# Observability Completion Plan

Status: **Local single-host scope and candidate remote CI verified; external email blocked (2026-11-14)**.

This is the canonical O1-O5 ledger for the explicitly authorized follow-up:
centralized logs, a trace backend and alert notification delivery. It is a narrow
exception to the pilot's foundation-feature freeze, not a new Day 1-90 schedule.
The [pilot ledger](real-scenario-pilot-plan.md) now tracks PV1 preparation;
PV2-PV6 have not started. Historical R1-R10/N1-N5 acceptance did not
include these backend/delivery guarantees and is not evidence for this work.
No commit, push, paid model call, external message, tag or release is implied
by this plan alone; each requires the corresponding explicit authorization.
The later baseline/CF1 commit, push and CI tracking were explicitly authorized;
their exact-candidate evidence is recorded below.

## Baseline and Scope

Already delivered: safe application JSON logs; operation spans and redacted OTLP
export; authenticated Prometheus metrics, 24 Grafana panels and 15 alert rules.
The local metrics stack is running. Those facts do not prove centralized log
search, trace storage/query, or notification delivery.

Deliver a reproducible optional single-host deployment, using existing runtime
interfaces. Prefer bounded rotating application files plus Alloy collection
over granting a collector access to the Docker control socket. Alloy also
receives OTLP traces and forwards them to Tempo. Loki stores logs. Grafana
provisions both data sources. Prometheus forwards alerts to Alertmanager.

The maintainer selected **SMTP email**. No SMTP service, sender, recipient or
credentials are currently available. A private Mailpit test mailbox establishes
local SMTP delivery only; it never forwards messages to real mailboxes. External
email delivery stays blocked/not accepted until explicitly configured and
confirmed at the intended inbox. Never paste credentials into chat or Git.

## Priority and Progress

| ID | Priority | Delivery | Implementation | Local E2E | External acceptance |
| --- | --- | --- | --- | --- | --- |
| O1 | P0 | Plan, accurate status, scoped design and evidence contract | Documented | Docs checks passed; not backend E2E | Not applicable |
| O2 | P1 | Safe bounded file sink, Alloy collection, Loki storage, Grafana search | Implemented | Passed: search, privacy, rotation/restart | No hosted/HA claim |
| O3 | P1 | OTLP receiver, Tempo storage, Grafana traces and log correlation | Implemented | Passed: model/tool spans, correlation, restart/outage | No hosted/HA claim |
| O4 | P1 | Alertmanager SMTP, grouping/deduplication, firing/recovery emails | Implemented | Passed: real fault, local firing/resolved, SMTP retry, grouping/deduplication | Blocked: SMTP settings and inbox confirmation absent |
| O5 | P0 | Security/recovery regressions, clean deployment, docs and final review | Locally and candidate-CI verified | Fresh 8-test deployment passed and cleaned up; regression evidence below | Candidate `5952ba7` CI passed; no production/HA or real-mailbox claim |

Update one row only after its evidence exists. Report implementation, local
verification, remote CI and external delivery independently. A blocked external
gate does not erase completed local work, but cannot be relabeled complete.

## Acceptance Checklist

### O1: Contract

- [x] Current README/roadmap/plan entries link to this ledger and preserve pilot status.
- [x] Historical scope stays distinguishable from these new deliveries.
- [x] Document local-only/production configuration, secrets, limits and evidence.

### O2: Centralized Logs

- [x] API and Worker emit sanitized JSON to separate bounded rotating files.
- [x] Collector reads only application log storage; no Docker socket or host-root mount.
- [x] A real runtime task's logs appear in Loki and through authenticated Grafana.
- [x] Search by run/trace ID works without using those IDs as indexed stream labels.
- [x] Sensitive canaries are absent from stored logs; unstructured raw messages fail closed.
- [x] Rotation/collector restart resumes collection; stored evidence survives backend restart.
- [x] Retention, disk bounds, outage/drop behavior and private access are documented.

### O3: Trace Backend

- [x] API and Worker export actual operation spans through Alloy to Tempo.
- [x] Query a known persisted trace ID and verify run/model/tool parent relationships.
- [x] Grafana can query Tempo and link the trace ID from a stored log entry.
- [x] Sensitive canaries are absent; raw prompts/tool results are not exported.
- [x] Stored traces survive backend restart; export failure does not fail agent execution.
- [x] Document retention, bounded buffering, sampling and single-host limitations.

### O4: Email Notifications

- [x] Production SMTP example requires TLS and reads auth secrets from private files.
- [x] Local Mailpit mode is explicit and cannot accidentally send to external recipients.
- [x] A real monitored fault becomes pending/firing and delivers an identifying email.
- [x] Recovery clears the alert and delivers a resolved email to the local mailbox.
- [x] Grouping/repeat policy and retry after temporary receiver failure are verified.
- [x] SMTP outage is visible; no guarantee of exactly-once or guaranteed delivery.
- [ ] Real SMTP configured with approved sender/recipient, and inbox confirms firing/recovery.

The final checkbox is intentionally blocked until external setup exists. Local
Mailpit receipt and SMTP server acceptance are not proof of external inbox arrival.

### O5: Integration and Evidence

- [x] Native configuration validators, focused Python tests, lint and typecheck pass.
- [x] A reproducible opt-in deployment test covers log/trace/SMTP paths and recovery.
- [x] Existing default-profile monitoring/runtime tests remain green; skips and profile are recorded.
- [x] Preserve user's running experience data; fault drills use disposable targets.
- [x] Document start/stop, endpoints, private credentials, troubleshooting and retention.
- [x] Record exact commands/results, failure fixes and unresolved gates below.
- [x] Verify the committed candidate in remote CI, including full-stack and default Docker profiles.

## Estimate and Tradeoffs

Planning estimate: 8-16 hours of focused implementation/verification, usually
1-2 working days; downloads and external SMTP setup can add elapsed time. This
is not a guarantee of passing all acceptance gates today. Approximate allocation:
contract 0.5-1h, logging 2-4h, tracing 2-4h, SMTP 1.5-3h, integration/docs 2-4h;
shared configuration and verification overlap rather than adding independently.

Local filesystem backends are a bounded single-host rehearsal, not HA or
object-storage production validation. Retention is not an instantaneous deletion
guarantee or a disk quota. Telemetry remains best effort under prolonged failure.
Monitoring data crosses workspaces: operators only, not tenant-facing Grafana
accounts. No raw task content, credentials or external recipients in test fixtures.

## Evidence

2026-11-14 initial checkpoint: plan created before implementation. No O2-O5
verification result is claimed. Real SMTP setup is unavailable. Existing metric
scrapes and SDK tests are baseline evidence only, not acceptance of this work.

Implementation checkpoint (not acceptance): native Loki/Tempo/Alloy configuration,
Alertmanager email templates and the two additional Prometheus alert scenarios
passed their native validators. Focused observability tests: 56 passed. Full
default-backend suite with promtool: 1059 passed, 89 opt-in cases skipped; the
new deployment tests are among those skips and run separately. Ruff passed;
mypy checked 222 files. The first sandboxed suite was invalidated by local socket
binding restrictions and rerun with the required permission, not called green.

The first real deployment exposed a Grafana read-only nested bind mount; the
second exposed Alloy data-volume ownership and an unsupported LogQL stage.match
pipeline. Those failures triggered repairs, not acceptance. An exploratory
ownership fix in that disposable volume is not clean-start proof; a new random
project is required for final verification. Existing experience data is untouched.

Follow-up clean starts exposed a missing-file startup race in the collector and
an overly strict test assumption about Loki's automatic `detected_level`
structured metadata. Built-in file discovery now finds the two exact paths after
creation; the test checks indexed labels through Loki's series API separately
from query-time metadata. Native validators and alert-rule tests now run inside
the rehearsal command itself, including in the new dedicated CI job. Search and
model trace checks subsequently passed; complete recovery/email acceptance is
still pending at this checkpoint.

First complete isolated rehearsal: `agent-kernel-observability-db60cf6e`,
`python scripts/observability_rehearsal.py`, **7 passed in 336.18 seconds** and
successful cleanup. This verified rotation, collector/backend restart, actual
Worker pending/firing/recovery, failed SMTP followed by retry, and both local
emails. Multi-alert grouping was added afterward and is not yet included in
that result. A fresh expanded rehearsal is running; do not reuse the 7-test
result as evidence for the new case.

Default suite rerun: `AGENT_KERNEL_TEST_PROMTOOL=1 .venv/bin/pytest -q`,
**1059 passed, 90 skipped in 68.84 seconds**, before adding the grouping case.
Opt-in PostgreSQL/Redis/restore/monitoring profiles are not all exercised by
that command. Native SMTP validation also passed for the TLS-required production
example without contacting its placeholder server. No remote CI was run.

Additional format review found six pre-existing, unchanged files outside this
workstream that `ruff format --check .` would reformat (`kernel_evals/rag.py`,
`kernel_evals/tool_calls.py`, `kernel_identity/authorizer.py`, and the memory
repository/retrieval and storage repository unit tests). This is recorded as
existing format drift, not a passing repository-wide format check. No unrelated
formatter churn was applied; Ruff lint and mypy pass.

## Final Local Evidence

2026-11-14, fresh project `agent-kernel-observability-400879cf`:

| Check | Result |
| --- | --- |
| `.venv/bin/python scripts/observability_rehearsal.py` | Native validators and two added alert-rule scenarios passed; **8 E2E tests passed in 312.13s**, exit 0 including owned-resource cleanup. |
| `AGENT_KERNEL_TEST_PROMTOOL=1 .venv/bin/pytest -q` | **1059 passed, 91 skipped in 71.37s**; conditional real-backend suites are not all part of this profile. The 8 deployment cases above run separately, not as accepted skips. |
| `.venv/bin/pytest -q tests/unit/test_docs_consistency.py tests/unit/test_observability_file_logging.py tests/unit/test_observability_full_templates.py` | **89 passed**. |
| `.venv/bin/ruff check .` / `.venv/bin/mypy .` | Passed / **222 source files** checked. |
| `ruff format --check` on the five new/modified observability Python files | Passed; unrelated repository-wide format drift is recorded above. |
| `git diff --check` | Passed. |
| Full-overlay Grafana API checks | Existing **24-panel** dashboard provisioned; Prometheus source health **OK**; anonymous search **401**. |

The 8 deployment tests cover existing upload/RAG/Worker/MCP approval HTTP smoke;
private searchable runtime logs; correlated model spans; API approval/tool spans;
real file rotation; collector outage and stored log/trace recovery across restart;
two-alert grouping and duplicate suppression; and real Worker pending/firing/
resolved plus SMTP outage/retry. No external model or mailbox was contacted.
Grouping uses explicit local fixture alerts; the Worker fault uses real Prometheus
scrapes. Repeat configuration and suppression before the repeat interval were
verified; an hour/four-hour repeat-soak was not run.

Rehearsal containers, networks and volumes are disposable and have been removed.
At that rehearsal checkpoint the original host API/Worker/Web and metrics-only
stack were preserved, and the new backends were not attached to them. The later
explicitly authorized [Docker-only cutover](docker-local.md) supersedes that
running-state snapshot: the legacy processes/metrics stack are stopped with data
backed up; all 13 services, including these backends and Web, now run together in
`agent-kernel-local`. The existing unrelated database was not modified.

Remaining gates: approved real SMTP configuration and inbox proof, and deployment-specific operational
hardening for any shared/production host. Long-duration retention, abrupt-crash
loss guarantees, HA, external inbox delivery and a user pilot are not certified
by these tests. This work is committed but unreleased; no new release is implied.

## Subsequent Remote Evidence

Baseline `8f87473` and CF1 candidate `5952ba75f2adeca101b938a9402292811ea56afc`
were pushed with explicit authorization. [CI run 43590573645](https://github.com/royliu1105/agent-kernel/actions/runs/43590573645)
passed all four jobs on 2026-11-14. The observability job passed native validators,
**8 full-stack E2E tests in 304.50 s**, cleanup, default `make docker-up`, and
**4 runtime/Web proxy tests**. The separate compose job passed HTTP and monitoring
rehearsals. See the [candidate record](reviews/2026-11-14-cf1-minimal-repair.md)
for all profiles and exact SHA. These disposable runner results do not mean the
maintainer's active Docker images were updated, or that real email is accepted.

References: [observability operations](observability-operations.md),
[backend/SMTP runbook](observability-backends.md),
[pilot plan](real-scenario-pilot-plan.md), [learning guide](pilot-learning-guide.md).
