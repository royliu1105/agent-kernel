# Supervised Local Paid Experience

Status (2026-11-22): configuration verified; real RAG Run succeeded earlier;
paid DeepSeek + GitHub approve→resume continuation **succeeded** on Run
`65050ea0-1a4f-4924-a795-64027f624d45` after pin refresh. Billing reconciliation
and full pilot (PV5) admission remain unverified; PV3 quality gate is closed on
R4 (v2). Earlier
configuration-only and failed-continuation evidence below is retained as
history.

## Documentation-Only Commit Boundary

Historical boundary for commit `17af7db`, retained for provenance. The separate
implementation follow-up below supersedes the availability statements in this
section, not the scope of that earlier commit.

This record describes observations on the maintainer's working tree based on
`d8f316d`, with additional uncommitted paid-profile and response-hash changes.
This documentation-only commit does not ship those runtime changes. In a clean
checkout of this commit, `make docker-paid-check`, `make docker-paid-up`,
`deploy/local-paid.compose.yml`, `deploy/local-paid-tools/` and the optional
`response_sha256` guard are not available. Do not use the recorded commands or
infer that the committed adapter enforces that guard. They require a separately
reviewed implementation commit and its own verification before reuse.

The sanitized observations below are retained so the pilot ledger has a truthful
source; document tests or this commit's CI cannot validate the excluded runtime
patch. Earlier business changes and their companion authorization/provider
documentation remain outside this submission. No new task execution is requested.

On 2026-11-15 the maintainer authorized configuring the existing Docker stack for
DeepSeek and Alibaba Embedding within the remaining first USD 2 batch (USD 10
total, USD 0.25/task). This is a specific exception to the earlier isolated-only
pilot deployment plan, for a trusted single-user localhost walkthrough. It does
not authorize automated drills, arbitrary uploads, new tool-response disclosure,
or additional batches. Retain all existing volumes and credentials.

## Separate Implementation Follow-Up

The subsequent review/submission includes the explicit paid Compose overlay,
`docker-paid-*` entrypoints, fixed local GitHub binding and optional
`response_sha256` adapter guard. These are a separate implementation change,
not part of `17af7db`. Its own CI must validate the submitted revision; the
earlier documentation-only CI cannot substitute for that result.

The review adds byte-exact mismatch cases and persisted approval-continuation
regressions for matching bodies, changed bodies, changed pins and removed pins.
Database cases use only disposable remote CI PostgreSQL in this review, not
the active local runtime. No new model/tool request or local Docker update is
authorized by this submission. The current Docker images remain unchanged.

The failed-response private-evidence repair was later implemented on 2026-11-22
(see Remaining Work below). Shipping the earlier hash guard alone did not resolve
the observed mismatch; pin refresh plus private evidence are both required.

## Recorded Local Activation

Keep ONLY these two entries in ignored `.agent-kernel/docker-local/paid.env`
(0600, inside the existing 0700 directory):

```dotenv
DEEPSEEK_API_KEY=<private value>
DASHSCOPE_API_KEY=<private value>
```

Never paste keys into chat, the Web sign-in form, tracked source or command-line
arguments. The runtime does not load any private reference checkout. An operator
may copy only the two previously authorized credential values from a private
reference config kept outside this repository, without sourcing that file or
printing its contents.

```bash
make docker-paid-check
make docker-paid-up
```

Both API and Worker get the same explicit provider configuration and bounded
execution settings. API readiness validates configuration without contacting
model services: ready does NOT prove key validity, balance or account access.
The default Web model remains `mock:echo`; paid Runs must explicitly select
`deepseek:deepseek-flash`. Embedding indexing and retrieval now use DashScope
`text-embedding-v3`, Beijing, 1024 dimensions and can incur charges even without
a generation Run. Do not use Retrieve as a supposedly free health check.

`make docker-up` always restores the mock configuration (keys cleared), keeping
the same data. `make docker-stop` stops the stack. Ordinary status/log commands
do not change configuration. Do not change profiles while a Run is active or
awaiting approval; existing queued tasks must be reviewed before activation.

## Data and Spending Boundary

Use only the frozen corpus in `docs/pilots/pv1-materials/corpus/`; exclude reviewer
answers, private files and personal memories. Use the dedicated walkthrough
knowledge base, not the older Docker acceptance sample. The maintainer already
uploaded and mock-indexed D01 in this separate KB. Indexing it once with DashScope
adds a model-specific index; replacement and retrieval filter by model, preserving
the old mock vectors. No reupload or rechunk is necessary. Switching the backend
alone does not convert existing vectors, and querying before the real index
exists is not a valid live-retrieval test.

