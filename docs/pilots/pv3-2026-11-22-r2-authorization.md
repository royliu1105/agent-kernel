# PV3 Cohort Authorization — Round 2 full admission (2026-11-22)

Status: **authorized to execute** as a **new** formal 30×2 cohort after:

1. First cohort failed under `MAX_MODEL_CALLS=2`.
2. Same-day re-run (calls=8) cleared A/U but failed I+X (X01 dump / incomplete).
3. Prompt **v2** + X-cohort harness omit-KB fix, plus preflight on A09/A18/X01.
4. Incomplete terminals correlated with output near the **2048** cap.

This admission does not overwrite prior evidence directories.

## Maintainer authorization

- Decision maker: maintainer (`royliu1105`)
- Date: 2026-11-22
- Scope: full frozen 30 questions × 2 Runs (60 attempts); optional smoke;
  GitHub approve/reject drills; scoring; billing reconciliation.
- Prompt: `pv1-runbook-assistant-v2`
  (`f3946b22fc4bbafc7274602ced1342a19e30073e647847ad26872f2b0f7cb783`).
- Models: `deepseek:deepseek-flash`; embedding `text-embedding-v3` / 1024
  (reuse indexed PV3 KB when still valid).
- Budget: remaining under **CNY 200 DeepSeek** + **CNY 200 Aliyun** from the
  earlier top-up. Stop on missing usage, reservation breach, or balance exhaustion.
- Domain reviewer: maintainer.
- Non-goals: PV4–PV6; CF3–CF8; rewriting gold; cherry-picking prior attempts.

## Bound changes (vs 2026-11-22 re-run)

| Setting | Prior re-run | This admission |
| --- | --- | --- |
| `AGENT_KERNEL_MAX_MODEL_CALLS` | 8 | 8 |
| `AGENT_KERNEL_MAX_TOTAL_TOKENS` | 128000 | 128000 |
| `AGENT_KERNEL_MAX_ACTIVE_SECONDS` | 300 | 300 |
| `AGENT_KERNEL_MAX_OUTPUT_TOKENS` | 2048 | **4096** |
| Task prompt | v1 | **v2** |
| Cohort X user task | includes KB id | **omit KB id** (runner) |

Rationale: raise per-response output cap to reduce `model_incomplete_response`
when `finish_reason` is not STOP after long answers; v2 hardens cross-workspace
refuse.

## Evidence isolation

Private evidence: `.agent-kernel/pv3-evidence-r2-20261122/` (gitignored).

## Ledgers

Results: `docs/pilots/pv3-2026-11-22-r2-results.md` (after execution).
Canonical checklist: [real-scenario-pilot-plan.md](../real-scenario-pilot-plan.md) § PV3.
Acceptance only if gates pass on **this** cohort.
