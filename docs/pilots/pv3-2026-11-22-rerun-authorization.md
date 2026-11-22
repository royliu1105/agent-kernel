# PV3 Cohort Re-run Authorization (2026-11-22)

Status: **authorized to execute** as a **new** formal cohort after the first
2026-11-22 run failed quality gates. Prior results remain historical evidence;
this re-run does not overwrite or cherry-pick them.

## Why re-run

The first cohort (`docs/pilots/pv3-2026-11-22-results.md`) recorded A 30/36,
U 8/12, I+X 9/12. Seven attempts ended `execution_model_calls_limit` under the
paid overlay's frozen `AGENT_KERNEL_MAX_MODEL_CALLS=2`. That bound is a
**technical model-round ceiling**, not a DeepSeek/Aliyun balance limit (spend
was ~CNY 2.8 with balance remaining ~CNY 206).

Raising the bound mid-cohort was forbidden. This document is the new recorded
scope decision before any re-run admission.

## Maintainer authorization

- Decision maker: maintainer (`royliu1105`)
- Date: 2026-11-22 (same calendar day; distinct authorization)
- Scope: same frozen 30 questions × **two separate Runs** (60 attempts), same
  prompt hash, DashScope `text-embedding-v3` / 1024 corpus (reuse indexed KB
  when still valid), optional smoke, GitHub approve/reject drills, scoring, and
  billing reconciliation.
- Models: `deepseek:deepseek-flash`; embedding `text-embedding-v3` / Beijing.
- Budget ceiling: remaining envelope under **CNY 200 DeepSeek** + **CNY 200
  Aliyun** from the earlier top-up (stop on missing usage, reservation breach,
  or balance exhaustion). Do not treat prior spend as zero.
- Domain reviewer: maintainer.
- Explicit non-goals: PV4/PV5/PV6; CF3–CF8; rewriting frozen gold after seeing
  model answers; claiming the first cohort passed.

## Bound changes (relative to first paid overlay)

| Setting | First cohort | This re-run |
| --- | --- | --- |
| `AGENT_KERNEL_MAX_MODEL_CALLS` | `2` | **`8`** |
| `AGENT_KERNEL_MAX_TOTAL_TOKENS` | `32000` | **`128000`** |
| `AGENT_KERNEL_MAX_ACTIVE_SECONDS` | `120` | **`300`** |
| `AGENT_KERNEL_MAX_TOOL_CALLS` | `8` | `8` (unchanged) |
| `AGENT_KERNEL_MAX_OUTPUT_TOKENS` | `2048` | `2048` (unchanged) |

Rationale: two model rounds were insufficient for retrieve-then-answer paths
that dominated empty failures. Token/time ceilings are raised so the higher
round budget is usable; they remain execution bounds, **not** a monetary cap.

## Evidence isolation

Private evidence for this re-run lives under
`.agent-kernel/pv3-evidence-rerun-20261122/` (gitignored). The first cohort's
`.agent-kernel/pv3-evidence/` is retained unchanged.

## Runtime session

- Agent / KB: recorded in the re-run `session.json` when execution starts
  (prefer reusing the prior PV3 agent/KB if still indexed).
- Prompt: `docs/pilots/prompts/pv1-runbook-assistant-v1.txt`
  (`bf6c5329a3e3bfa8587947b53a904fe4c3193444ad1f24a947305f163b1b091b`).

## Relationship to ledgers

Canonical checklist:
[real-scenario-pilot-plan.md](../real-scenario-pilot-plan.md) § PV3.
Results for this admission: `docs/pilots/pv3-2026-11-22-rerun-results.md`
(created after execution). Acceptance is ticked only if scoring gates pass on
**this** cohort.
