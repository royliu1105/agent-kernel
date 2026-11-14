# CF1 Baseline and Memory Boundary Review

Date: **2026-11-14**. Scope: read-only source review, temporary fixture probes and
existing regressions. **No business implementation changed, no repair accepted.**
The canonical CF1 status remains in the [follow-up ledger](../reference-follow-up-plan.md).
PV1-PV6 have not started; no pilot candidate, budget, model or participants have
been approved by this review. No commit/push or external call was performed.

## Working Tree Baseline

HEAD is `d599fc2ab44c054af009aabb7cab298d4988f4eb`, but the reviewed runtime is
the dirty working tree, not that commit alone. Before this review's documentation
updates: 143 tracked modified files, 33 untracked maintained files and zero
staged paths. `resource/` is excluded from these counts and must not be staged
as part of baseline consolidation. Existing changes were not reverted.

Source/config/test fingerprint: **303 files**, SHA-256
`8dd9d280882c786af9b7fc18ae16a098a5a4cb847d8c13de9c395e14471cbc0b`.
This identifies local reviewed inputs, not a committed/released candidate.
It does not include runtime secrets, data, images or the reference project.

Fingerprint method: sorted unique file paths from
`git ls-files --cached --others --exclude-standard` under `apps`, `packages`,
`scripts`, `tests`, `deploy`, `evals`, `.github`, plus `.dockerignore`,
`.env.example`, `Makefile`, `pyproject.toml`, `uv.lock`, `package.json`,
`package-lock.json`, `docker-compose.yml`, `alembic.ini`. Hash the concatenation
of each UTF-8 path, NUL, raw file bytes, NUL. Documentation-only edits are outside
this fingerprint. A later implementation requires a new fingerprint and commit.
At review close, the same 303 files produced the same digest: maintained source,
configuration and tests were unchanged by this review.

### Change Groups Before a Commit

| Group | Existing changes | Coupling and commit boundary |
| --- | --- | --- |
| PostgreSQL-only | Storage URL/migration/session cleanup, isolated test service/helper, database test conversion and operator documentation. | Keep storage and test conversion together; CI PostgreSQL configuration and Make test targets must match. |
| Full observability | File logging, OTel dependency extra, collector/backends, local SMTP, rehearsal and tests. | Requires matching Docker build/dependency lock, Compose overlays and CI rehearsal. |
| Docker-only runtime | Local stack wrapper/configuration, Web API proxy and browser target, startup/data-retention docs and AGENTS rules. | Shares CI/Make/build files with the two groups above. |
| Planning and evidence | Pilot/learning/comparison/follow-up documents and index links. | Can be a separate documentation commit once all referenced maintained files exist. |

These are proposed groups, not staged commits or independently verified intermediate
states. Splitting shared files requires deliberate hunks and verification at each
candidate. If runtime groups cannot pass independently, keep the coupled runtime
changes together and separate the planning record. Do not use an indiscriminate
`git add .`; never include reference code, private runtime files or business data.
The final commit/push and exact-candidate CI still require explicit authorization.

## Inspected Execution Path

