# PV4 Closure — Operations for This Deployment

Date: **2026-11-22**. Status: **PV4 ops gate closed** on the admitted local
Docker candidate. Canonical checklist:
[real-scenario-pilot-plan.md](../real-scenario-pilot-plan.md) § PV4.

This closes the **user-admission blocker** for recovery/upgrade/bounded-load
evidence on the same candidate family as PV2/PV3. It is **not** PV5
independent-user admission or full-pilot (PV6) closure.

## Accepted admission

| Field | Value |
| --- | --- |
| Authorization | [pv4-2026-11-22-authorization.md](pv4-2026-11-22-authorization.md) |
| Results | [pv4-2026-11-22-results.md](pv4-2026-11-22-results.md) |
| Profile | `agent-kernel-local` mock + disposable drill PostgreSQL/Redis |
| Storage | PostgreSQL/pgvector + local objects (not S3) |
| Private evidence | `.agent-kernel/pv4-evidence-20261122/` |
| Decision maker | maintainer (`royliu1105`) |

## Gates

All five PV4 checklist items passed on 2026-11-22 (restart 43 s; backup ~3.9 s;
upgrade/rollback ~1.4 s; quick mock soak 25/25; Redis-hint recovery 3/3). See
results for measurements and non-claims.

## Follow-on

Next ledger blocker for full pilot claim: **PV5** (two independent participants
and dates). Optional: paid provider-outage drill under a new authorization if
desired; not required to reopen PV4 for the mock local-object candidate.
