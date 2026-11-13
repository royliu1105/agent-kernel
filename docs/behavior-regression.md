# Behavior Regression and Optional Live Smoke

## Scope and Release Impact

This document covers the P5.1/P5.2 regression tooling in the
[capability hardening plan](capability-hardening-plan.md). It does not certify
that the entire hardening plan or a new release is complete.

The following deliberately separate paths exist:

| Path | Default network/cost | Release impact |
| --- | --- | --- |
| Runtime golden timelines | None; in-memory SQLite and fixture providers/tools | Candidate blocking gate; a behavior mismatch exits 1. |
| OpenAI wire/runtime contracts | None; actual adapter with HTTP mock transport and SQLite | Blocking Python test suite; not a live-provider success claim. |
| Live provider smoke | Disabled unless explicitly enabled | Optional; never part of the default credential-free gate. |
| Cost/latency comparison | Offline reads of two JSON reports | Informational; increases or incomparable samples do not fail a release. |

The commands below are runnable directly. `make release-eval` and its CI step
include the timeline command as a blocking gate. Green local fixtures are not
remote CI evidence.

## Deterministic Timeline Gate

From the repository root after the normal workspace dependency sync:

```bash
uv run python scripts/timeline_regression.py
uv run pytest tests/integration/test_timeline_regression.py tests/unit/test_eval_comparison.py tests/unit/test_live_provider_smoke.py
uv run pytest tests/unit/test_openai_provider.py tests/integration/test_openai_runtime_contract.py
```

The first command is the release-gate entry point. It emits an `EvalReport` JSON
object on stdout with `passed`, case counts and named assertions. Runtime logs
use stderr. Exit codes are 0 for all cases passing, 1 for a behavior/fixture
failure and 2 for an invalid or incomplete golden dataset.

The checked-in contract is `evals/timelines/runtime-v1.json`. No credentials,
existing database, migration history, object store, Redis or external service
are used. Each case builds its own disposable SQLite database. Run UUIDs,
timestamps and execution durations are deliberately absent from the comparison.

The harness invokes the actual execution service and storage repositories; it
does not construct a list of expected events and pass that list off as runtime
output. It reopens sessions to read the committed result. The fixtures are:

| Case | Protected behavior |
| --- | --- |
| `native-tool` | Model/tool/model execution, policy before execution, persisted native call ID and result, exactly two model calls and one tool execution; follow-up messages must carry the original task, call arguments and the actual correlated result. |
| `approval-approved` | No tool invocation before approval, persisted decision, session-reopened resume, exactly one execution after approval. |
| `approval-rejected` | Explicit rejected decision, failed run, no tool side effect or result. |
| `model-retry` | One retryable failure, a retry event with attempt 2, then success without fallback. |
| `model-fallback` | Exhaust primary attempts before selecting backup; preserve attempt count and selected model. |
| `tool-retry` | Read-only transient failure retried once using the same persisted tool-call key. |
| `lease-recovery` | Runtime acquires a lease, injected interruption leaves a running run, expiry recovery fails it once, repeated recovery is a no-op, restarted worker does not replay it. |

All cases check contiguous event sequences and trace correlation. Successful
tool cases also check trusted `ToolExecutionContext.tool_call_id` against the
persisted tool call. These IDs are compared for consistency, not serialized
as a fixed UUID in the golden.

Fixture providers validate the incoming requests before returning a canned
answer. The native follow-up must contain user/assistant/tool messages in that
order, the expected tool call and arguments, and the exact synthetic result.
The internal tool-call UUID is compared with the persisted record; it is not
accepted merely because two request fields agree. Initial/retried/fallback
requests must retain the task and expected tool definitions. These checks run
inside `scripts/timeline_regression.py`, so the CLI gate enforces them too.

The interruption fixture raises a dedicated `BaseException` from the provider
after runtime start. Runtime cleanup immediately expires the lease; the fixture
asserts it is discoverable for recovery without editing persisted lease state.
The actual run events and recovery result come from runtime/storage services.
This is not a process-kill experiment or proof of PostgreSQL claim fencing.
Real multi-process ownership/race contracts remain in the P2/P4 suites.
The helper `_recover_crashed_run` isolates the runtime integration boundary.

