# PV3 Closure — Live Model/Embedding Cohort

Date: **2026-11-22**. Status: **PV3 quality gate closed** on admission **R4**
(prompt `pv1-runbook-assistant-v2`). Canonical checklist:
[real-scenario-pilot-plan.md](../real-scenario-pilot-plan.md) § PV3.

This closes the **effectiveness** gate for the frozen 30×2 cohort under the
admitted paid profile. It is **not** PV4 ops drills, PV5 user admission, or
full-pilot (PV1 human fields + PV6) closure.

## Accepted admission

| Field | Value |
| --- | --- |
| Authorization | [pv3-2026-11-22-r4-authorization.md](pv3-2026-11-22-r4-authorization.md) |
| Results | [pv3-2026-11-22-r4-results.md](pv3-2026-11-22-r4-results.md) |
| Prompt | `pv1-runbook-assistant-v2` / `f3946b22fc4bbafc7274602ced1342a19e30073e647847ad26872f2b0f7cb783` |
| Models | `deepseek:deepseek-flash` + DashScope-indexed frozen corpus |
| Bounds | `MAX_MODEL_CALLS=8`, `MAX_OUTPUT_TOKENS=4096`, `MAX_TOTAL_TOKENS=128000`, `MAX_ACTIVE_SECONDS=300`; X omits KB id |
| Private evidence | `.agent-kernel/pv3-evidence-r4-20261122/` (gitignored) |
| Decision maker | maintainer (`royliu1105`) |

## Gates (R4)

| Gate | Result | Required |
| --- | --- | --- |
| Terminal cohort | 60/60 succeeded | record all attempts |
| A answerable | 33/36 | ≥33/36 |
| U missing-evidence | 12/12 | 12/12 |
| I+X safety | 12/12 | 12/12 |
| Approval drills | approve→resume succeeded; reject → `approval_rejected` | exercised |
| Billing | R4 tariff label ~CNY 2.97; balance CNY 199.38; same-day wallet Δ ~7.38; see [billing-reconciliation-2026-11-22](billing-reconciliation-2026-11-22.md) | reconciled with unknowns |

Scoring: assistant draft, maintainer-accepted for gate closure on 2026-11-22.
Fails retained (not cherry-picked): A09-a1, A09-a2, A18-a2.

## Explicit non-claims

- Earlier same-day admissions (first / re-run / R2 / R3) remain historical
  evidence only; **R4 is the accepting profile**.
- Prompt **v3** was tried and regressed; it is **not** the accepted instruction.
- Does not rewrite frozen gold (`pv1-materials`) or claim PV4/PV5/PV6.
- Console day-line / Aliyun itemized lag remain labeled unknowns, not zero
  (maintainer reconciliation pass 2026-11-22 documented the DeepSeek wallet
  series and the tariff-label vs wallet mismatch).

## Follow-on

Next blockers on the ledger: **PV4** (ops/recovery/load) and **PV5**
(independent participants). Re-run the full 30×2 only for material
model/prompt/retrieval/runtime changes; do not reopen PV3 by re-scoring R4
cells selectively.
