# Guided Learning During Pilot Acceptance

Status: **Mechanism documented; CF1/CF2 demonstrations recorded, independent learner
practice not established; PV1 planning started, PV2-PV6 sessions not started (2026-11-15)**.

The [PV1 draft](pilots/pv1-2026-11-15-runbook-assistant.md) records scenario and
budget decisions plus pending model/data/participant gates. Choosing an option
does not establish independent diagnostic or test-design proficiency.

The pre-pilot [CF1 review](reviews/2026-11-14-cf1-memory-boundary.md) records a
maintainer-requested demonstration of assertions and temporary fixture checks.
It does not establish learner mastery or technical acceptance of CF1.
The later [CF2 API/CLI rehearsal](reviews/2026-11-14-cf2-workflow-inventory.md#remaining-gates-and-learning)
records the requested approval/effect/persistence demonstration. It is not an
independent learner assessment or a completed PV2 session.
The [rejected-approval repair demonstration](reviews/2026-11-14-approval-rejection-repair.md#learning-note)
extends this evidence with transaction visibility, injected rollback, safe retry
and timeline mutation tests. It does not establish independent learner mastery.

Use this guide alongside the [PV1-PV6 pilot plan](real-scenario-pilot-plan.md).
It defines how Codex and the maintainer work together, not another feature
backlog, course, day schedule or release gate. The maintainer has asked for
guided understanding of design tradeoffs, fault diagnosis and test verification,
not just completed tasks. No personal proficiency is inferred from project size.

## Collaboration Contract

- Default to Chinese explanations. Define unfamiliar English terms once and
  use small Python examples from the actual path. Node.js/TypeScript analogies
  can help, but explain where runtime, concurrency or typing semantics differ.
- Orient the learner using one relevant spec and at most 1-3 initial source/test
  files. Follow the execution path incrementally; do not dump the whole repository.
- Choose one main learning question per meaningful work unit, not a quiz for
  every command. Keep the checkpoint brief and adapt depth to the learner's needs.
- Explain before an important decision or repair, not only after completing it.
  Invite one concrete prediction, hypothesis, evidence choice or test assertion.
- At that checkpoint, wait for the learner's response before revealing the full
  diagnosis or carrying out the same exercise. Independent safe preparation may
  continue, but do not complete the learning step silently in the background.
- If the learner is unsure, offer a hint and a smaller question. If they request
  a demonstration or faster execution, demonstrate and record that assistance.
  Silence, assent or a generic "continue" is not evidence of understanding.
  Do not force repeated quizzes; if the learner chooses to proceed, leave the
  unverified learning outcome open rather than blocking routine work indefinitely.
- AI assistance is allowed. Independence means the learner can make and explain
  the relevant judgment, not that they must write every line without tools.
- During a real safety incident, contain the risk first, then teach from sanitized
  evidence. Never prolong exposure or withhold a needed fix for a teaching moment.

This mechanism does not authorize paid requests, destructive drills, invitations,
deployment, commit/push, new features or release actions. The pilot's approvals,
scope freeze, privacy requirements and stop conditions remain authoritative.

## Working Loop

| Step | Codex responsibility | Learner participation / evidence |
| --- | --- | --- |
| 1. Orient | Name the PV task, user outcome, relevant path and invariant. Separate known facts from assumptions. | Restate what must remain true; ask about unfamiliar Python/domain concepts. |
| 2. Compare | Describe the current choice, one viable alternative, costs and the condition that would justify changing it. Do not expand scope. | Choose or challenge the tradeoff and predict a failure case. |
| 3. Investigate | Present a small symptom/evidence set. Ask for a hypothesis and the next safe observation before giving the root cause. | Suggest a discriminating check and say what result would support or refute the hypothesis. |
| 4. Verify | Identify the test boundary and meaningful assertions before repair; review results together afterward. | Propose an assertion or minimal test/repair, run or interpret it, and explain why it proves the intended property. |
| 5. Explain Back | Ask for a short explanation in the learner's own words and one changed-condition question. Correct gaps with evidence, not a grade alone. | Explain why this works, what it does not guarantee, and what would change if a condition changed. |
| 6. Record | Summarize project evidence and learning evidence separately, including assistance and one remaining question. | Confirm the summary reflects what was actually practiced. |

Use only the relevant steps for the current task. A scope/budget discussion does
not need an invented incident or a code edit. For a real blocker, let the learner
lead a bounded part of the diagnosis/test/repair when they are ready; Codex can
handle routine setup and explain the resulting diff. Keep safety checks intact.

## Three Practice Standards

### Design Tradeoffs

An explanation should identify the user requirement, protected invariant,
current mechanism, reasonable alternative and limitation. It should answer
"when would we choose differently?", not just recite component names.

Example question: why is PostgreSQL the source of truth while Redis supplies
scheduling hints? Ask the learner to predict the result of losing a hint and
locate the polling/ownership path before explaining the full behavior.
Use [backend operations](backend-operations.md) and
[Worker execution](../packages/kernel-runtime/src/kernel_runtime/worker.py).
This discussion does not propose replacing the queue or database.

### Fault Diagnosis

Use the sequence: symptom -> competing hypotheses -> distinguishing evidence
-> minimal reproduction -> supported cause -> smallest safe repair or operator
action. Preserve the initial hypothesis and explain why it was revised.

For a stuck Run, distinguish queued, running and waiting-for-approval states;
inspect scoped status/events, ownership and relevant logs rather than blindly
restarting or replaying an external action. Ask which observation distinguishes
a missing scheduling hint from an approval wait or expired owner.
Use [execution ownership](execution-ownership.md),
[runtime execution](../packages/kernel-runtime/src/kernel_runtime/execution.py)
and [storage repositories](../packages/kernel-storage/src/kernel_storage/repositories.py).
Do not present a suspected cause as confirmed without evidence.

### Test Verification

The learner should identify setup, stimulus, expected outcome and the assertion
that would catch the defect. Distinguish unit, integration, real-backend, live
model and human-pilot evidence; a mock success is not remote-service proof.

For an actual repair, demonstrate that the regression fails on the defective
behavior for the intended reason and passes after the minimal fix. Verify the
important negative case too: repeated resume must not invoke the tool again,
and rejected approval must not invoke it at all. An exit-code assertion or a
green suite alone does not prove those effects; inspect downstream counters,
persisted call IDs/events and ownership where appropriate.

Use [bounded-execution contracts](../tests/integration/test_bounded_native_execution.py),
[checkpoint contracts](../tests/integration/test_execution_checkpoint_storage.py)
or [backoff contracts](../tests/integration/test_runtime_backoff.py). The learner
can design an assertion first; Codex can help with pytest/async syntax afterward.
Explain which test failed, why it failed and which broader gate is still needed.

If there is no real defect, inspect an existing negative regression or use an
explicitly agreed disposable fixture/copy. Do not break the main branch or an
active pilot, manufacture a production incident, or add a feature just to create
homework. Label deliberate fault injection; never report it as an observed defect.

## Learning Focus by Pilot Gate

These are exercises within the existing tasks, not a second completion checklist.

| Gate | Main judgment to practice | Small observable exercise |
| --- | --- | --- |
| PV1 | Scope, risk and evidence boundaries | Explain why estimated cost is not an invoice cap; choose a permitted scenario and defend one exclusion. |
| PV2 | State transitions, permissions and approval | Trace one run from queue to approval/resume; predict a rejection or repeated-resume result and identify the proving assertion. |
| PV3 | Retrieval versus generation failure | Inspect a wrong or unsupported answer, separate retrieval evidence from synthesis, and score citations before changing prompts. |
| PV4 | Ownership, recovery and data consistency | Form a hypothesis for a disposable fault, choose a discriminating observation, and explain what the restore/checkpoint evidence does not prove. |
| PV5 | Usability versus engineering correctness | Observe a participant without coaching, classify one issue, then explain why green backend tests did not guarantee task usability. |
| PV6 | Evidence-based release decisions | Present a scoped go/no-go using failures, denominators and unresolved risks, and propose the smallest justified follow-up. |

For PV5, coaching the maintainer must happen before or after the independent
participant attempt. Do not coach participants through a scored onboarding/task
and count it as unassisted success. Record any intervention in the pilot outcome.

## Separate Evidence Tracks

Project acceptance and learner practice are separate tracks. A task can satisfy
its technical gate while the related learning remains unpracticed; report both.
Learning success cannot waive a failed project safety or acceptance gate. Operator
competence required by the pilot still needs its own demonstrated evidence.

Record observed practice, not a blanket skill rating:

| Learning status | Evidence required |
| --- | --- |
| Not practiced | No learner attempt yet; this is the initial state. |
| Demonstrated by Codex | Codex explained/executed it; learner participation has not been established. |
| Practiced with guidance | Learner attempted a judgment/test/explanation with recorded hints or corrections. |
| Observed independent on this task | Learner made and justified the judgment, selected/interpreted evidence and answered a changed-condition question without step-by-step solution prompts. |
| Revisit | A misconception or unresolved question remains; record the next small exercise. |

Syntax lookup and AI/tool use do not by themselves disqualify independence.
One successful exercise is not proof of general mastery or senior-expert status.
Do not mark understanding complete because CI passed, the learner said "OK",
or Codex supplied a good explanation. Never write a learner answer on their behalf.

## Session Record and Handoff

Append a short learning note to the existing sanitized
`docs/pilots/<pilot-id>.md` record once PV1 starts. No separate learning database,
task board, new curriculum or execution record is created by this document.
Use no private user prompts, credentials or unsanitized incident payloads.

```text
PV task / date / candidate SHA:
Project result and evidence (pass/fail/blocked, with run/test references):
Concept / initial learner prediction or hypothesis:
Source/test references / observation that confirmed or changed the hypothesis:
Learner contribution / hints or demonstration provided:
Assertion / failure-before and pass-after evidence, or existing-test-only review:
Learner explanation / changed-condition question and observed response:
Learning status / remaining misconception / next small exercise:
```

Keep notes proportional: a few lines per work unit, not a transcript. Do not
publish personal learning notes without the learner's agreement; keep them
private if preferred and link only an approved summary in shared pilot evidence.

Each work-session close-out states: what the project verified, what the learner
actually practiced, and what remains to understand. At the next session, read the
last note and revisit one unresolved point rather than restarting a lecture.
At the original planning checkpoint no learning session had occurred. The later
CF1 demonstration is linked above; no independent learner proficiency is claimed.
