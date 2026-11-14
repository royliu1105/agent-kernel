# Reference Project Comparison

Review date: **2026-11-14**. Status: **Read-only comparison recorded; no
remediation or feature acceptance implied**.

Implementation priorities and status live in the separate
[reference follow-up plan](reference-follow-up-plan.md). User-facing validation
still belongs to the [PV1-PV6 pilot plan](real-scenario-pilot-plan.md).

## Scope and Evidence Boundary

- Maintained project: the Python/TypeScript working tree at repository HEAD
  `d599fc2ab44c054af009aabb7cab298d4988f4eb`, including existing uncommitted
  Docker-only, PostgreSQL-only and observability changes. This is NOT an audit
  of that commit alone, the published v1.0.0 tag, or a clean release candidate.
- Reference: the user-provided `resource/agent-kernel` TypeScript project.
  Its upstream provenance/commit and redistribution license were not verified.
  It is not a maintained dependency or a second runtime to deploy.
- Reference paths below are relative to `resource/agent-kernel`. They are
  intentionally code locators rather than required Markdown links: a normal
  checkout need not contain this local reference material.
- Inspection covered execution entry points, providers, tools, storage,
  approvals, memory/RAG, prompts, UI, evals, observability, deployment and tests.
  This was not an exhaustive security audit, load test or live-model benchmark.
- Reference tests ran in a temporary source-only copy without its `.env`,
  business data or original runtime. Local test harnesses used fixtures; no
  paid calls, external email, reference deployment or live-user trial ran.
- Current database tests used the separate disposable `agent-kernel-test`
  PostgreSQL service, never the active `agent-kernel-local` database. The test
  service was removed after verification; existing runtime data was untouched.

Historical CI links in other documents do not verify this dirty working tree.
Test counts below are observations, not a maturity score or completion percentage.

## Overall Assessment

The reference has broader Agent strategies and a more connected interactive
product: chat, sessions, streaming, orchestration and automatic memory handling.
The maintained project has more explicit deployment boundaries and stronger
focused evidence for bounded execution, ownership fencing, scoped resources,
external-tool controls and the local observability stack.

Neither conclusion means that all originally envisioned capabilities are done.
The maintained project still lacks a complete chat/task-creation Web journey,
general multi-agent orchestration, automatic memory lifecycle and effective
runtime prompt-version binding. The reference also contains incomplete paths
and concrete security/reliability defects. Keep the Python runtime and
TypeScript product surface; borrow behavior and tests, not whole directories.

## Capability Comparison

