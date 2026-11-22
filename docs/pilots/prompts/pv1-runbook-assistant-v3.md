# Accepted Task Prompt v3 (complete multi-constraint answers)

Status: **maintainer-directed agent-instruction fix** for the next PV3
admission (2026-11-22 evening). Does **not** change gold answers, corpus, or
paid monetary ceilings.

## What is being optimized

| Layer | Changed? |
| --- | --- |
| **Agent task prompt (system instruction)** | **Yes — this file / v3.txt** |
| Runtime bounds (`MAX_*`) | No (keep R2: calls=8, output=4096, …) |
| Reviewer gold / questions | No |
| Scoring gates | No |
| Cherry-pick failed cells | No |

R2 cleared terminal stability and U/I+X; A failed at 32/36 because some answers
omitted material second-half constraints (credential don’ts, resume count
checks, default Mailpit vs external). v3 tightens **answer completeness**
behavior of the assistant instruction.

## Artifact

- Version: `pv1-runbook-assistant-v3`
- File: [pv1-runbook-assistant-v3.txt](pv1-runbook-assistant-v3.txt)
- SHA-256: `70fbf3e26ce99243991e4063a078d5d0b5d6f4312eea45cf1a2154be3bf70e02`
- Hash input: complete UTF-8 file bytes, no BOM, LF, one final newline

## Changes vs v2

| Rule | Change |
| --- | --- |
| 1–8 | Same as v2 |
| **9 (new)** | Multi-constraint answers must cover both “do / don’t”, full countable proof steps (including repeat/concurrent and approval-phase call counts), and default local-capture vs external delivery requirements without contradicting documented defaults |

## Next admission

Name this prompt hash in a new PV3 authorization, then run a full 30×2.
Do not patch R2 by re-scoring cherry-picked retries alone.
