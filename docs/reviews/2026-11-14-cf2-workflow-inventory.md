# CF2 Workflow Inventory and Isolated Rehearsal

Date: **2026-11-14**. Status: **isolated authenticated API/CLI rehearsal and
offline request/config provenance passed; CF2 overall acceptance remains open**.

The [CF1-CF8 ledger](../reference-follow-up-plan.md) owns acceptance. This is
supporting evidence, not a second completion checklist or a CF2/PV2 pass.
Runtime source base: `bef87a94b5c50405ba104298839367c4b53b0fcc`, plus uncommitted
test harness/documentation and the subsequently authorized rejection repair below.
Private source hashes identify the exact tested files for each rehearsal;
these local rehearsals did not themselves commit or remotely verify the candidate.

The maintainer selected an authenticated API/CLI-only disposable Docker rehearsal
after the source inventory. This permits test harnesses and documentation, not
Web-auth implementation or business-code expansion. No active Docker
environment, data, credentials or `resource/` is changed. No active deployment,
paid provider request, user admission, commit/push or release is included.
Purchasing usage credits does not identify a provider, model, budget or data
transmission approval.

The maintainer later authorized the bounded rejection-terminal code repair,
regressions and documentation. Its
[repair record](2026-11-14-approval-rejection-repair.md) supersedes only that
residual issue, not the initial rehearsal's historical results or other exclusions.

