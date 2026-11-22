# PV3 Cohort Authorization — Round 3 (2026-11-22)

Status: **authorized to execute** as a **new** formal 30×2 cohort using task
prompt **v3** after R2 cleared terminal/U/I+X but failed A at 32/36.

Prior admissions remain historical; this run does not overwrite their evidence
dirs or cherry-pick cells.

## Maintainer authorization

- Decision maker: maintainer (`royliu1105`)
- Date: 2026-11-22
- Scope: full frozen 30 × 2 Runs; optional smoke; GitHub approve/reject drills;
  scoring; billing reconciliation.
- Prompt: `pv1-runbook-assistant-v3`
  (`70fbf3e26ce99243991e4063a078d5d0b5d6f4312eea45cf1a2154be3bf70e02`).
  This is the **pilot task system instruction** for the runbook-assistant
  candidate, not a change to Agent Kernel built-in product prompts.
- Models: `deepseek:deepseek-flash`; reuse DashScope-indexed PV3 KB when valid.
- Bounds (unchanged from R2 paid overlay):
  `MAX_MODEL_CALLS=8`, `MAX_OUTPUT_TOKENS=4096`, `MAX_TOTAL_TOKENS=128000`,
  `MAX_ACTIVE_SECONDS=300`; cohort X omits `knowledge_base_id` in the runner.
- Budget: remaining under **CNY 200 DeepSeek** + **CNY 200 Aliyun**.
- Domain reviewer: maintainer.
- Non-goals: PV4–PV6; rewriting gold; claiming R2 passed; implying arbitrary
  user prompts match this candidate without shipping the prompt as a template.

## Evidence isolation

`.agent-kernel/pv3-evidence-r3-20261122/` (gitignored).

## Ledgers

Results after execution: `docs/pilots/pv3-2026-11-22-r3-results.md`.
Canonical checklist: [real-scenario-pilot-plan.md](../real-scenario-pilot-plan.md) § PV3.
