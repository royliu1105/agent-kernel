# PV1 and Pilot Provider Review

Date: 2026-11-15. Status: **Review, final local verification and implementation
candidate remote CI passed; live providers and pilot admission remain unaccepted**.

## Scope and Authority

The maintainer authorized review of the PV1 draft and minimal DeepSeek/Alibaba
Embedding adaptation, then commit/push and exact-candidate CI tracking once
review passes. This does not authorize paid requests, current Docker updates,
credential copying, pilot admission, a tag or release. Budget remains USD 10;
authorized spending remains USD 0. `resource/` and private runtime data stay
excluded from the commit and from build contexts.

The preparation baseline is `767e35af19d52d0596478af13d010ea2ba0ab45b`.
The [compatibility contract](../specs/pilot-provider-compatibility.md) retains
implementation evidence; the [pilot ledger](../real-scenario-pilot-plan.md) alone
owns PV1-PV6 acceptance. Prior baseline CI does not verify the new implementation;
its exact-candidate result is recorded below.

## Review Findings and Disposition

The review identified a **P2 response-validation defect** in the shared embedding
parser used by the new DashScope adapter: non-finite numeric values were accepted
and overflowing integers escaped as `OverflowError`. A second-batch non-finite
response reached PostgreSQL as an invalid JSON/vector value instead of the
provider's controlled failure path. That contradicts the batch-validation contract
and can leave indexing state requiring recovery. Eight unit cases and one actual
PostgreSQL case reproduced the defect before repair. The shared parser now rejects
both classes as `OpenAIEmbeddingError` before returning any vectors, allowing the
existing indexing failure path to preserve the old index and restore its status.
Post-repair verification below closes this finding for the exercised contract;
it is not a claim that a live provider has passed acceptance. No unresolved
blocking code finding remains in the reviewed scope.

The review also covered shared Responses serialization/error classification, dedicated provider
credentials and endpoints, API/Worker routing, native checkpoint replay and
approval effects, embedding batch failure and persistence, readiness, Compose
defaults and consistency of the PV1 authorization/acceptance records.

Two review follow-ups were needed before submission:

- Native continuation fixtures used a populated summary even for DeepSeek.
  Its [Responses contract](https://api-docs.deepseek.com/guides/responses_api/)
  does not generate a reasoning summary. The DeepSeek fixture now uses an empty
  summary with plaintext content across two approval/resume rounds. The strict
  validator is not relaxed; live response shape remains unverified.
- Readiness override documentation omitted Docker environment wiring. The
  [profile guide](../provider-compatibility.md#readiness-and-verification) now
  explains that the future isolated API override must explicitly supply the
  settings; a host export/root `.env` alone is insufficient. No deployment
  profile is activated by this correction.

Additional regressions assert that both providers reject HTTP 301/302/303/307/308
without a second request, so credentials cannot follow a redirect. Authorization
history now distinguishes the earlier implementation-only request from the
current commit/push request. The only runtime repair is the shared embedding
finite-value validation; no new feature or dependency was added by review.

## Review Verification

| Check | Observed result |
| --- | --- |
| Red regression before finite-value repair | 8 unit cases and 1 PostgreSQL second-batch case failed as expected |
| Post-repair provider/embedding/bootstrap/native continuation/readiness suites | 93 passed; both providers reject invalid numeric values; previous pgvector index and indexed status preserved after failed second batch |
| Final provider/documentation/local-default suites | 141 passed |
| Final full offline suite after the repair | 1251 passed, 35 opt-in skips in 227.20 seconds |
| `make release-eval` after repair | RAG 3/3 and 4/4; tool 2/2; execution/backoff/native/budget 72 passed; timeline 7/7 |
| `ruff check .`, `mypy .`, changed-file pre-commit hooks | Passed; mypy checked 237 source files |
| Base Compose `config --quiet`, `git diff --check` | Passed; config validation did not start services |
| Disposable DB cleanup | Zero `test_kernel_%` schemas remained; `make test-db-down` removed only the test project |

A full run begun before the finite-value repair passed 1242 tests with 35 opt-in
skips; it is not final-tree coverage. The final rerun above supersedes it.
The skips are opt-in Docker-local, monitoring/full-observability, promtool,
backup/restore, real Redis/shared-admission and self-hosted deployment gates;
they are not counted as local passes. Remote CI exercised its configured
disposable services separately, as recorded below.

Only `agent-kernel-test` on loopback port 55432 is used for local database tests.
Provider responses and credentials are synthetic. The active local runtime is
not rebuilt, restarted, migrated, seeded or used as a test target.

## Commit and Remote Verification

Reviewed implementation: `384416ce2f80538b4f3bffaf3806883deaf6d7fd`,
`feat(providers): add reviewed DeepSeek and DashScope pilot compatibility`.
It was pushed to `origin/master` with authorization.
[CI run 43622497986](https://github.com/royliu1105/agent-kernel/actions/runs/43622497986)
reports that exact `headSha`, `completed` and `success`; all four jobs passed.

| Remote check | Observed result |
| --- | --- |
| Python | Migration smoke 27 passed; Ruff passed; mypy checked 237 files; main suite 1270 passed, 15 opt-in skips; separate restore drill 1 passed; release eval gates passed, including 72 execution/continuation tests |
| Web | Typecheck/build passed; Playwright 2 passed, 1 explicit Docker-targeted case skipped in this job |
| Compose | Fresh isolated deployment built; HTTP rehearsal 1 passed; monitoring rehearsal 3 passed; cleanup passed |
| Observability | Full logs/trace/local SMTP rehearsal 8 passed; default Docker startup and runtime/Web proxy 4 passed; cleanup passed |

The main Python skips are Docker-local, monitoring/full-observability and
self-hosted deployment tests exercised by their dedicated jobs. The standalone
Web job's skipped Docker-targeted case is not silently counted as a browser pass;
the separate default Docker job verifies its configured runtime/proxy contract.
Existing Node-action deprecation and runner-image migration notices are warnings,
not test failures; no unrelated workflow upgrade is included in this batch.

Before submission, the staged paths and diff were reviewed: no `resource/`,
private runtime/config/data paths or real credentials were included. All provider
tests use synthetic values. This documentation-only follow-up records the already
completed implementation CI, not a claim about any future commit. No tag/release
was created, no actual provider was called, and no current local Docker service
or data was updated. The isolated local test database was removed after use.

## Remaining Gates

- The saved `deepseek-chat` identifier, account balance/access, returned model
  identity and actual Responses continuation remain live-unverified. Do not
  remap the model or infer support from fixtures. A later explicitly authorized
  smoke must resolve this before pilot admission.
- Alibaba region/account entitlement, real vector/semantic behavior and billing
  remain unverified. Existing 1536-dimensional HNSW indexing is not performance
  evidence for the 1024-dimensional pilot profile.
- PV1 corpus/config/provenance, transmission permission, budget allocation,
  participants, read-only target, Web-auth scope and risk sign-off remain open.
  PV2-PV6 have not started; CF1/CF2 are not closed by this review.
- The active Docker environment remains unchanged. Offline/remote disposable
  verification does not mean these changes are deployed locally.
