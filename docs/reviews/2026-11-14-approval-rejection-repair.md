# Rejected Approval Terminal Consistency

Date: **2026-11-14**. Status: **implementation, full local regression and isolated
Docker verification passed; not deployed to the active runtime**.

This is the maintainer-authorized minimal repair of the residual issue observed
in the [CF2 rehearsal](2026-11-14-cf2-workflow-inventory.md). Its initial scope did
not include commit/push; the later review authorization is recorded below.
It does not close CF2, admit pilot users or authorize active deployment,
historical backfills, paid providers or release. Implementation/review: Codex; this is not an
independent audit. Runtime base is `bef87a94b5c50405ba104298839367c4b53b0fcc` plus
the then-uncommitted repair and existing CF2 harness/docs. Remote verification
is tracked separately below, not inferred from local results.

## Cause and Repair

The rejected branch of `_resume_claimed` called a helper that only used
`RunRepository.fail`. The Run became `failed`, but its approval-protected tool
remained `waiting_approval` with no terminal event. Existing tests checked the
Run error and absence of effects, not the tool's terminal status.

The [Runtime change](../../packages/kernel-runtime/src/kernel_runtime/execution.py)
delegates to
[`RunRepository.fail_rejected_approval`](../../packages/kernel-storage/src/kernel_storage/repositories.py).
This method locks the Run, validates the live execution lease and re-reads the
approval/tool relationships and statuses, then commits together:

- matching tool: `denied`, `error_type=approval_rejected`, saved reason;
- Run: `failed`, same error/reason and terminal timestamp;
- ordered `tool_call_failed` and `run_failed` events linked to the approval/tool.
  The tool event says `status=denied` and `execution_skipped=true`; it is not an
  assertion that a remote tool ran and failed.

The first event is flushed to allocate the next sequence, **not committed**.
A single final commit makes both states and events visible together. The runtime
failure log now follows the successful commit, so rollback does not log a durable
Run failure. No model/tool call is added. No new schema/status enum is introduced.

Calling `ToolCallRepository.fail` and `RunRepository.fail` separately was rejected:
both commit independently, and the first could survive failure of the second.
This focused repository operation follows the existing Run-first lock/lease
pattern without introducing a generic transaction framework.

## Contract and Limits

