# CF1 Minimal Repair Verification

Date: **2026-11-14**. Status: **code review, local verification and candidate CI passed; deployment/pilot pending**.
The [follow-up ledger](../reference-follow-up-plan.md) owns CF1 acceptance.
This follows the [historical read-only review](2026-11-14-cf1-memory-boundary.md),
not a rewrite of its evidence. The maintainer authorized the minimal repair,
tests and documentation, then code review and two separate baseline/CF1 commits,
push and CI tracking. `resource/`, private configuration and runtime data are
excluded. Updating the active Docker environment, release, paid provider calls
and user admission remain outside this authorization.

## Scope and Progress

- [x] Freeze the bounded workspace-shared trust contract in the
  [memory context spec](../specs/memory-context-safety.md).
- [x] Separate fixed SYSTEM rules from untrusted USER JSON memory; verify the
  actual OpenAI adapter payload with mocked HTTP transport.
- [x] Bound write content/metadata, selection inputs and aggregate context.
  Validate API and repository writes; use one globally limited recall query.
- [x] Reject unsafe memory checkpoints before effects; retain no-memory legacy
  compatibility and unchanged safe snapshots after memory-row deletion.
- [x] Focused regression: 128 passed, covering memory, roles/workspaces, native
  execution, approvals and actual adapter continuation fixtures.
- [x] Post-review full Python regression: **1146 passed, 35 skipped in 218.33 s**.
- [x] Ruff, touched-file format checks, mypy (230 source files), diff whitespace
  and focused documentation/byte-boundary verification (102 passed).
- [x] Release evals: RAG 3/3 and 4/4, tool evals 2/2, bounded execution/approval/
  backoff/budget 71/71, persisted timeline scenarios 7/7.
- [x] Read-only check: API/Worker/Web/PostgreSQL container IDs and start times
  are identical to the pre-repair baseline; no active deployment was performed.
- [x] Zero remaining `test_%` schemas; task-created `agent-kernel-test` container
  and network removed without touching active runtime volumes.
- [x] Codex code review: repair the validation-error response finding below;
  no remaining blocking finding in the reviewed CF1 change. This is not an
  independent security audit or live-model safety acceptance.
- [x] Record candidate `5952ba7` and exact-revision remote CI: all four jobs passed.
- [ ] Maintainer disposition of residual risk for the intended deployment/pilot.
- [ ] Deploy the approved candidate to the intended environment and verify it there.

Deployment and pilot admission are not implicitly authorized by code review. CF2 and
PV1-PV6 have not started; CF3-CF8 remain deferred/conditional. Live injection/
quality evidence belongs to PV3, not these fixture tests.

## Reproduction and Verification Method

Initial new unit regressions: **16 failed, 1 passed** against the pre-repair code.
Integration regressions initially had six behavior failures and four fixture
failures: the checkpoint fixture attempted lease-protected repository access
without an execution lease. It was corrected to seed historical/corrupt records
directly in the disposable database, matching existing checkpoint tests. The
production lease protection was not relaxed; fixture failures are not evidence
of four production defects.

The first full regression run passed **1132 tests, 35 skipped** in 220.29 s.
Two exact structural/aggregate byte-boundary cases and a documentation contract
were added afterward; the final rerun passed **1135 tests, 35 skipped**. One
documentation assertion initially failed because
Markdown emphasis interrupted its literal phrase; wording was corrected, then
all 102 focused documentation/contract tests passed.

The 35 skips are explicit opt-ins: active Docker acceptance (4), monitoring
deployment (3), full observability/SMTP rehearsal (7), native promtool (3),
backup/restore drill (1), real Redis contracts (12), HTTP deployment (1), and
Redis-backed shared admission (4). None is counted as passing. All CF1 regressions
ran; no live provider, email delivery, browser or deployment acceptance is claimed.
The final documentation-only recheck passed **77 tests**.

Focused verification: **128 passed in 36.26 s**. The new assertions inspect
captured model requests, persisted call statuses, approval decisions, actual
downstream invocation counts and completion-event counts. Testing only the
model's textual claim of refusal would miss an already-executed side effect.

All database tests use `agent-kernel-test`, port 55432, tmpfs storage and randomly
named schemas with actual Alembic migrations. They never use the active
`agent-kernel-local` database or volumes. No active runtime build/start/stop,
migration, data cleanup, or credential change is part of this repair.
All 13 active runtime services remained running. API/Worker/Web/PostgreSQL IDs
and their `2026-11-14T06:42:25Z` start times matched the initial read-only check.
This is non-interference evidence, not a new business-data checksum or proof
that the running images already contain CF1.

Reproduce locally without starting a host runtime:

```bash
make test-db-up
export AGENT_KERNEL_TEST_POSTGRES_URL=postgresql+psycopg://agent_kernel:test-only@127.0.0.1:55432/agent_kernel_test
uv run pytest -q tests/unit/test_memory_context_contract.py tests/integration/test_memory_context_security.py
uv run pytest -q
make release-eval
uv run ruff check .
uv run mypy .
make test-db-down
```