| Area | Maintained implementation | Reference implementation | Practical conclusion |
| --- | --- | --- | --- |
| Product journey | Live run lookup/events, approvals, KB retrieval and eval views coexist with fixture/preview views; no complete chat submission journey. | Console submits chat, lists runs, cancels, approves and follows SSE; WS is also wired. | Reference is closer to direct user operation; verify actual browser journeys before claiming usability. |
| Providers | Mock/OpenAI/replay routing and native tool continuation; provider protocol exposes non-streaming `complete`. | OpenAI-compatible/OpenAI/Anthropic/Gemini/Ollama adapters; OpenAI supports actual deltas. Several other `chatStream` methods wrap a completed response. | Adapter count is not protocol or streaming parity. |
| Agent loop | Bounded native rounds, serial tool batches, persisted continuation, limits, usage and cancellable backoff. | ReAct, planning, tool selection and reflection; more strategy switches. Reflection does not establish a complete autonomous repair loop. | Preserve current execution contracts when adding strategies. |
| Multi-agent | No general graph orchestrator or durable handoff engine found. | Supervisor/rule plans, role tools, DAG scheduling and shared blackboard. Graph progress is mainly in memory. | Useful design reference, not a drop-in durable workflow engine. |
| Worker | Separate Worker app; database polling remains authoritative with optional Redis hints; each Worker processes its loop serially. | Background executor starts inside the API process, with bounded concurrent dispatch. | Current separation is clearer; neither arrangement alone proves capacity. |
| Recovery | Lease fencing, heartbeat, concurrent-resume guards and approval checkpoints; expired execution is normally failed safely. | Durable single-agent approval recovery and job requeue paths; multi-agent approval continuation is explicitly rejected. | Neither promises arbitrary crash-point resume or exactly-once external effects. |
| Memory | Scoped typed records, CRUD and explicit injection; retrieval filters and sorts by recency. | Token windows, summaries, fact extraction, semantic recall, TTL, confidence and deletion. | Reference lifecycle is richer; automatic writes need a trust/provenance design first. |
| Knowledge base | Separate document/object/chunk/index/retrieval/citation lifecycle with workspace scope and pgvector. Text/Markdown parsing is not general PDF/OCR ingestion. | Primarily memory-oriented vector retrieval with multiple adapters. | Current domain boundaries better support traceable KB answers. Neither has a complete RRF hybrid-retrieval pipeline. |
| Prompt versions | Immutable in-memory registry exists, but no effective version/snapshot binding in the execution entry path was found. | YAML templates, manifest and selection/reload facilities; main prompt builder is used. Canary key propagation and failed reload have gaps. | Integrate and test the whole lifecycle, not just a registry. |
| External tools | Official MCP SDK, fixed operator-owned bindings, scope/policy checks, retry eligibility, deadlines and pinned validated IP connections. | Broader built-in tools and custom MCP transport implementation. | Prefer current boundaries; neither is an OS sandbox for untrusted executable tools. |
| Evals/feedback | Persisted eval records, isolation, behavior cases and replay through the actual runtime to compare timelines. | Trace scoring, provider fixtures and failure-to-case-draft feedback reports. | Borrow reviewed case generation; scoring a saved trace is not re-executing current code. |
| Observability | Docker logging/Trace/metrics/alerts/Mailpit backend configuration and end-to-end rehearsal. | Structured logs, metrics, OTel export and dashboards; bundled deployment lacks the complete log/Trace backend and notification receiver chain. | Local backend delivery is stronger here; external inbox delivery remains a separate gate. |
| Storage/deployment | PostgreSQL-only runtime/tests, optional Redis, local/S3 object adapters; current local profile uses local object volumes. | SQLite/PostgreSQL plus multiple vector adapters, increasing supported combinations. | Do not reintroduce SQLite or add backends just for parity. S3 adapter presence is not a restore acceptance result. |
| Maintainability | Package boundaries are explicit, but execution, repositories, API and Web page have large concentrated modules. | Fewer package boundaries, but AgentLoop/MCP/inline console also concentrate complexity. | Refactor touched boundaries when justified; a language rewrite does not solve this. |

### Maintained Source and Test Anchors

- [Execution](../packages/kernel-runtime/src/kernel_runtime/execution.py),
  [Worker](../packages/kernel-runtime/src/kernel_runtime/worker.py),
  [checkpoint/budget state](../packages/kernel-runtime/src/kernel_runtime/native_state.py)
  and [repository recovery](../packages/kernel-storage/src/kernel_storage/repositories.py):
  bounded rounds, ownership and deliberate fail-closed recovery.
- [Bounded execution tests](../tests/integration/test_bounded_native_execution.py),
  [ownership tests](../tests/integration/test_execution_ownership.py),
  [wire continuation tests](../tests/integration/test_native_continuation_wire.py)
  and [backoff tests](../tests/integration/test_runtime_backoff.py): repeated
  approvals, budget preservation, stale owners, continuation history and retry safety.
- [Provider protocol](../packages/kernel-providers/src/kernel_providers/base.py),
  [memory retrieval](../packages/kernel-memory/src/kernel_memory/retrieval.py),
  [prompt registry](../packages/kernel-runtime/src/kernel_runtime/prompts.py)
  and [Web page](../apps/web/src/app/page.tsx): the narrower capability boundaries
  above are visible in the actual entry paths, not inferred from package names.
- [RAG retrieval](../packages/kernel-rag/src/kernel_rag/retrieval.py),
  [object adapters](../packages/kernel-rag/src/kernel_rag/object_store.py),
  [HTTP transport](../packages/kernel-tools/src/kernel_tools/external/http.py)
  and [transport tests](../tests/unit/test_external_http_transport.py): citation
  lineage, replaceable storage and DNS/connection boundary checks.

### Reference Source and Test Anchors

- `src/server/routes/console.ts`, `src/server/routes/chat.ts`,
  `src/server/run-executor.ts` and `src/__tests__/run-executor.test.ts`:
  real submission/control paths and tested single-agent approval recovery.
