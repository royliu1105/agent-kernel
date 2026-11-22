# PV3 Cohort Authorization (2026-11-22)

Status: **authorized to execute**; results recorded separately under private
evidence and the pilot ledger.

## Maintainer authorization

- Decision maker: maintainer (`royliu1105`)
- Date: 2026-11-22
- Scope: formal PV3 frozen cohort — all 30 questions in
  `docs/pilots/pv1-materials/questions.json`, **two separate Runs each**
  (60 attempts), plus DashScope `text-embedding-v3` indexing of D01–D12,
  optional live smoke, GitHub approve/reject drills, and billing reconciliation.
- Models: `deepseek:deepseek-flash`; embedding `text-embedding-v3` / 1024 / Beijing.
- Budget ceiling: **CNY 200 DeepSeek API** + **CNY 200 Aliyun (DashScope/百炼
  embedding)**. Stop on missing usage, reservation breach, or balance exhaustion.
- Domain reviewer: maintainer (already confirmed in PV1 materials).
- Explicit non-goals: PV4/PV5/PV6; CF3–CF8; rewriting frozen gold after seeing
  model answers.

## Runtime session

Recorded when execution starts (IDs filled by the runner session file):

- Agent / KB: see `.agent-kernel/pv3-evidence/session.json` (gitignored private).
- Prompt: `docs/pilots/prompts/pv1-runbook-assistant-v1.txt`
  (`bf6c5329a3e3bfa8587947b53a904fe4c3193444ad1f24a947305f163b1b091b`).

## Relationship to ledgers

Canonical checklist remains
[real-scenario-pilot-plan.md](../real-scenario-pilot-plan.md) § PV3.
This file only records the spending/scope authorization for the 2026-11-22
cohort run.