The test database is disposable. Do not substitute the active runtime URL or
enable deployment/fault-test opt-ins against `agent-kernel-local`.

## Candidate Identity

The pre-review candidate was the dirty working tree based on
`d599fc2ab44c054af009aabb7cab298d4988f4eb`, not that commit or the published
v1.0.0 tag. Its source/config/test fingerprint was **306 files**, SHA-256
`a240c9f7eb2dcf86b0baae781a800cf3de5baf4747d49347c7295dd251609281`.
After the review fix below: **307 files**, SHA-256
`1978cc06877cad79ad2b476ce4536d834c23d5e09595d6d0ec49f24088d4cc17`.
Both use the historical review's source/config/test fingerprint method and exclude
documentation, secrets, runtime data and `resource/`. Existing PostgreSQL-only,
observability and Docker changes are retained as the separate baseline commit.
Baseline commit: `8f87473`; an exported staged snapshot passed **1085 tests,
35 skipped in 216.21 s** independently of CF1. Its pre-commit checks passed.
CF1 candidate: `5952ba75f2adeca101b938a9402292811ea56afc`, including that baseline.
Both commits were pushed normally to `origin/master`, without a tag or release.

## Exact-Candidate CI Evidence

[GitHub Actions run 43590573645](https://github.com/royliu1105/agent-kernel/actions/runs/43590573645)
completed successfully for `5952ba75f2adeca101b938a9402292811ea56afc`.
The `python`, `web`, `compose` and `observability` jobs all passed on 2026-11-14.

| Gate | Recorded result |
| --- | --- |
| Python migration smoke | 27 passed. |
| Python regression | 1165 passed, 15 opt-in deployment cases skipped; separate deployment jobs ran their profiles below. |
| Disposable PostgreSQL restore drill | 1 passed. |
| Ruff / mypy | Passed / 230 source files. |
| Release eval gates | RAG 3/3 and 4/4; tools 2/2; bounded execution 71/71; persisted timeline 7/7. |
| Web | Typecheck/build passed; Playwright 2 passed, 1 Docker-only browser case skipped in the managed-server job. |
| Compose deployment | HTTP smoke 1 passed; monitoring 3 passed; owned deployment cleanup succeeded. |
| Full observability | Native validators and 8 log/trace/local-SMTP E2E tests passed in 304.50 s; disposable cleanup succeeded. |
| Default Docker runtime | `make docker-up` on the isolated CI runner and 4 real runtime/Web proxy tests passed; stack teardown succeeded. |

This is exact-candidate fixture and disposable-deployment evidence, not a claim
about live provider safety, external mailbox delivery or pilot usefulness.
The CI Web proxy checks do not replace a new live browser user-path rehearsal.
Nonblocking Action Node-runtime deprecation and runner-image transition notices
remain maintenance items; they did not fail these jobs.

Locally, the test schema count was zero before removing only the temporary
`agent-kernel-test` service/network. The active API/Worker/Web/PostgreSQL IDs and
start times still matched the pre-review check. No active Docker rebuild, restart,
migration or data cleanup was performed. The post-CI documentation commit records
this candidate's results; it does not retroactively change the tested SHA.

## Pre-Commit Code Review

One P2 finding was reproduced and fixed: rejecting non-finite numbers or invalid
Unicode in memory payloads could make FastAPI's default validation response
fail serialization and return HTTP 500. Its default error details also echoed
private raw inputs, including oversized content. The API now returns JSON-safe
422 errors with only `loc`, `msg` and `type`, omitting raw `input` and `ctx`.
This applies consistently to request-validation errors, not just memory routes.

`tests/unit/test_api_validation.py` adds 11 regressions for content/metadata,
NaN, both infinities, lone surrogates, excessive size, malformed JSON and invalid
memory selection. They failed before the handler fix and passed afterward;
the focused validation/context suite passed **36 tests**. The full post-review
suite passed **1146 tests, 35 skipped**; all CF1 tests ran. Ruff and mypy passed.

The reviewed scope includes input admission, repository bounds, request roles,
legacy checkpoint rejection, approval/resume effects and cross-workspace tests.
No remaining blocking CF1 finding was identified within that scope. Prompt
placement is not a general prompt-injection defense; live quality, independent
review and the intended deployment remain separate evidence requirements.

## Demonstrated Tradeoffs

- Keep structured memory rather than keyword-filtering arbitrary text: harmless
  notes may discuss approvals, and a keyword filter cannot enforce authorization.
- Treat model intent as untrusted even after prompt repair: deny must mean zero
  calls, undecided/rejected approval must mean zero calls, approved resume must
  call the original tool once. The positive approved case proves the test did
  not merely disable the entire tool path.
- Reject old unsafe context rather than silently changing approved history.
  Safe snapshots remain reproducible, but memory deletion is not retroactive
  erasure. Restarting a task requires review of earlier effects.
- Fail rather than truncate an oversized memory set: callers must deliberately
  narrow selection, avoiding undocumented changes to included evidence.

The maintainer requested a professional demonstration. These are explanations
and measured tests, not independent learner-performance or mastery evidence.