- `src/agent/Orchestrator.ts`, `src/__tests__/orchestrator.test.ts`:
  role dispatch, dependency waves and bounded parallel execution, not durable DAG state.
- `src/llm/OpenAIClient.ts`, `src/agent/StreamingToolCallAccumulator.ts`,
  `src/__tests__/llm.test.ts`, `src/__tests__/streaming-toolcalls.test.ts`:
  fragmented tool-call assembly and no retry after partial stream delivery.
- `src/memory/LongTermMemory.ts`, `MemoryExtractor.ts`, `ShortTermMemory.ts`,
  `src/agent/PromptBuilder.ts`, `src/__tests__/memory-rag.test.ts`:
  memory lifecycle and explicit untrusted-content treatment. Text delimiters
  are useful context controls, not a security enforcement boundary by themselves.
- `src/prompts/PromptRegistry.ts`, `src/learning/learning-loop.ts`,
  `src/evals/trace-replay.ts`: prompt/feedback ideas to adapt with end-to-end tests.

## Findings and Adoption Restrictions

These findings are not repair acceptance. Reference-only defects do not imply
the maintained project has those same defects, and do not authorize editing
`resource/`. Severity describes exposure if the affected path is used.

| ID | Finding and evidence | Confidence and consequence | Follow-up |
| --- | --- | --- | --- |
| CUR-1 | At comparison time, `_request_from_run` placed `MemoryContext.to_prompt_text()` in a SYSTEM message without an explicit untrusted-data instruction boundary. | Static trust-boundary concern; no successful live-model exploit demonstrated. Scope isolation tests do not prove injection resistance. | CF1; subsequent [minimal repair evidence](reviews/2026-11-14-cf1-minimal-repair.md), not yet pilot admission. |
| CUR-2 | Web fixture/live mixture; in-memory prompt registry is not effective runtime version binding. | Source-confirmed capability gaps, not proof that existing scoped API workflows fail. | CF2 for truthful pilot instructions/provenance; CF3/CF4 for later product work. |
| REF-1 | `src/config/index.ts` supplies `change-me-in-production`; `Authenticator.verifyJwt` accepts HS256 and only compares `exp` with current time. | Reproduced in isolated defaults: a token with no `exp` and role `admin` was accepted. No claim about the private reference `.env`, which was not read. Critical if exposed with this default. | Do not port hand-written JWT/default-secret behavior; use maintained auth boundaries. |
| REF-2 | `AgentLoop.runLoop` yields `contentDelta` before final `checkOutput`. | Static ordering defect: a final redaction cannot retract streamed content. No paid-model exploit test performed. | CF4 must decide and test output policy before streaming. |
| REF-3 | `PromptRegistry.reload` saves the current Map reference; `load` clears it before validation. | Reproduced with a missing source directory: reload failed and the formerly available template became unknown. | CF3 must use validated immutable snapshots/atomic replacement if reload is implemented. |
| REF-4 | `buildSystemPrompt` supports `sessionId`, but the main AgentLoop call supplies only recalled memory and plan. | Static integration gap: registry canary support is not evidence of actual session-based canary execution. | CF3 requires entry-path tests; canary is optional, not an initial requirement. |
| REF-5 | `src/tools/security.ts` validates DNS, then `fetch` connects by hostname again. | Static DNS-rebinding/TOCTOU risk; no rebinding exploit run. | Preserve current pinned transport and deny tests. |
| REF-6 | `SemanticCache.get/set` scope by tenant and query, not effective role/session/prompt/model/corpus context. | Static reuse risk for context-dependent answers within one tenant; not a demonstrated cross-tenant breach. | Do not import answer caching by default; require a separate isolation/invalidation design. |
| REF-7 | `run-executor.ts` rejects multi-agent approval continuation; Orchestrator graph/blackboard state is in memory. | Explicit implementation limit despite tested ordinary orchestration. | CF7 requires durable node/edge and handoff contracts, not just a copied scheduler. |
| REF-8 | Local reference copy has no dependency lockfile; its workflow runs `npm ci`. | Clean-copy CI reproducibility gap; temporary `npm install` success is not proof of its upstream CI. | Verify provenance, license and reproducible dependencies before copying implementation. |

