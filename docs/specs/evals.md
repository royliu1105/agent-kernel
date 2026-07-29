# Feature Spec: Evals

## Goal

Provide a deterministic and repeatable evaluation system for agent behavior, regressions, tool use, citations, step count, latency, and cost.

## Non-Goals

- Full benchmark platform in v0.1.
- Heavy LLM-as-judge dependency for default CI.
- Public leaderboard.
- Complex experiment tracking platform.

## User Stories

- As a maintainer, I can run behavior evals before merging changes.
- As a developer, I can catch tool-calling regressions.
- As an operator, I can compare cost and latency changes.
- As a prompt author, I can see whether a prompt version caused behavior drift.

## Domain Model

Initial entities:

- `EvalDataset`
- `EvalCase`
- `EvalRun`
- `EvalCaseResult`
- `EvalAssertion`
- `EvalReport`

Dataset format:

```text
YAML or JSONL
```

## State Transitions

Eval run lifecycle:

```text
created -> running -> succeeded
created -> running -> failed
created -> running -> canceled
```

Detailed assertion semantics will be completed during Phase 4 implementation.

## Phase 3B RAG Behavior Eval Foundation

Day 21 introduces a small deterministic eval foundation before the full Phase 4 eval platform:

- `EvalAssertionResult`: one assertion outcome with a readable message.
- `EvalCaseResult`: one case outcome with assertion results and optional error details.
- `EvalReport`: aggregate report with pass/fail counts.
- `RagEvalCase`: retrieval-specific deterministic eval case.
- `RagEvalRunner`: executes cases against a retrieval callable.

Implemented Day 21 RAG assertions:

- Minimum retrieved result count.
- Top result contains required terms.
- Retrieved results include valid citations.
- Empty knowledge base returns no results.
- Expected retrieval errors are reported deterministically.

Day 21 deliberately does not implement full eval API, full eval CLI, persisted eval runs, LLM-as-judge, cost/latency dashboards, or public benchmark datasets.

## API / CLI

Expected API:

```http
POST /v1/evals/datasets
GET  /v1/evals/datasets
POST /v1/evals/runs
GET  /v1/evals/runs/{eval_run_id}
```

Expected CLI:

```bash
agent-kernel eval run ./evals/research.yaml --agent <agent-id>
agent-kernel eval report <eval-run-id>
```

## Failure Modes

- Eval dataset is invalid.
- Mock replay transcript is missing.
- Expected tool call differs.
- Required citation missing.
- Step count exceeds limit.
- Cost exceeds limit.
- Agent run fails.

## Security

- Eval datasets should not include secrets.
- Eval reports should redact sensitive inputs where configured.
- Real-model evals should be optional and not required for default CI.

## Observability

- Eval run status.
- Case latency.
- Case cost.
- Pass/fail summary.
- Assertion failures.
- Linked run IDs.

## Test Plan

- Valid dataset loads.
- Invalid dataset fails clearly.
- Mock provider eval passes.
- Expected tool call assertion works.
- Forbidden behavior assertion works.
- Max cost and max step assertions work.

## Acceptance Criteria

- Evals can run through CLI.
- Reports show pass/fail and failure reasons.
- CI can run cheap deterministic evals.
- Eval results include cost and latency summaries.