See [approval semantics](../specs/approval-resume.md#rejected-continuation-consistency).
`reject` still saves only the human decision; **the explicit resume processes its
terminal outcome**. Until resume, the Run/tool still wait. A rejected resume
does not execute anything. Approved, requested, expired and canceled behavior is
not broadened by this repair. Only the tool referenced by this rejected approval
is finalized; unrelated calls and earlier successful results are not rewritten.

There is no data migration or bulk repair. Already-terminal historical Runs
are not resumable and their old tool rows are not silently changed. Fixing those
rows requires a separately reviewed maintenance operation. Invalid checkpoint
and general cancellation/failure cleanup remain outside this specific branch.
The active `agent-kernel-local` code/data/credentials have not been updated.

## Verification Ledger

- [x] Reproduce on pre-fix code: four new tests fail specifically because the
  persisted tool is `waiting_approval`, not `denied` (4 failed in 2.13 s).
- [x] Same four pass after repair (4 passed in 2.06 s).
- [x] Expanded 17-case regression covers explicit/native flows, fresh sessions,
  earlier result preservation, no invocation, duplicate/concurrent resume,
  rollback before commit, stale/absent/replaced owners, canceled Run fencing,
  mismatched relationships and already-terminal states. Requested/expired/canceled
  approvals still refuse execution without new terminal writes.
- [x] Focused approval/runtime/ownership/cancellation/auth suite: **140 passed**
  in 56.42 s, on the independent PostgreSQL test service.
- [x] Isolated Docker API/CLI rehearsal: exit 0, **14 scenario checks**; rejected
  tool `denied`, zero rejected effects, one approved effect, correct linked events,
  duplicate resume 409, and no active-stack changes.
- [x] Full Python suite on disposable PostgreSQL: **1183 passed, 35 skipped** in
  227.46 s; includes the subsequently added assertion that an injected rollback
  emits no committed-failure log. Skip boundaries are listed below.
- [x] Reviewed timeline golden amendment and two mutation regressions: require
  the denied tool state and the new terminal event, not just a failed Run.
  Combined timeline/rejection suite: **41 passed** in 47.82 s.
- [x] Mypy: **235 source files**; full-repository Ruff lint and changed-file format
  checks passed. Earlier unrelated whole-repository formatting issues stay out of scope.
- [x] Test database had zero remaining `test_kernel_%` schemas before teardown;
  `make test-db-down` removed only the disposable test service/network. Final
  read-only comparison confirms all 13 active service identities are unchanged.
- [x] Final documentation/harness unit checks: **95 passed**; changed-file
  pre-commit checks passed. Full-repository Ruff lint and mypy were rechecked.

Reproduction and regression:

```bash
make test-db-up
AGENT_KERNEL_TEST_POSTGRES_URL=postgresql+psycopg://agent_kernel:test-only@127.0.0.1:55432/agent_kernel_test .venv/bin/pytest -q tests/integration/test_approval_rejection_terminal.py
.venv/bin/python scripts/cf2_rehearsal.py
make test-db-down
```

These commands use the disposable test service and a randomly named CF2 project,
never the active runtime DB. The regression is part of normal pytest discovery;
the full Docker rehearsal remains opt-in. Models are offline fixtures and
embeddings are mock, not live quality or external side-effect evidence.

The first full-suite attempt reported **11 failed, 1170 passed, 35 skipped**:
all failures came from the unchanged rejection timeline golden (or tests which
expected only their intentional mutation to fail). Review confirmed that this
repair intentionally adds `tool_call_failed` before `run_failed`. Only that case
was amended, adding both the event and required `tool_statuses=["denied"]`.
The fixture/comparator were not weakened, and unrelated goldens were not regenerated.
The subsequent full run passed with the result above; the failed attempt is
retained as diagnostic history, not counted as acceptance.

The 35 skips were opt-in Docker-local checks (4), monitoring deployment (3),
full observability (7), promtool (3), backend drill (1), real Redis contract (12),
self-hosted HTTP deployment (1), and shared admission Redis checks (4). No
required PostgreSQL test was skipped. The separate CF2 Docker rehearsal uses
real Redis for its queue path, but does not replace the skipped Redis fault tests
or other deployment profiles. Active-runtime acceptance was deliberately not run.

Final private Docker evidence (after the golden amendment):
`.agent-kernel/agent-kernel-cf2-eddae55cbb783df8/`. `manifest.json` identifies
the exact source/image/config/request evidence and passed the credential scan.
All rehearsal containers, networks and volumes were removed; generated credentials
were removed. `cleanup.json` confirms all 13 active service identities, images,
start times and statuses matched. No active DB requests/backfills were made.
The earlier post-repair Docker rehearsal also passed at
`.agent-kernel/agent-kernel-cf2-d7d79d64cc4ce1db/`; it predates the golden amendment
and is not substituted for the final candidate evidence above.

## Learning Note

This continues the requested professional demonstration: correct status fields
alone are insufficient unless their transaction boundary is verified. The fault
test flushes the changes, uses an independent session to confirm they remain
invisible, throws before commit, then verifies rollback and successful retry.
This establishes the tested PostgreSQL transaction behavior, not exactly-once
delivery to arbitrary remote systems. Independent learner practice was not assessed.

## Pre-Commit Review

The maintainer subsequently authorized review, then commit/push and exact-candidate
CI tracking if no blocking issue remains. Active Docker deployment remains
explicitly excluded. Reviewer: Codex, the implementer; not an independent audit.

Source review found no blocking defect in the submitted scope:

- The Run-first lock matches approval/lease writers; finalization re-reads both
  child records and validates the live lease before committing terminal states.
- One commit covers the tool, Run and both events. Failure injection verifies
  visibility and rollback through another session, not only returned objects.
- Explicit/native rejection, duplicate/concurrent resume, ownership fencing,
  invalid relationships and timeline mutations have regression assertions.
- CF2 uses authenticated CLI/HTTP routes and real storage/queue/MCP components;
  only provider transport and embeddings are offline fixtures. Invocation evidence
  is persisted independently of approval status and checked before/after resume.
- Random owned Compose resources, internal networking, environment allowlisting,
  private evidence, credential removal and guarded cleanup preserve the active
  project. `resource/`, runtime data and credentials are excluded from Git.

Review verification passed: **1183 passed, 35 optional skips** in 225.77 s on the
disposable PostgreSQL service; **17** focused rejection cases and **95** document/
harness checks passed separately. Ruff, mypy (235 source files), changed-file
pre-commit and diff checks passed. Zero test schemas remained before teardown.
The first review rerun could not reach loopback PostgreSQL from the execution
sandbox (`Operation not permitted`); that attempt is not acceptance evidence.
The successful rerun used approved test-only network access, not relaxed assertions.

All **172 source-file hashes** from the final isolated Docker rehearsal still
match the submitted code, and all manifest evidence-file hashes verify. Its 14
scenario checks, zero rejected effects and cleanup evidence therefore apply to
this code candidate; the full Docker rehearsal was not repeated for prose edits.

Remote CI is pending at this pre-commit checkpoint. The CF2 Docker rehearsal is
opt-in and is not automatically run by the existing CI workflow. Existing CI
does run the new rejection and harness unit/regression tests. The earlier local
results above remain historical evidence, not a remote-CI claim.