Provider caveat: `AnthropicClient` and `GeminiClient` encode prior tool
calls/results as text rather than preserving provider-native continuation blocks;
several adapters wrap full `chat()` results as a stream. Fixture mapping tests do
not prove live native multi-round equivalence. New providers require their own
contract and authorized live acceptance, not a configuration-name addition.

## Verification Record

| Check | Observed result | What it does not prove |
| --- | --- | --- |
| Maintained focused Python suite | 128 passed, no skips, 46.82 seconds; separate PostgreSQL database. | Not a new full-suite, deployment, release or remote-CI run. |
| Reference TypeScript typecheck | Passed with original copied dependencies and again after clean temporary install. | Types do not validate runtime authorization or recovery. |
| Reference Vitest run | 38 files passed, 2 skipped; 325 tests passed, 30 skipped, 16.97 seconds. | No real-model quality, real browser journey or production capacity evidence. |
| Reference real-backend cases | Skips in `pgvector.test.ts`, `milvus-vector-store.test.ts`, `postgres-transaction-store-contract.test.ts`, `postgres-approval-continuation-migration.test.ts`. | These backend contracts were NOT accepted; mock backend tests are separate. |
| REF-1 and REF-3 focused probes | Both behavior defects reproduced in the temporary copy; final probe exited successfully. | Probes are review evidence, not yet committed regression tests or fixes. |
| Active local stack | All 13 existing containers still running after review; no business data operation performed. | A process-status check is not a fresh full observability/health rehearsal. |

The first reference Vitest attempt was blocked by macOS native-module loading
policy in the supplied dependencies. No security policy was disabled. A clean
dependency installation in a temporary copy resolved that startup problem.
The reference suite used fake model credentials and loopback-only provider URLs;
its own temporary SQLite fixtures do not restore SQLite support to this project.

The focused Python invocation was:

```bash
# First use make test-db-up and the isolated URL from docs/postgresql-only.md.
# Never substitute the active runtime DATABASE_URL.
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider \
  --junitxml=/tmp/agent-kernel-current-review.xml \
  tests/integration/test_bounded_native_execution.py \
  tests/integration/test_execution_ownership.py \
  tests/integration/test_native_continuation_wire.py \
  tests/integration/test_runtime_backoff.py \
  tests/integration/test_execution_budget_edges.py \
  tests/integration/test_operational_scope.py \
  tests/integration/test_memory_eval_isolation.py \
  tests/integration/test_knowledge_workspace_isolation.py \
  tests/integration/test_runtime_tracing.py \
  tests/unit/test_external_http_transport.py \
  tests/unit/test_prompt_registry.py \
  tests/unit/test_memory_retrieval.py \
  tests/unit/test_rag_evals.py \
  tests/unit/test_eval_comparison.py
make test-db-down
```

`AGENT_KERNEL_TEST_POSTGRES_URL` was explicitly set to the separate test service
for that invocation. Reference commands, executed only in the sanitized temporary
copy with Node 24.16.0, were `npm install --no-audit --no-fund`,
`tsc --noEmit --incremental false` and
`vitest run --maxWorkers=1 --no-cache --configLoader=runner` with default/JSON
reporters. The clean install resolved Vitest 4.1.12; the original reference copy
and its dependencies were not changed.

Temporary evidence locations on the review machine, not durable public artifacts:

| Artifact | Location | SHA-256 |
| --- | --- | --- |
| Maintained JUnit result | `/tmp/agent-kernel-current-review.xml` | `5026e79518627021bf34e83cf580d01142cfb166e7a362be7ab5ab6eb7be0dfb` |
| Reference Vitest result | `/tmp/agent-kernel-reference-review.XkAwBW/test-results.json` | `7f2454de8a5055fcb6e9efe10708f1ff84f4c3c19600fe7d7668f0ee965e77d7` |
| Temporary resolved dependency lock | `/tmp/agent-kernel-reference-review.XkAwBW/package-lock.json` | `e65d30b3ca32c44ed1fd3dbfdbe33df33c1e65963bb4a46025cac9645ab39f76` |

These hashes identify outputs/dependencies, not a source snapshot or security
attestation. Temporary files may disappear. Future acceptance must rerun on a
pinned candidate, retain sanitized evidence and record its own CI; do not reuse
these results to mark the [follow-up tasks](reference-follow-up-plan.md) passed.