No shared dollar-budget admission ledger is installed by this Compose override.
The two-model-call ceiling includes continuation/retries, not two independent
Runs. Token/time ceilings and estimated-cost fields are not provider hard caps;
provider estimated-cost fields currently default to zero and must not be used as
billing proof. Keep one active Run, admit each reserved batch slot separately,
reconcile provider usage, and stop on unknown charges or exhausted reservations.
See the existing [first-batch worksheet](pilots/pv1-2026-11-15-runbook-assistant.md#first-usd-2-allocation-and-calculation).

Configuration alone sends no documents or model requests. Do not claim that the
first USD 2 is available from a zero-cost mock Run: project records can establish
no recorded paid calls, not the provider account's complete billing history.
The separately requested GitHub approval walkthrough below adds one external
binding; it never waives approval or changed-response inspection.

## Historical Configuration-Only Evidence

- Six local-stack tests, provider compatibility and documentation checks:
  **158 passed**; Ruff, shell syntax and diff-whitespace checks passed.
- `make docker-paid-check` and `make docker-paid-up` succeeded; 13 services running.
- Both actual API/Worker containers have dedicated credentials present, OpenAI
  credentials absent, DashScope v3/1024 and identical execution limits. No secret
  values were printed. `/readyz` reports ready with DeepSeek/DashScope required/ok.
- Before/after metadata counts match: 2 Agents, 2 KBs, 2 documents, 2 mock vectors,
  1 succeeded mock Run; no queued/running/waiting-approval Run was admitted.
  No index, retrieval or generation request was made by this setup.
- The uploaded D01 checksum matches the frozen file:
  `dd90cab6e642d8196e82deefeab943555880f9428ac266d57d34d38bd82b4e68`
  (1428 bytes). Its existing mock index remains unchanged.
- No account invoice/balance check or shared budget guard is claimed. First
  paid dispatch, usage reconciliation, live quality and approval-tool integration
  remain unverified. No commit/push or remote CI was requested in this setup.

## Subsequent RAG Walkthrough

The maintainer indexed D01 with `text-embedding-v3`/1024, performed manual
retrieval, then queued Run `6ee6ad17-e47c-4777-b3fe-d4e3deeb9ac0`.
Read-only inspection confirmed succeeded, two `deepseek-flash` usage rows
(682/148 and 2772/720 input/output tokens), one succeeded `kb_search`, and a final
answer citing the exact stored document/chunk. No fallback was used; elapsed Run
time was about 6.22 seconds. The later inspection did not repeat execution.
This is one live RAG example, not full pilot acceptance or billing reconciliation.
The corpus's old pending-authorization wording remains frozen historical content;
it does not override the maintainer's subsequent scoped authorization.

## GitHub Approval Walkthrough

Configuration uses `deploy/local-paid-tools/`, mounted read-only into API/Worker
only by the paid overlay. The maintained OpenAPI adapter loads the local schema
without network discovery. Exact boundary:

- Tool: `github_ci_run_status`; GET only, public GitHub, no credential/cookie.
- Fixed repository `royliu1105/agent-kernel`; only run `43634747295`, with required
  `query.exclude_pull_requests=true`. This is a historical run, not latest CI.
- `policy_decision=require_approval`, `retry_safe=false`, 10 seconds, 32 KiB.
- No dispatch/rerun/cancel/logs/artifacts/linked URLs or arbitrary headers.
- For this explicitly requested anonymous localhost walkthrough only,
  `allow_unscoped=true`, empty authenticated workspace allowlist. Loopback exposure
  and disabled auth are unchanged. This is NOT the authenticated pilot profile or
  proof of workspace/RBAC acceptance; do not expose it on a shared network.
- `response_sha256` pins the previously reviewed raw response bytes. A different
  response, including changed metadata or JSON whitespace, raises
  `external_response_review_required` before content becomes a tool result. No
  changed body is returned to the model or included in the error. No automatic
  retry or silent hash refresh. Manual reinspection needs a separate operator step.
  The pin is in tool metadata, so changing it invalidates saved approval contracts.

The optional OpenAPI binding `response_sha256` accepts exactly 64 lowercase hex
characters. Unpinned bindings retain their existing response behavior. Adding
this external metadata field can make older external-tool checkpoints fail closed
on contract comparison; update only with no active/waiting Run. The frozen pilot
source documents and corpus stay byte-identical; this document records the new
local exception and response guard without silently revising frozen evidence.

Budget reservations retain E=USD 0.10 and G2=USD 0.25 for the observed embedding/
RAG activity without treating their zero estimated-cost fields as free. Reserve
G5=USD 0.25 for the new approval Run, including initial/continuation attempts.
These three reservations total USD 0.60 within the existing USD 2 batch; they are
not measured charges or account balance. Do not consume contingency or repeat
failed tasks automatically. Existing pending billing reconciliation remains open.

### Historical Walkthrough Instructions (Already Exercised)

These instructions describe the one Run recorded below, not a request to create
or repeat it. The completed RAG Run and failed approval Run must not be requeued
as part of documentation review or diagnosis.

Keep the frozen System prompt and `deepseek:deepseek-flash`. Create one NEW Run
with the following task (do not requeue the completed RAG Run):

```text
请调用 github_ci_run_status 查询已获准的历史 GitHub CI 运行。
参数：path.run_id=43634747295，query.exclude_pull_requests=true。
只查询这一个运行，不检索知识库，不查询最新运行或其他链接。
工具需要人工审批，请等待批准；不得绕过审批或改用其他工具。
获得结果后说明运行 ID、run_attempt、head_sha、status、conclusion，
明确这是历史记录，不代表当前部署状态。工具失败时停止，不重试。
```

Click Create run, Queue run once, then Refresh run. Initial model generation
costs money even when the tool is waiting. At that checkpoint, stop at
`waiting_approval` and have the operator inspect the bound tool/arguments.
Approval decision alone does not invoke GitHub; Resume run does. Neither action
is performed automatically by configuration. The subsequent observed
wait/approve/resume/response-rejection sequence is recorded below.

Offline tests use the exact deployment binding with a counted mock HTTP transport:
loading plus repeated unapproved attempts dispatch zero requests, central allow
cannot weaken required approval, valid authorized adapter execution dispatches
once, invalid arguments/workspaces dispatch zero, changed content never returns,
and the response pin is included in the checkpoint contract. This is policy/
adapter evidence, not independent observation of a live GitHub socket or a new
persisted approval Run. No real GitHub or model request is needed for these tests.

### Historical Pre-Walkthrough Configuration Verification (2026-11-15)

- 1,027 unit tests passed against the separate `agent-kernel-test` PostgreSQL;
  56 OpenAPI/native-loop/rejection/approval-observation integration tests passed.
  The test DB used tmpfs and was removed afterward, never sharing runtime data.
- Initial broad tests without the required test DB failed; that environment issue
  was resolved by the isolated rerun, not by pointing fixtures at the active DB.
  A frozen-source mismatch was resolved by retaining those source files unchanged
  and moving new guidance here. The manifest/corpus/prompt were not regenerated.
- Ruff passed; mypy passed for 254 source files; changed-file formatting and
  whitespace checks passed. One existing multiprocessing fork warning remains.
- Paid Docker build/start succeeded. API/Worker each load only the configured
  GitHub external binding, require approval, veto retry, and use the same exact
  response pin and argument schema. Configuration inspection performs no dispatch.
- `/readyz` is ready. The previous RAG Run remains succeeded with its original
  two model-usage rows. No GitHub tool record or approval exists yet; live approval
  acceptance remains pending. This setup issued no GitHub or paid-model request.
- These tests are not remote CI or the completed live approval walkthrough.

### Observed Approval and Failed Continuation

The maintainer created Run `e737c1a6-72fe-485e-9d5a-82888bbaee2a`.
Approval `4fed4e27-7fcc-495c-875a-f91d1db7baa8` binds tool call
`d4afe625-95e7-4000-84ef-f822f196f90f` to the exact historical run/query above.
Read-only inspection and the maintainer's Workbench observations established:

- Before approval, the Run/tool were `waiting_approval`, approval `requested`,
  tool result empty. One DeepSeek usage row recorded 846 input/114 output tokens.
- The maintainer clicked Approve. Approval became `approved`; Run/tool still
  waited. Approval alone did not resume execution. Local auth was disabled,
  so `reviewed_by=null` is not authenticated reviewer-identity evidence.
- The maintainer then clicked Resume. Events recorded `run_resuming`,
  `run_started`, `tool_call_failed`, `run_failed`; tool latency was 778 ms.
  Error: `external_response_review_required`.
- Approval remained approved, tool and Run failed, result/output remained empty.
  The same single model usage row remained; no post-tool model continuation
  consumed the rejected response. No final CI answer was produced.

These are local state/usage observations, not an independent socket-level
exactly-once certificate or a passing live approval cohort. They did not close
PV2/CF1 at the time. A later successful continuation is recorded below; it still
does not authorize unbounded tasks, disclosure, retries or budget.

### Successful Paid Approve→Resume (2026-11-22)

After the private-evidence repair and pin refresh to `a1b24653…`, the maintainer
authorized one new paid DeepSeek walkthrough (same frozen system prompt, no KB):

- Run `65050ea0-1a4f-4924-a795-64027f624d45` → `waiting_approval` after one
  DeepSeek call (`github_ci_run_status` proposed with the fixed historical args).
- Approval `52ac5ddb-f8bc-4e51-9f40-1e7ada75e9f2` approved, then explicit resume.
- Tool dispatch returned HTTP 200 against pin `a1b24653…`; Run **succeeded**.
- Totals: 6464 input / 884 output tokens on `deepseek-flash`. Answer reported
  run_id `43634747295`, `run_attempt=1`, `conclusion=success`, and stated this
  is historical evidence only (not current deploy status).
- Private summary (gitignored):
  `.agent-kernel/external-response-review/paid-github-resume-20261122.json`.

This closes the previously open paid-model GitHub continuation observation. It
is not billing reconciliation, PV3 cohort acceptance, or shared-user admission.

### Subsequent Read-Only Response Inspection

One separately authorized anonymous GET used the same fixed GitHub target,
query and API headers, no credentials, redirects or retries. It returned HTTP
200, JSON, 14,622 bytes. Its body matched the previously reviewed body byte for
byte; both SHA-256 values were:

```text
37637575f2483bd19f6d91c84ae8db84a0189993e50b96ca247242a59009bc7f
```

JSON field differences: zero. The ETag matched. Some response headers changed
(including date, request ID and rate-limit counters); these headers are not
part of the body hash. An offline mock-transport replay of the inspected body
passed the current adapter's validation. No model was called and the failed
Run was not repeated; the pin/approval checks were not disabled or updated.

The failed tool dispatch did not preserve its raw response body. Therefore
the later matching GET cannot establish what differed during that dispatch.
It used a separate diagnostic client, not the failed actual transport instance.
Metadata changes, serialization or transport differences remain hypotheses,
not a root-cause finding. Private response bodies remain outside tracked docs.

### Remaining Work and Current Hold

**Implemented (2026-11-22):** when `response_sha256` mismatches, the OpenAPI
adapter writes a bounded private evidence envelope under
`.agent-kernel/external-response-review/` (or
`AGENT_KERNEL_PRIVATE_EVIDENCE_DIR`) and still fails closed without putting the
unreviewed body into Run/tool error text. Unit coverage:
`tests/unit/test_local_github_tool.py`.

**Pin refresh (2026-11-22):** a public GET of the same historical run
`43634747295` returned a different raw body than the 2026-11-15 review
(`37637575…` → `a1b24653…`, still `conclusion=success`, `run_attempt=1`).
Private review envelope:
`.agent-kernel/external-response-review/pin-refresh-20261122T060822Z.json`
(gitignored). `deploy/local-paid-tools/tools.json` now pins
`a1b246537bc9e07143ad3daaf7dc1a9da6d03d1663b28829257f05766b11d232`. Historical
authorization docs retain the earlier hash as period evidence.

Opt-in approval→resume against live GitHub with a **scripted** (non-paid) model:

```bash
export AGENT_KERNEL_TEST_LIVE_GITHUB=1
export AGENT_KERNEL_TEST_POSTGRES_URL=...  # disposable test DB only
uv run pytest -q tests/integration/test_live_github_tool_resume.py
```

That path proves real GitHub tool success after approval without DeepSeek spend.
It does **not** close PV3, reconcile billing, or replace a paid-model walkthrough.

Paid-model continuation through the paid Docker path is now observed successful
(2026-11-22). Formal PV3 same-day admissions: R2 short on A; R3 (v3) regressed;
**R4** returned to prompt v2, **met** A/U/I+X gates, and is the **accepted**
PV3 admission — see [pv3-closure](pilots/pv3-closure.md) and
[pv3-2026-11-22-r4-results](pilots/pv3-2026-11-22-r4-results.md).
Still open: optional console day-lines, pin drift, PV5. PV4 ops closed —
[pv4-closure](pilots/pv4-closure.md). Default stack remains mock via
`make docker-up`.

The documentation-only commit boundary for earlier docs remains historical.
Budget reservations above are not reconciled charges.
The [pilot plan](real-scenario-pilot-plan.md) remains the sole PV1-PV6 ledger;
the [project overview](project-overview.md) summarizes capability boundaries.
