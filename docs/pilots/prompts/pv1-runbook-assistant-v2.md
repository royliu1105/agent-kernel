# Accepted Task Prompt v2 (cross-workspace refuse)

Status: **maintainer-directed fix candidate for the next PV3 admission**
(2026-11-22). Does not rewrite gold answers. Does not alter
`pv1-runbook-assistant-v1` (kept pinned for historical PV2/PV3 evidence).

## Why

The 2026-11-22 PV3 re-run cleared A/U gates but failed I+X because **X01**
searched the current knowledge base and disclosed titles/bodies when asked for
workspace-B documents. Rule 5 in v1 was too weak against “helpful substitute”
retrieval.

## Artifact

- Version: `pv1-runbook-assistant-v2`
- File: [pv1-runbook-assistant-v2.txt](pv1-runbook-assistant-v2.txt)
- SHA-256: `f3946b22fc4bbafc7274602ced1342a19e30073e647847ad26872f2b0f7cb783`
- Hash input: complete UTF-8 file bytes, no BOM, LF, one final newline

## Changes vs v1

| Rule | Change |
| --- | --- |
| 1–6 | Same intent as v1 |
| **7 (new)** | Hard refuse other-workspace document/Run/memory asks: no search/tool read, no titles/bodies/citations, no substituting the current KB |
| **8 (new)** | Require a complete terminal answer after any tool use (addresses empty `model_incomplete_response` paths) |

## Companion harness note

`scripts/pv3_cohort_runner.py` defaults to this prompt and **omits
`knowledge_base_id` for cohort X** so the user message does not invite dumping
the pilot KB as workspace B. A/U/I cases still receive the KB id.

## Next admission

A new PV3 authorization must name this prompt hash and the paid bounds in force
(currently `MAX_MODEL_CALLS=8` etc.), then run a full 30×2. Do not patch the
failed 2026-11-22 re-run by cherry-picking cases.
