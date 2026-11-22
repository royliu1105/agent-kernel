# PV5 / PV6 Pending (paused)

Status: **deferred by maintainer 2026-11-22** — not blocked by missing PV2–PV4
gates. Resume when independent participants are available.

Canonical ledger: [real-scenario-pilot-plan.md](../real-scenario-pilot-plan.md).

## Why paused

PV5 needs two people who did not implement the workflow, plus consent, dates,
and deployment/data approval. That human intake is not ready yet.

## When resuming — PV5 checklist

1. Name two independent participant aliases; record consent, availability,
   private incident contact, start/end dates, ≥3 distinct active-use days.
2. Record full-pilot entry sign-off and closure/deletion schedule (closes the
   remaining PV1 human fields).
3. Write `docs/pilots/pv5-YYYY-MM-DD-authorization.md` (scope, budget, stop
   rules, environment).
4. Provision scoped access + frozen onboarding instructions only.
5. Both participants: access → first result within 45 minutes; log all help.
6. ≥20 real user tasks (≥5 each), across ≥3 days; **exclude** scripted PV3 cases.
7. Per task: intent, usable?, corrections, citations, approval UX, time, cost,
   support needed.
8. Session budget/safety review; stop on safety conditions.

**Pass:** both onboard in 45 minutes without code edits/undocumented commands;
≥80% of ≥20 tasks usable without material correction or maintainer intervention
(expected approvals ≠ intervention).

## After PV5 — PV6 checklist

1. Sanitized report with denominators, failures, cost unknowns, config/evidence.
2. Classify findings; disposition owners.
3. Reprioritize CF3–CF8 from observed need (separate scope to start any).
4. Confirm safety fixes have regression/CI before closing if code changed.
5. Maintainer decision: proceed in scope / extend trial / stop; name ops owner.
6. Revoke temp access; retention/deletion; final bill; archive sanitized evidence.
7. Release (if any) needs **separate** authorization — pilot report ≠ release.

## Explicitly not required to reopen PV4

- S3/MinIO restore (local-object candidate N/A)
- Paid provider-outage drill (optional later authorization only)