| Boundary | Actual behavior and source | Meaning for the pilot |
| --- | --- | --- |
| Write entry | CLI `create_memory` calls the API. API create/delete require `MEMORY_WRITE` when auth is enabled. [CLI](../../apps/cli/src/agent_kernel_cli/main.py), [API](../../apps/api/src/agent_kernel_api/main.py). | This is not an anonymous write path in the authenticated profile. The default Docker localhost profile is deliberately unauthenticated and is not a multi-user pilot profile. |
| Roles | Owner/admin/operator can write memory; viewer can read. [Role permissions](../../packages/kernel-identity/src/kernel_identity/authorizer.py). | Permission to store data does not make its content trusted system instructions. Operator also has approval-review rights; do not promise independent two-person approval without a separate role decision. |
| Ownership | Repository/API use authenticated workspace; runtime uses persisted Run workspace. Same-workspace `source_run_id` is checked. [Repository](../../packages/kernel-storage/src/kernel_storage/repositories.py). | `scope` such as `user:roy` is a caller-supplied filter, not a per-user ACL. A source Run link is provenance association, not verified truth. Freeze shared-workspace assumptions in PV1. |
| Selection | `_explicit_memory_request_from_run` accepts caller-selected scopes/types/positive limit; `_memory_context_from_run` loads the records. [Execution](../../packages/kernel-runtime/src/kernel_runtime/execution.py). | No memory exclusion was established. `Agent.memory_policy` is stored/exposed but no execution enforcement was found; it cannot be advertised as an off switch. |
| Rendering | `MemoryContext.to_prompt_text` JSON-serializes content into text; `_request_from_run` places it in a SYSTEM message. [Memory rendering](../../packages/kernel-memory/src/kernel_memory/retrieval.py). | JSON serialization is not a trust boundary. Instruction-like text reaches the high-priority context; this is reproduced request construction, not a demonstrated live-model exploit. |
| Dispatch | `_drive_native_loop` consults tool metadata/policy and persisted approval identity/status before `_execute_tool_call_only`. [Policy](../../packages/kernel-policy/src/kernel_policy/evaluator.py). | Model-generated calls are proposals, not authorization. Text cannot itself change the static policy decision in the tested path. |
| Resume | `_resume_claimed` loads NativeState and validates run/cursor/call/provider/tool contracts; continuation uses the saved request. [State](../../packages/kernel-runtime/src/kernel_runtime/native_state.py). | Deleting the memory row does not rewrite already persisted execution history. A trust-format repair must consider existing memory-bearing checkpoints. |
| Size limits | NativeState serialization enforces `max_history_bytes` before the provider call. Memory create has no content-byte bound; run recall has no hard maximum count/scopes bound in the inspected path. | Provider/history safety exists, but it is checked after retrieval/rendering. This does not prove bounded database/CPU/memory work at ingress. No load/DoS experiment was run. |

## Fixture Evidence

Temporary script: `/tmp/agent-kernel-cf1-probe.py`, SHA-256
`7a83b35ccf17dbe3051b3c418aacf23114eee66bd72e5f1aa7db8d07a18276fe`.
It reuses `CountingTool`, `ScriptedProvider`, `reply` and `call` from the existing
bounded-execution tests. The fake provider always proposes a predetermined call;
it does not interpret or obey the memory. Tool execution only increments an
in-process counter. No real model, network tool or external write was used.

The script used the guarded `isolated_database()` helper on the dedicated
`agent-kernel-test` PostgreSQL service. A fresh schema was migrated and removed.
Instruction-like memory and a forged text delimiter were fixture data only.

| Scenario | Assertions and observed result |
| --- | --- |
| Approve | Initial state waits for approval; undecided resume is rejected; counter remains 0. Approved resume through a new executor succeeds with exactly 1 call and 1 completion event; repeated terminal resume is rejected. Initial memory is SYSTEM content. |
| Reject | Initial state waits with counter 0; rejected resume ends failed with 0 calls, 0 tool completion events and no continuation provider request. Repeated terminal resume is rejected. |
| Explicit deny | Even with instruction-like memory and a proposed write call, run fails with `tool_denied`, persisted call is denied and counter remains 0. |
| Oversized memory | A 10,000-character memory with a 2,048-byte history limit fails with `execution_history_bytes_limit`; provider and tool call counts are both 0. Retrieval/rendering occurred before this check. |
| Workspace isolation | Matching scope label in workspace B is not retrieved for workspace A; retrieval event count is 0 and the captured provider request contains no B fixture content. |

In the approve scenario, the original memory row was deleted after pausing.
The resumed provider still received the exact original memory message from the
checkpoint. That confirms snapshot semantics; it is not proof of unauthorized
retrieval and is not a promise that memory deletion purges all prior records.
Retention/deletion and old-checkpoint behavior must be documented before repair.