## Golden Contract and Failure Diagnosis

Dataset schema version 1 requires unique case names and complete fixture
coverage. Omitting a case, adding an unknown scenario or loading an unsupported
schema fails before fixtures run. There is intentionally no auto-update flag.

Each case declares:

- Expected final `status` and optional `error_type` (default: no error).
- An exact ordered list of event types. Unexpected, missing and reordered
  events fail; no event type is silently filtered out.
- Selected stable event payload fields. These are required subsets, allowing
  additive diagnostic fields without forcing timestamp/UUID snapshots.
- Selected runtime facts: execution counts, persisted statuses/results and
  correlation booleans. Missing fields fail, even when the expected value is null.

The adapter allowlists stable payload fields. Golden assertions must use only
synthetic fixture data, never customer prompts, secrets or live response bodies.
Fixture exceptions report the exception class, not the potentially sensitive
exception message. The focused pytest case provides a local traceback.

Example failure:

```text
First divergence at event[3]: expected 'model_call_retrying', observed
'run_failed'; event counts 5 expected / 4 observed.
facts.model_calls: expected 2, observed 1.
```

Inspect the named transition, retry policy and committed records first. Tests
deliberately change the actual retry policy to prove this failure is caught.
Other mutation tests remove/add events and change an observed attempt number.
Seven request-mutation cases additionally remove a tool result, corrupt its
contents, remove the assistant call, change its arguments, change the provider
call ID, change the original task, or substitute a consistent but wrong internal
call UUID. Each must fail the native-tool case without changing its golden.

To intentionally change behavior:

1. Explain the compatibility/security impact and update the relevant spec.
2. Change runtime behavior with a focused regression test.
3. Review each affected golden field in the diff. Do not regenerate goldens to
   make a failing gate green without understanding the difference.
4. Run the timeline gate and the affected runtime/approval/worker suites.

## OpenAI Wire Contracts (R3)

`tests/integration/test_openai_runtime_contract.py` constructs the actual
`OpenAIProvider`, `RunExecutionService`, router, tool registry and repositories.
Only HTTP transport is mocked. The adapter must send valid Responses request
items before the fixture returns success; the fixture is not a generic provider
that succeeds based solely on invocation count.

