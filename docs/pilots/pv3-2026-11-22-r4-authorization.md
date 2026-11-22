# PV3 Cohort Authorization — Round 4 (2026-11-22)

Status: **executed and accepted** (PV3 quality gate closed 2026-11-22 on this
admission). See [pv3-2026-11-22-r4-results.md](pv3-2026-11-22-r4-results.md) and
[pv3-closure.md](pv3-closure.md).

Authorized as a **new** formal 30×2 cohort **returning to prompt v2** after R3
(v3) regressed. R2 remains prior observation only; this admission did not
overwrite R2/R3 evidence dirs.

## Maintainer authorization

- Decision maker: maintainer (`royliu1105`)
- Date: 2026-11-22
- Scope: full frozen 30 × 2; optional smoke; GitHub approve/reject drills;
  scoring; billing reconciliation.
- Prompt: `pv1-runbook-assistant-v2`
  (`f3946b22fc4bbafc7274602ced1342a19e30073e647847ad26872f2b0f7cb783`).
  Pilot **task** system instruction only (not a product built-in prompt change).
- Explicitly **not** using v3 for this admission.
- Models: `deepseek:deepseek-flash`; reuse DashScope-indexed PV3 KB when valid.
- Bounds (same as R2 paid overlay): `MAX_MODEL_CALLS=8`,
  `MAX_OUTPUT_TOKENS=4096`, `MAX_TOTAL_TOKENS=128000`, `MAX_ACTIVE_SECONDS=300`,
  `MAX_HISTORY_BYTES=262144`; cohort X omits `knowledge_base_id` in the runner.
- Budget: remaining under **CNY 200 DeepSeek** + **CNY 200 Aliyun**.
- Domain reviewer: maintainer.
- Non-goals: PV4–PV6; rewriting gold; treating R3 as preferred; cherry-picking.

## Evidence isolation

`.agent-kernel/pv3-evidence-r4-20261122/` (gitignored).

## Ledgers

Results: `docs/pilots/pv3-2026-11-22-r4-results.md` (after execution).
Canonical checklist: [real-scenario-pilot-plan.md](../real-scenario-pilot-plan.md) § PV3.