The maintainer subsequently authorized review of both changes, commit/push after
successful review, and CI tracking, still without active Docker updates. See the
[review record](2026-11-14-approval-rejection-repair.md#pre-commit-review). This later
authorization does not turn fixture evidence into Web/live-model or pilot acceptance.

## Available Surfaces

**API-backed** below means a source-confirmed backend request path, not a live
model, an authenticated browser journey or a newly executed acceptance test.

| Surface | Source-confirmed behavior | Pilot boundary |
| --- | --- | --- |
| Web health | Proxy calls API readiness. | Readiness is not a successful user task. |
| Web Agents/overview | Static arrays and preview state. | Not live agent management or a reliable queue overview. |
| Web Runs | UUID lookup fetches Run/events; renders status, agent, trace, cost and timeline. | List remains fixture-backed. No create/queue/cancel/resume action or full answer/output renderer in live lookup. |
| Web Approvals | Live list and approve/reject POSTs coexist with preview cards. | Live decision does not invoke Run resume. Preview cards do not mutate backend approvals. |
| Web Knowledge | Live KB list and retrieval search show content/source citations. | Ingestion cards remain previews; create/upload/ingest/chunk/index use API/CLI. Retrieval snippets are not a generated answer. |
| Web Evals | Reads persisted reports. | Display/persistence does not itself run a live quality evaluation. |
| Web Settings | Static/read-only presentation. | Not proof of effective container/model/policy configuration. |
| API/CLI | Agent creation, Run lifecycle, approvals, KB/document lifecycle, memory and eval publication. | CLI is an HTTP client; it does not bypass API permissions or execute the Worker in-process. |

Evidence: [Workbench](../../apps/web/src/app/page.tsx),
[proxy routes](../../apps/web/src/app/api/agent-kernel),
[API](../../apps/api/src/agent_kernel_api/main.py),
[CLI](../../apps/cli/src/agent_kernel_cli/main.py).
The page uses same-origin proxy handlers; the separate `ApiClient` class in
`apps/web/src/lib/api.ts` is not evidence of a different page request path.

## API and CLI Workflow Map

CLI entries omit the `agent-kernel` prefix. This is an inventory, not instructions
to mutate the active stack. Rehearse only in an explicitly isolated Docker
harness with its own ports/data/credentials. Use returned IDs, not preview IDs.

| Step | API | CLI | Permission with auth enabled | Evidence to retain privately |
| --- | --- | --- | --- | --- |
| Agent | `POST /v1/agents` | `agent create --name ...` | `agent:write` | Agent/workspace IDs. |
| KB | `POST /v1/knowledge-bases` | `kb create --name ...` | `knowledge:write` | KB/workspace IDs. |
| Upload | `POST /v1/knowledge-bases/{id}/documents/upload` | `document upload <kb-id> <path>` | `knowledge:write` | Document ID, checksum, object reference. `document register` alone only registers metadata. |
| Parse | `POST /v1/documents/{id}/ingest` | `document ingest <id>` | `knowledge:write` | Ingestion job status and document linkage; not vector indexing. |
| Chunk | `POST /v1/documents/{id}/chunk` | `document chunk <id>` | `knowledge:write` | Chunk IDs, offsets and count. |
| Index | `POST /v1/documents/{id}/index` | `document index <id>` | `knowledge:write` | Actual embedding model/dimensions and indexed count. |
| Retrieve | `POST /v1/knowledge-bases/{id}/retrieve` | `kb search <id> --query ...` | `knowledge:read` | Citation KB/document/chunk IDs and source passage. |
| Create Run | `POST /v1/agents/{id}/runs` | `run create <agent-id> --input @<file>` | `run:write` | Run in `created`, input, principal/workspace and model selection. Creation does not queue it. |
| Enqueue | `POST /v1/runs/{id}/queue` | `run queue <id>` | `run:write` | Queued event, actual Worker state/events. Redis is a hint, not the source of truth. |
| Inspect | `GET /v1/runs/{id}` and `/events` | `run inspect <id>` / `run events <id>` | `run:read` | Full output/error/usage and ordered events. Use API/CLI for the answer. |
| Decide | `GET /v1/approvals`; `POST /v1/approvals/{id}/approve` or `/reject` | `approval list`; `approval approve <id> --note ...` / `approval reject <id> --reason ...` | `approval:review` | Approval/Run/tool IDs, reviewer and decision; zero forbidden effects. |
| Resume | `POST /v1/runs/{id}/resume` | `run resume <id> --approval-id <id>` | `run:write` | Continuation outcome, invocation counter, tool-call records and completion events. Synchronous API execution, not queued Worker resume. |
| Cancel | `POST /v1/runs/{id}/cancel` | `run cancel <id>` | `run:write` | State and observed termination; cannot undo an already-performed remote effect. |

Built-in `owner`, `admin` and `operator` have these write/review permissions;
`viewer` has read permissions but not approval review or writes. See the
[role mapping](../../packages/kernel-identity/src/kernel_identity/authorizer.py).
Keys must resolve to the intended principal/workspace; knowing an ID is not
authorization. CLI JSON/upload requests attach the privately configured
`AGENT_KERNEL_API_KEY` as a Bearer header.

## Gaps and Scope Decisions

1. **Authenticated Web remains unresolved.** Current proxy handlers do not attach
   or forward Authorization, and the page has no authenticated session bridge.
   Protected browser operations are therefore expected to return 401 with API
   auth enabled. This is source evidence, not a newly observed browser rehearsal.
   The [local overlay](../../deploy/local.compose.yml) disables API auth for the
   trusted single-user loopback profile; it cannot prove scoped pilot access.
   Do not expose an unauthenticated API, embed keys in browser code or silently
   substitute a shared admin key to make the journey pass.
2. **Decision and execution are separate.** `decideLiveApproval` sends only the
   decision; the API persists it. API/CLI resume must follow. A synchronous resume
   timeout is not proof that the server did nothing: inspect status/events first.
   CLI's default 330-second wait does not change server execution bounds.
3. **Inspection is not a complete answer journey.** The live Web lookup does not
   render full `Run.output`. Knowledge search shows retrieved passages, not the
   Agent's synthesized answer. Inspect the answer and supporting sources via API/CLI.
4. **Explicit-tool smoke is not native synthesis.** The deployment smoke queues
   an explicit `input.tool` `kb_search`. It does not show a live model selecting
   that tool, synthesizing supported claims or completing multi-round approval.
5. **Persisted evals can be fixture results.** CLI `eval report` uses
   `_cheap_rag_retrieve_for_cases`, deriving responses from case expectations;
   `--publish` saves that report. Neither persistence nor a Web report converts
   it into independent retrieval/live-answer quality evidence.

The maintainer selected the authenticated API/CLI-only rehearsal. It leaves
authenticated Web unaccepted, without reducing the eventual product goal.
Do not combine auth-disabled Web and authenticated API demonstrations into one
claimed authenticated browser journey. PV1/PV2 remain open.

## Manual Provenance Contract

[PromptRegistry](../../packages/kernel-runtime/src/kernel_runtime/prompts.py)
holds immutable in-memory versions. The inspected execution entry path does not
select a registry version or bind it to Run/eval records.
[`_request_from_run`](../../packages/kernel-runtime/src/kernel_runtime/execution.py)
builds model/messages from Run input; CF1 prepends fixed policy and bounded
untrusted memory when selected. Native execution adds tool schemas and stores
private continuation state. This is not CF3 automatic prompt-version binding.

Evidence contract implemented for the offline rehearsal below, **not yet accepted
for a real pilot profile**:

- Pin Git SHA, lockfile digests, built image IDs and exact Compose files/profile.
  Hash an explicit non-secret configuration allowlist, never an environment dump
  or secret-bearing rendered Compose output.
- Record effective API/Worker model routes/fallbacks, embeddings/dimensions,
  execution/retry limits, memory context version, tool binding/schema digests,
  corpus/dataset revision and admitted roles/workspaces.
- Keep raw input, effective provider request bodies, tool results, checkpoints
  and their digests in restricted local evidence storage. Exclude credentials
  and authorization headers even there; do not publish private data or potentially
  identifying hashes in public logs, telemetry or the sanitized report.
- Define one serializer before measurement: UTF-8 JSON, sorted object keys,
  preserved array order, compact separators and finite numbers only; SHA-256
  over those bytes. This is an evidence convention, not a new runtime API.
- Capture the actual adapter boundary on initial and resumed calls with an
  offline transport fixture in the isolated harness. Hashing a prompt file or
  registry object alone is insufficient. Label this fixture evidence, not live.
- Record every call separately. Resume appends assistant/tool messages, so full
  request digests should not be forced equal. Verify preserved history, pinned
  memory, tool contracts and route constraints; record tightened budgets.
- Link calls to Run/trace/tool/approval IDs and frozen cases. Public evidence
  contains sanitized outcomes/references, not request or checkpoint dumps.

## Existing Evidence

The previous [CI run 43592058574](https://github.com/royliu1105/agent-kernel/actions/runs/43592058574)
was rechecked: all four jobs passed at the candidate above. This is existing
candidate evidence, not a newly completed CF2 rehearsal.

| Test/source | What it establishes | What it does not establish |
| --- | --- | --- |
| [CLI tests](../../tests/unit/test_cli_commands.py) | Endpoint/body/header construction and resume timeout. | Real authenticated CLI-to-Docker journey; transports are mocked. |
| [Workbench smoke](../../apps/web/e2e/workbench.smoke.spec.ts) | Navigation/fixture-backed presentation and decisions. | Real mutations; `page.route` fulfills business responses. |
| [Docker browser smoke](../../apps/web/e2e/docker-runtime.spec.ts) | Real health/KB proxy access and desktop/mobile rendering when enabled. | Authenticated submit/approve/resume/answer workflow. |
| [HTTP deployment smoke](../../tests/integration/test_self_hosted_hardening.py) | Real upload/index/retrieve, Worker execution and explicit MCP approval/resume. | Live quality, browser/CLI journey or selected pilot profile. |
| [Native wire tests](../../tests/integration/test_native_continuation_wire.py) | Adapter history across Worker/API approvals, scoped fixtures and effect counts. | Live provider acceptance or full Docker/browser path. |
| [CF1 regressions](../../tests/integration/test_memory_context_security.py) | Memory limits, policy/approval effects and saved-context boundaries. | General injection immunity or acceptance of active local deployment. |

The selected API/CLI path and private provenance manifest were subsequently
verified below, without intercepting API business responses. Keep paid providers,
real email and the user pilot separate. Do not update the active stack to obtain
evidence. Missing Web-auth or pilot-profile provenance remains explicit, not a
reason to pass CF2 or expand CF3-CF8.

## Inventory Verification

This step uses source inspection and credential-free local unit/document checks,
not PostgreSQL fixtures, runtime business records, browser/server startup or Docker
operations. The following checks passed: **134 tests, no skips, in 1.09 s**.

```bash
.venv/bin/pytest -q tests/unit/test_docs_consistency.py tests/unit/test_cli_commands.py tests/unit/test_prompt_registry.py tests/unit/test_execution_limits.py tests/unit/test_observability_full_templates.py
git diff --check
```

These are document, CLI/transport-fixture, registry and budget contracts, not a
real backend/browser rehearsal. Learning evidence is limited to Codex's boundary
explanation; independent understanding is not assessed. The next-path selection
was subsequently answered: API/CLI first, Web authentication remains open.

## Selected Rehearsal Contract

Implementation and scoped review: Codex; residual-risk/pilot admission: maintainer,
pending. The maintainer requested a professional demonstration of the approval
evidence chain, not an independent learner assessment.

- Use a fresh random Compose project, internal-only network, private evidence,
  disposable PostgreSQL/Redis/object volumes and containerized API/Worker/CLI.
  Do not restart, migrate or write to `agent-kernel-local`.
- Exercise actual HTTP routes through the CLI and API with separate operator,
  viewer and other-workspace identities. Include upload/index/retrieve, queued
  native execution, approval, API restart/continuation, duplicate/denied resume,
  rejection and cancellation. Retain persisted records and invocation counts.
- The production router does not expose a configurable OpenAI endpoint. A
  test-only container entrypoint substitutes an offline HTTP transport in the
  real OpenAI adapter. It does not replace the API, Worker, repositories, policy,
  tool registry or MCP execution. Record actual adapter request bodies privately.
  Synthetic responses and mock embeddings are not live model/quality evidence.
- Approval demonstration: zero invocations while waiting and after decision;
  one invocation after resume; matching stored tool-call ID and completion event;
  repeated resume rejected without a second effect. This does not establish
  distributed exactly-once effects under arbitrary crashes.
- Record checks only after execution. CF2/PV2 stay open for unresolved surfaces,
  pilot-profile freeze and review. No paid calls, real email, commit/push or
  active local deployment is included.

## Docker Rehearsal Evidence

This section preserves the initial **pre-repair** rehearsal. The later
[rejection repair evidence](2026-11-14-approval-rejection-repair.md) is separate.
The final run of that initial [cf2_rehearsal.py](../../scripts/cf2_rehearsal.py)
candidate exited **0**.
It builds the maintained Python Dockerfile, runs fresh PostgreSQL/Redis/API/Worker,
and invokes the installed CLI inside Docker against actual authenticated HTTP
routes. Its only provider replacement is the
[offline adapter transport](../../tests/fixtures/cf2_runtime.py); MCP runs as a
separate subprocess with an on-disk invocation ledger. The
[scenario](../../tests/fixtures/cf2_scenario.py) asserts all results below.

| Check | Observed result | Limit |
| --- | --- | --- |
| Upload, ingest, chunk, index, retrieve | CLI performed actual operations; returned KB/document/chunk citation identities agree. | One synthetic Markdown document; mock 8-dimensional embeddings, not retrieval-quality scoring. |
| Native execution | Worker made two adapter requests: `kb_search`, then protected MCP lookup; Run waited for approval. | Deterministic offline model responses, not live model selection quality. |
| Missing key / viewer / other workspace | 401 / 403 / 404 for approve/resume; cross-workspace Run, approval and KB hidden; no new provider request/effect. | Selected endpoints/roles, not an exhaustive authorization audit. |
| Approval decision | `approved` and reviewer principal persisted; Run still waited; protected-tool count **0**. | Decision is not execution. |
| API restart + resume | Private checkpoint unchanged across restart; CLI resume succeeded; protected-tool count **1**. | Clean API process restart, not arbitrary crash/HA proof. |
| Correlation | CLI/API output and events agree; two completed tool IDs match stored records and provider result IDs; answer cites the actual retrieved chunk. | Fixture answer copies a real retrieval result; no live synthesis-quality claim. |
| Duplicate resume | 409; count still **1**, no extra provider request. | No universal distributed exactly-once claim. |
| Rejection | Run failed with `approval_rejected`; rejected case invoked protected tool **0** times; another resume returned 409. | Tool record stays `waiting_approval`; see residual issue below. |
| Stop | Created Run canceled before queue; subsequent queue returned 409; zero provider/tool work. | Does not test mid-flight cancellation or undo external effects. |
| Memory and continuation | Adversarial memory stayed an untrusted user message; deleting its DB row after approval did not change pinned continuation. Request prefixes/tool schemas preserved; three request digests differed as history grew. | Validates boundary/permission mechanics, not general prompt-injection immunity. |
| Provenance | Actual normalized/wire requests, input, checkpoints, tool results, source/lock/image/config hashes and effective API/Worker limits/retry/embedding configuration retained privately. Effective API/Worker configuration matched. | Manual fixture revision, not automatic CF3 prompt-version binding. |
| Isolation and cleanup | Actual Docker network verified internal; no published ports. All temporary containers, networks and volumes removed; all **13** active container IDs/images/start times/statuses unchanged. | No active runtime rebuild/migration/business request was made. |

Initial rehearsal's final private evidence directory (pre-repair):
`.agent-kernel/agent-kernel-cf2-b10ebc273f6673ba/` (ignored, directory 0700).
`manifest.json` records revision `cf2-api-cli-offline-v1`, exact file hashes,
canonical configuration hash and a passed credential scan. `provider.jsonl`
records the adapter boundary without authorization headers. Raw IDs, inputs,
checkpoints and document content remain private. Generated API/DB credentials
and secret-bearing temporary Compose configuration were removed after teardown.
The candidate image tag remains available for inspection; no existing image was
removed. This evidence is not suitable for public raw-artifact upload.

Two earlier harness attempts failed before acceptance: first Docker rejected
`local` log compression with `max-file=1`; then a checkpoint observer incorrectly
called an execution-lease-protected repository method. The harness now uses
three log files and reads the isolated DB record without mutating/acquiring a
lease. Neither failure required weakening production guards or business-code
changes. Both attempts cleaned their temporary resources and preserved the
active stack. One intermediate full scenario passed before final manifest checks
were added; only the final directory above is the complete evidence set.

Verification commands:

```bash
.venv/bin/python scripts/cf2_rehearsal.py
.venv/bin/pytest -q tests/unit/test_cf2_rehearsal.py tests/unit/test_docs_consistency.py tests/unit/test_cli_commands.py tests/unit/test_prompt_registry.py tests/unit/test_execution_limits.py tests/unit/test_observability_full_templates.py
.venv/bin/ruff check scripts/cf2_rehearsal.py tests/fixtures/cf2_runtime.py tests/fixtures/cf2_scenario.py tests/unit/test_cf2_rehearsal.py
.venv/bin/mypy .
git diff --check
```

Focused suite: **152 passed, no skips** (18 new harness tests). Mypy:
**234 source files passed**. Ruff passed. No full PostgreSQL test-suite rerun,
new remote CI, commit/push or active-stack deployment is claimed by this step.
The rehearsal is opt-in, not automatically part of CI. Rerunning it creates and
deletes only its own new disposable project; do not substitute `make docker-up`.

An additional whole-repository `ruff format --check .` check reported three
unchanged baseline files: `kernel_evals/rag.py`, `kernel_evals/tool_calls.py` and
`kernel_identity/authorizer.py`. Their Git diff is empty. They were deliberately
not reformatted in this test/documentation scope. Full-repository Ruff lint and
format checking of the four new Python files passed; this is not a claim that
the entire repository's format check is green.

## Remaining Gates and Learning

CF2 is **not closed**. Authenticated Web is still missing, and the real pilot
profile/corpus/provider/budget and risk disposition remain unaccepted. At this
2026-11-14 checkpoint, PV1-PV6 had not started. The subsequent
[PV1 draft](../pilots/pv1-2026-11-15-runbook-assistant.md) records planning only,
not acceptance of this gate. Do not reuse the offline fixture as paid-model or user evidence.

**Observed residual issue:** rejection terminates the Run but leaves its protected
tool row at `waiting_approval` with no result. This did not execute the tool or
allow repeated resume, but status consumers can misread it as still actionable.
The maintainer subsequently authorized the minimal rejected-approval terminal
repair with regressions and documentation. Its
[separate repair record](2026-11-14-approval-rejection-repair.md) tracks scoped
verification; the initial evidence above remains the pre-repair observation.
Expired/canceled lifecycle changes and historical backfills are excluded; their
existing fail-closed behavior must not regress. Do not silently change records
in the harness. Web-auth work remains deferred.

### Rejection Repair Acceptance

The following scoped checks passed locally, including full Python regression
and a fresh isolated Docker rehearsal. See the
[repair ledger](2026-11-14-approval-rejection-repair.md#verification-ledger) for
counts, skipped profiles and exact private evidence. This is not active deployment,
remote CI or overall CF2 acceptance; the initial pre-repair evidence is unchanged.

- Preserve decision-only `reject`: `resume` remains the terminal-processing step.
- Atomically persist the matching tool as `denied`, the Run as `failed` with
  `approval_rejected`, and linked ordered terminal events under the execution lease.
- No tool/provider invocation on rejection; preserve earlier completed results.
- Repeated/concurrent resume adds no duplicate terminal writes or effects.
- Inject a failure before commit and prove both state/event changes roll back;
  reject stale owners, mismatched approvals and already-terminal Runs.
- Verify explicit and provider-native paths, API/CLI and fresh database sessions.
- Use only disposable PostgreSQL/Docker fixtures; no active runtime update,
  schema migration requirement, historical-row repair or paid provider calls.

Learning checkpoint: the maintainer requested a professional demonstration.
The demonstrated chain is **decision -> actual invocation -> durable tool record
-> completion event -> duplicate denial**, not just a 200 response or green test.
Both traceable records and an independent effect counter are needed: the residual
tool status above shows why either view alone can mislead. Learning status:
**demonstrated by Codex**, not independently practiced or assessed. A later short
exercise can ask what changes if a remote effect succeeds just before the process
crashes and before its database transaction commits; this rehearsal does not
prove exactly-once execution in that failure window.