Five fixture scenarios completed successfully. These are temporary observation
probes, NOT new committed regression tests or CF1 acceptance. They demonstrate
the exercised runtime controls, not resistance to every model injection,
inference-time disclosure, alternate tool or provider path.

### Existing Regressions and Static Checks

Command: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider
--junitxml=/tmp/agent-kernel-cf1-regressions.xml` with
`AGENT_KERNEL_TEST_POSTGRES_URL` set explicitly to the disposable test service,
and these files:

- `tests/unit/test_runtime_execution.py`
- `tests/unit/test_memory_retrieval.py`
- `tests/integration/test_memory_eval_isolation.py`
- `tests/integration/test_bounded_native_execution.py`
- `tests/integration/test_api_memory.py`
- `tests/unit/test_api_auth.py`

Result: **75 passed, zero skipped, 24.22 seconds**. JUnit SHA-256:
`1d8577be0823bd0064a17d9694b471a38dd34900f8c0f0a7d512d839d4ae1ee4`.
Ruff passed; mypy passed on 226 source files; `git diff --check` passed.
Documentation consistency passed 76 tests; 161 local links in the changed
documentation entry points were checked with no missing targets.
These are current local results, not a full-suite rerun or remote CI.
Temporary artifacts may disappear; formal repair must retain its own regressions
and sanitized evidence. The earlier 128-test comparison run is separate and overlaps.

The review-created test service was stopped/removed with `make test-db-down`.
All 13 pre-existing `agent-kernel-local` containers remained running. No business
DB query, fixture insertion, restart, migration or volume deletion was performed
against that project in this review.

## Minimal Repair Proposal, Not Implementation

1. Define memory as untrusted data at the provider boundary. Keep trusted rules
   separate, preserve provenance, encode arbitrary content and make initial and
   continuation paths use the same contract. Do not invent unmatched provider
   tool messages to get a lower-trust role. Prompt instructions alone are not
   the security enforcement mechanism.
2. Bound memory intake and recall work: content bytes, number of scopes/items
   and total rendered context before expensive processing where practical.
   Retain the existing history/token/runtime limits as independent protections.
3. Define a versioned memory-context/checkpoint compatibility rule. Do not
   silently reinterpret old memory-bearing snapshots as safe after changing the
   renderer. Fail closed for unsupported state or provide an explicitly tested
   migration; preserve unrelated no-memory continuation behavior.
4. Promote the necessary adversarial cases into maintained tests, including
   API role-specific writes, forged boundaries, oversized input, denied tools,
   approval/reject/repeat/new-executor continuation and workspace isolation.
   Demonstrate a failing assertion for the intended repaired contract before
   implementation, then passing behavior afterward. Reusing old green tests is
   not sufficient; live-model attack cases remain a separately authorized PV3 gate.

No automatic memory extraction, semantic search, prompt management platform,
general sandbox, multi-agent engine or identity redesign is needed for this
minimal proposal. A memory-disabled pilot is not yet a proven alternative:
the admitted API path must enforce exclusion, not merely omit a sample field.

Open before implementation: confirm the minimal contract and exclusions, assign
the final reviewer, authorize business-code repair, decide old-checkpoint behavior
and choose concrete size limits. The maintainer remains the scope owner; Codex
performed this review. No independent reviewer sign-off is claimed.

## Learning Checkpoint

The maintainer was asked which assertion would establish that instruction-like
memory did not bypass approval. They requested a professional demonstration;
no learner prediction or independent assertion was supplied. Codex explained
counter/persisted-event assertions, then ran the fixture scenarios above.

Learning status: **Demonstrated by Codex; independent understanding unverified**.
This is a CF1 pre-pilot demonstration, not a completed PV learning session.
This learning note is local evidence; obtain maintainer approval before publishing it.
The technical result is deliberately separate: several controls were verified,
while CF1 repair and overall acceptance remain open. The next learning point is
why changing new-request rendering alone does not change a saved approval checkpoint.
