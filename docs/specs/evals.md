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

## Day 28 RAG Eval Dataset Foundation

Day 28 adds the first file-backed eval dataset path:

- JSON RAG eval dataset format.
- Dataset-level `name`.
- Non-empty `cases` array.
- Case fields mapped to `RagEvalCase`.
- Readable validation errors through `EvalDatasetError`.
- File-backed loader: `load_rag_eval_dataset(path)`.
- Dataset runner helper: `RagEvalDataset.run(retrieve)`.

Supported Day 28 case fields:

```json
{
  "name": "deployment",
  "query": "alpha deployment rollback checklist",
  "top_k": 1,
  "min_results": 1,
  "max_results": 1,
  "min_top_score": 0.0,
  "top_result_must_contain": ["deployment", "rollback"],
  "citation_source_uri_must_contain": ["deploy.md"],
  "all_results_require_citations": true,
  "expect_empty": false,
  "expected_error_type": null
}
```

Day 28 intentionally does not implement YAML loading, full eval API, full eval
CLI, persisted eval runs, LLM-as-judge, agent behavior evals beyond deterministic
RAG retrieval, public benchmark datasets, or Web UI eval reports.

## Day 29 Eval Report and Cheap CI Eval

Day 29 adds the first CI-runnable eval report path:

- Stable JSON-compatible eval report serialization.
- Local CLI command: `agent-kernel eval report <dataset.json>`.
- Default non-zero exit code for failing reports.
- Cheap deterministic RAG eval fixture at `evals/rag-smoke.json`.
- Makefile target: `make cheap-eval`.
- GitHub Actions cheap eval step.

Day 29 intentionally does not implement full eval API, persisted eval runs,
LLM-as-judge, real-model CI evals, full agent behavior evals, or Web UI eval
reports.

## Day 47 Behavior Eval Coverage Expansion

Day 47 expands deterministic RAG behavior assertions without adding an eval
platform or persisted eval runs.

Additional supported RAG case fields:

- `max_results`: optional upper bound for result count. This protects `top_k`
  behavior from accidentally returning too many chunks.
- `min_top_score`: optional minimum score for the top result. This catches
  obvious scoring regressions while keeping thresholds dataset-owned.
- `citation_source_uri_must_contain`: optional list of terms that each result's
  citation source URI must include.

Additional Day 47 assertions:

- Maximum retrieved result count.
- Minimum top-result score.
- Citation source URI contains required terms.

Day 47 intentionally does not implement persisted eval runs, an eval API,
LLM-as-judge, real-model CI evals, Web eval authoring, or release-blocking eval
suites.

## Day 67 Provider-Native Tool-Call Eval Foundation

Day 67 adds a deterministic eval runner for provider-native tool-call behavior:

- `ToolCallEvalToolCall`: one observed tool call from a runtime, replay, or
  external harness.
- `ToolCallEvalObservation`: one observed run outcome with status, output,
  error type, timeline events, tool calls, and optional model-call count.
- `ToolCallEvalCase`: expected behavior for one agent/tool-call scenario.
- `ToolCallEvalRunner`: async runner that executes cases and returns the same
  `EvalReport` shape used by existing evals.

Implemented Day 67 assertions:

- Run status.
- Error type.
- Tool-call count.
- Tool name.
- Tool status.
- Provider tool-call id.
- Timeline event sequence.
- Model-call count.
- Presence of `output.provider_tool_loop`.
- Required output content terms.

The first runtime-backed regression cases cover:

- Safe provider-native tool call completes a model/tool/model run.
- Approval-required provider-native tool call pauses at `waiting_approval`.
- Unknown provider-native tool call fails safely before a follow-up model call.

Day 67 intentionally does not implement persisted eval runs, eval API endpoints,
eval Web views, LLM-as-judge, live-provider evals, or release-blocking eval
suites. Those remain part of later Beta and v1.0 hardening.

## Day 74 Persisted Eval Runs and API

Day 74 adds the first durable eval platform boundary:

- `EvalRun` domain model with status, pass/fail counts, full report JSON,
  metadata, trace ID, and timestamps.
- `eval_runs` storage table and repository.
- `POST /v1/evals/runs` to persist an eval report.
- `GET /v1/evals/runs` to list recent eval runs.
- `GET /v1/evals/runs/{eval_run_id}` to inspect one eval run.
- CLI `agent-kernel eval report <dataset.json> --publish` to run the existing
  deterministic local RAG eval and publish the report through the API.
- Web Workbench eval view loads persisted eval runs through a same-origin route
  and renders live report summaries and case details when available.

Day 74 intentionally does not execute arbitrary eval datasets on the server,
upload dataset files, schedule eval jobs, run LLM-as-judge, execute live-provider
evals by default, or enforce release-blocking eval suites.

## API / CLI

Expected API:

```http
POST /v1/evals/runs
GET  /v1/evals/runs
GET  /v1/evals/runs/{eval_run_id}
```

Expected CLI:

```bash
agent-kernel eval report evals/rag-smoke.json
agent-kernel eval report evals/rag-smoke.json --publish
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