The protocol follows the official [function-calling guide](https://developers.openai.com/api/docs/guides/function-calling)
and [Responses input reference](https://developers.openai.com/api/reference/resources/responses/methods/create):

- Preserve replayable OpenAI `response.raw.output` through assistant metadata
  into the next wire request, in original order. This includes reasoning items
  (with IDs, summaries, optional content and encrypted content), assistant
  messages and function calls. Do not turn reasoning into assistant answer text.
- Cross-check native calls against normalized `tool_calls`. For normalized-only
  histories, reconstruct calls with the provider ID, function name and JSON
  arguments. Malformed or unsupported native output fails before tool execution;
  inconsistent supplied history fails before the next HTTP request.
- Emit each tool message as `function_call_output` with that same `call_id`
  and its string result. Never use the internal database UUID or the response
  item's `fc_...` ID as the provider call ID.
- Preserve ordinary messages and omit empty assistant carrier messages.
  Reject unmatched, duplicate or missing call results before HTTP dispatch.
- Compare the submitted result with persisted tool state and verify one tool
  execution, bounded HTTP attempts, final text and combined observed token usage.

Reasoning continuation follows the official
[reasoning guide](https://developers.openai.com/api/docs/guides/reasoning).
The adapter preserves actual native items rather than synthesizing reasoning or
relying on a provider-specific cache. Supported replay item types are `reasoning`,
`message` and `function_call`; unknown/incomplete items accompanying a native call
are rejected explicitly rather than silently dropped. Stateless encrypted items
are preserved when supplied; this does not implement streaming or arbitrary
OpenAI built-in tools.

Error classification is checked against the official [error-code guide](https://developers.openai.com/api/docs/guides/error-codes).
Each adapter invocation makes one HTTP attempt; runtime owns retry/fallback:

| Failure | Adapter category | Current initial-call runtime behavior |
| --- | --- | --- |
| Temporary HTTP 429 throttling | `rate_limit` | Bounded retry, then configured fallback. |
| HTTP 408/504 or HTTPX timeout | `provider_timeout` | Bounded retry, then configured fallback. |
| HTTP 409, other 5xx, network/remote protocol failure | `provider_unavailable` | Bounded retry, then configured fallback. |
| Recognized billing/quota exhaustion on 429 | `openai_quota_exhausted` | Fail without retry or fallback. |
| Other HTTP 4xx | `openai_status_error` | Fail without retry or fallback. |
| Other request errors or invalid response JSON/object shape | Non-retryable adapter error | Fail without a hidden adapter retry. |

Transport error messages and HTTP response bodies are not copied into the
public `LLMProviderError` message. These tests do not replace process-wide log
redaction: chained exceptions and third-party loggers remain separate concerns.

For 429, 503, read timeout and connection error, actual-adapter/runtime tests
verify retry success, fallback after primary exhaustion, and total exhaustion.
With two attempts per model and one fallback, the asserted bounds are two,
three and four HTTP requests respectively. Persisted attempt numbers, fallback
selection and failure categories must match. Permanent failures stop after one
request even when fallback is configured.

After a native tool succeeds, synthesis now gets its own bounded attempt loop
using the same `RetryPolicy.provider_max_attempts`. The configured default is
unchanged (currently 2); dedicated wire tests explicitly use 3 attempts. A
retry repeats only the same provider/model request with the same original
history and persisted tool result. It never re-executes the tool. Native
follow-up fallback, including cross-provider fallback, is deliberately unsupported
because native call IDs and reasoning history are not portable. Exhaustion or
a non-retryable error fails the run while retaining the successful tool record.

The wire matrix covers plain calls, stored reasoning items and encrypted
reasoning items. It asserts exact request counts (one initial request plus up
to three follow-up attempts), identical retry bodies, ordered persisted events,
`phase: tool_followup`, attempts 2/3, and exactly one tool execution even after
exhaustion. Each successful response contributes usage once: initial + final
on success, initial only on follow-up failure. The model-usage ledger row count
and Run/output totals are cross-checked. Failed HTTP attempts have unknown usage;
the absence of a usage response is not evidence that the provider charged zero.

Explicit limits of this repair:

- Runtime still has no backoff/jitter or `Retry-After` delay support. Bounded
  attempts are not a claim of production throttling compliance; runtime policy
  work needs separate coordination and regression evidence.
- The supported loop still executes one native call followed by a bounded
  synthesis stage. Multi-call loops and model continuation after persisted approval
  are not added or certified by these contracts.
- No paid request or live-provider compatibility test was performed. HTTP
  fixtures test the documented contract, not remote service availability.

## Optional Live Provider Smoke

```bash
uv run python scripts/live_provider_smoke.py
```

Without `AGENT_KERNEL_LIVE_SMOKE=1`, this returns `status: skipped` and exit 0.
It neither constructs a network provider nor checks credentials. Merely having
an API key in the shell does not enable live execution. A skipped result is
not a passed live test and contains no fabricated timing or zero-cost sample.

To opt in, configure these variables in your private shell environment:

| Variable | Requirement/default |
| --- | --- |
| `AGENT_KERNEL_LIVE_SMOKE` | Exactly `1` to permit one live request. |
| `OPENAI_API_KEY` | Required; never include in command arguments or reports. |
| `AGENT_KERNEL_LIVE_MODEL` | Required explicit model; prefer a pinned model for comparable reports. |
| `AGENT_KERNEL_LIVE_INPUT_USD_PER_MILLION` | Required positive input-token rate; operator must verify current upper-bound pricing. |
| `AGENT_KERNEL_LIVE_OUTPUT_USD_PER_MILLION` | Required positive output-token rate, including applicable reasoning/output billing. |
| `AGENT_KERNEL_LIVE_MAX_OUTPUT_TOKENS` | 32 by default; allowed range 16..128. |
| `AGENT_KERNEL_LIVE_TIMEOUT_SECONDS` | 20 by default; allowed range 0.1..60. |
| `AGENT_KERNEL_LIVE_MAX_COST_USD` | 0.01 by default; must be positive and at most 0.10. |

Then run, retaining stdout as an optional local artifact:

```bash
AGENT_KERNEL_LIVE_SMOKE=1 uv run python scripts/live_provider_smoke.py > /tmp/agent-kernel-live-current.json
```

Safety and interpretation:

- Exactly one request to the existing OpenAI provider's default endpoint. No
  automatic retry, fallback, arbitrary prompts, attachments or tool execution.
- A fixed short ASCII prompt requests `OK`. A response must finish normally,
  be text-only and match that text. Incomplete or mismatched output fails.
- Admission reserves 1,024 input tokens (a conservative allowance for the fixed
  prompt and framing) plus the configured output cap at the supplied rates.
  If this exceeds the budget, no request is made. Missing/invalid prices fail.
- Both HTTP timeout and an outer async deadline are applied. Cancellation cannot
  undo provider-side work or charges already incurred; use provider account
  spend limits as the independent billing control.
- After completion, returned token counts are checked against the reservations
  and used to calculate estimated USD. Missing usage is an error, not free usage.
  The provider adapter's default `estimated_cost=0` is not treated as a price.
- This is a conditional client-side cost bound, not an invoice guarantee:
  incorrect operator prices, changed provider accounting or ignored token caps
  can invalidate it. Over-bound responses fail and require billing review.
- Latency is measured with a monotonic clock around the actual provider attempt.
  Keys, full prompt/response bodies and exception text are not written to reports.

Live script exits 0 for pass or skip, 1 for an attempted smoke failure, and 2
for invalid configuration/report input. An explicitly scheduled live check may
choose to gate on those statuses, but the standard release gate remains offline.
Tests use fake providers or HTTP mock transports only. Injected providers are
labeled `sample_kind: fixture`, never evidence of a live-provider pass.

## Non-Blocking Trend Reports

Keep successful smoke JSON reports as artifacts, then compare offline:

```bash
uv run python scripts/live_provider_smoke.py --compare /tmp/agent-kernel-live-baseline.json /tmp/agent-kernel-live-current.json
```

This command never contacts the provider and does not require live opt-in.
It requires successful report inputs, not skipped/failed runs. Comparisons check
case ID, request fingerprint, fixture/live kind, provider, requested model,
returned model and both price rates. Changing the output cap changes the request
fingerprint. A changed model alias resolution or pricing is incomparable, not a
performance regression disguised as an apples-to-apples measurement.

Comparable results contain absolute and percentage deltas for estimated USD,
latency, input tokens and output tokens. A zero baseline has null percentage,
not infinity. An increase is flagged for review but always has `blocking: false`.
Incomparable reports explain each mismatched identity field and omit deltas.
Invalid/non-finite/negative measurements are rejected.

One latency sample is noisy. Collect repeated equivalent live samples before
making performance claims; fixture timing only measures local test machinery.
No fabricated historical baseline, live credential run or elapsed-time claim is
included with this change.

## Remaining Release Evidence

The parent release workflow must record the current SHA's CI result, run the
full offline gates, review dependencies/security and perform the documented
self-hosted rehearsal (including backup/recovery and external backends).
These tools do not replace those checks or independently close P5.2. Live
provider evidence remains optional and must be marked not run when credentials
and an approved budget are not available.

## Historical Local Verification Record

2026-11-13, uncommitted shared-worktree verification:

- The three new suites above: 48 passed.
- Those suites plus the existing RAG/tool eval, runtime execution, stuck-run
  recovery, worker and API-to-worker suites: 96 passed. The existing
  Starlette/httpx deprecation warning remains unrelated to these changes.
- Direct timeline command: 7/7 cases passed, exit 0.
- Live command with `AGENT_KERNEL_LIVE_SMOKE=0`: `skipped`, exit 0, no request.
- Ruff on the new Python files: passed. `mypy .`: passed (181 source files
  present at verification time, including concurrent work).
- No actual live provider request, remote CI, release, tag, commit or push was
  performed by this workstream. Numerical comparator tests are synthetic fixture
  samples, not measured production latency or historical live cost evidence.

## Initial R3/R10 Repair Verification

2026-11-13, local shared-worktree checkpoint after the audit reopened acceptance.
This historical checkpoint predates follow-up retry and reasoning continuation.
It verifies the first adapter/request-contract repair only; it does not mark
R10, P5.2 or the complete hardening batch accepted.

| Check | Observed result |
| --- | --- |
| `.venv/bin/pytest -q tests/unit/test_openai_provider.py tests/integration/test_openai_runtime_contract.py tests/integration/test_timeline_regression.py` | 86 passed, no skips. |
| The above plus `test_runtime_execution.py`, `test_runtime_usage.py`, `test_model_router.py`, `test_tool_call_evals.py`, `test_provider_tools.py`, `test_live_provider_smoke.py`, `test_eval_comparison.py` under `tests/unit` | 154 passed, no skips. |
| `.venv/bin/python scripts/timeline_regression.py` | 7/7 normal scenarios passed, exit 0. |
| Runtime follow-up mutation removes the tool result, then calls the same CLI entry point | Exit 1; native-tool case fails with `FixtureContractError`. |
| `UV_NO_SYNC=1 UV_NO_CACHE=1 UV_OFFLINE=1 make release-eval` | Passed: RAG datasets, tool-call evals and timeline command. Existing virtualenv used without dependency changes or network access. |
| Ruff check and format check on the five changed Python files | Passed. |
| Scoped mypy on those files, with workspace source roots in `MYPYPATH` and `--follow-imports=silent` | Passed; dependencies were not rechecked by this scoped command. |
| Full `.venv/bin/mypy .` | Not green at this checkpoint: concurrent files outside this workstream reported errors. Parent must rerun after integration; no full typecheck acceptance claimed. |

The modified Python files are the OpenAI adapter, timeline script, provider unit
tests, actual-adapter integration tests and timeline integration tests. No
runtime execution source, API/Worker entry point, RAG tool, canonical plan or
canonical verification record was edited by this workstream. No credentials,
paid calls, commit, push, tag or remote CI run were used. The residual runtime
limitations above remain explicit review items, not silently closed work.

## Follow-Up Retry and Reasoning Verification

2026-11-13, subsequent local checkpoint after review expanded R3's scope:

- The provider, actual-adapter/runtime and timeline suites: **113 passed**, no
  skips. The 18 native wire cases cover three history forms and six follow-up
  outcomes, including success on the third attempt, exhaustion and permanent
  failure. A second configured adapter/endpoint remains uncalled in all cases.
- Adding the seven related unit suites from the initial checkpoint and
  `tests/integration/test_execution_cancellation.py`: **198 passed, 17 skipped**.
  The skips are PostgreSQL ownership/cancellation cases because this process
  did not have `AGENT_KERNEL_TEST_POSTGRES_URL`; they are not passed evidence.
  The source-usage failure assertion now derives request count from the retry
  policy and still asserts the tool executes once and usage is not duplicated.
- Exact persisted follow-up timelines and per-response ledger rows are asserted
  by the wire suite. The existing seven golden scenarios and all request-mutation
  tests still pass; no golden expectations were relaxed to allow the new behavior.
- `UV_NO_SYNC=1 UV_NO_CACHE=1 UV_OFFLINE=1 make release-eval`: passed again.
  Ruff lint/format checks on all seven changed Python files: passed.
- Full `mypy .` at this checkpoint: one remaining error outside this workstream,
  `test_observability_operational_signals.py` importing an attribute not explicitly
  exported by `agent_kernel_api.main`. Parent integration must rerun the full gate.

Runtime edits were limited to the authorized native follow-up block,
`_request_with_tool_result`, and its `deepcopy` import. The parent's usage recorder
and the observability workstream's execution metrics block were not edited.
Malformed native reasoning/history fails before tool execution; mismatched
normalized/native calls fail before HTTP dispatch. No paid model requests,
commits, pushes, releases or canonical acceptance-state changes were performed.
Full real-backend/remote verification still belongs to the parent closure gate.
