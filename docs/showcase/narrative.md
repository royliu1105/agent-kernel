# Showcase Narrative

Status: **operator / interview talking points** (2026-11-22). This is how to
explain the completed demo goals. PV3 quality gate is **closed on R4 (v2)**;
this narrative is still not full-pilot (PV5) or shared-user admission.

Lead with the engineering story: durable Run → human approval → explicit resume
→ one tool effect. Then name the trust boundary. Only then mention the paid
GitHub continuation as a separate, authorized observation.

## One-minute arc

```text
1. Mock happy-path     durable execution + approval gate (no paid keys)
2. CF1 memory boundary untrusted context ≠ authorization
3. Paid continuation   DeepSeek → approve → GitHub lookup succeeded once
```

| Beat | What to show | What not to claim |
| --- | --- | --- |
| Mock | `make docker-showcase-up` then `make showcase-happy-path`; evidence under `.agent-kernel/showcase-evidence/` | Not real GitHub; not PV pass |
| CF1 | Instruction-like memory still waits on approval; SYSTEM policy + untrusted USER JSON | Not “models ignore injection”; not multi-user isolation |
| Paid | Run `65050ea0-…` succeeded after approval `52ac5ddb-…` | Not full 30-case PV3; not billing proof; historical CI only |

Optional mock add-on (same showcase overlay): TraceId log lookup + fault KB with
refuse-when-thin — see [troubleshooting-mock](troubleshooting-mock.md)
(`make showcase-troubleshooting`). Not one of the three interview beats above.

## Beat 1 — Mock happy-path

**Point:** the product is a workbench with a durable Run lifecycle, not a chat
log that silently calls tools.

**Do:** start the showcase overlay, run the one-command rehearsal, open the
evidence JSON. Call out: queue → `waiting_approval` → approve (still no side
effect) → resume → tool once → succeeded.

**Evidence:** [mock-happy-path](mock-happy-path.md),
[clean-machine results](clean-machine-rehearsal-results.md).

## Beat 2 — CF1 memory boundary

**Point:** stored memory can influence wording, but it does not grant tool
rights. Execution stays behind static policy + persisted approval + original
arguments.

**Do:** in the happy-path, note the instruction-like memory item; the inventory
tool still paused until resume. Separately, say maintainer R01–R11 disposition
for the bounded local path is recorded (2026-11-22).

**Evidence:** [memory-context-safety](../specs/memory-context-safety.md),
[cf1-risk-disposition](../reviews/cf1-risk-disposition.md),
[CF1 repair](../reviews/2026-11-14-cf1-minimal-repair.md).

## Beat 3 — Paid approve→resume

**Point:** the same gate works when the model is DeepSeek and the tool is the
pinned public GitHub CI lookup—not only with mock MCP.

**Do:** cite Run `65050ea0-1a4f-4924-a795-64027f624d45`, approval
`52ac5ddb-f8bc-4e51-9f40-1e7ada75e9f2`, pin `a1b24653…`, historical run
`43634747295` / `conclusion=success`. Stress: historical record ≠ current
deploy status; answer marked the tool result untrusted.

**Evidence:** [local-paid-experience](../local-paid-experience.md)
(Successful Paid Approve→Resume). Private summary (gitignored):
`.agent-kernel/external-response-review/paid-github-resume-20261122.json`.

## Where this sits on the ledgers

| Ledger | State after these demos |
| --- | --- |
| PV2 bounded rehearsal | Closed (offline + Web + CF1 disposition) |
| CF1 bounded path | Disposition + intended local Docker check recorded |
| PV3 formal cohort | Closed on R4 (v2): A 33/36, U+I+X 12/12 — [pv3-closure](../pilots/pv3-closure.md) |
| PV4 ops | Closed 2026-11-22 — [pv4-closure](../pilots/pv4-closure.md) |
| CF3–CF8 | Deferred / conditional — not part of this narrative |

Canonical ledgers:
[real-scenario-pilot-plan](../real-scenario-pilot-plan.md),
[reference-follow-up-plan](../reference-follow-up-plan.md).

## Suggested speaking order (≈3 minutes)

1. “Workbench, not chat: Runs are durable and tools need human resume.”
2. “Memory is untrusted data in the prompt; approval is the execution gate.”
3. “We also ran the gate once with DeepSeek and a pinned GitHub lookup; that
   proves the paid path, not pilot quality or billing.”
4. If asked about formal live acceptance: PV3 (R4) and PV4 ops are **closed**
   (2026-11-22). That is not PV5 independent-user admission.
