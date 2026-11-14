# PV1 GitHub CI Candidate Design Review

Date: 2026-11-15. Scope: PV1 contract/status documents and offline document tests.
This record concerns design consistency, not tool implementation or live acceptance.

## Authority

The maintainer authorized review, scoped commit/push and tracking CI after the
review passes. Submission CI management queries do not exercise the proposed
`github_ci_run_status` candidate and are not pilot evidence. No candidate API
test, credential use for that tool, active Docker update or paid model call is
authorized. No business code, connector, runtime binding or observer is added.

## Findings and Disposition

- P2: The draft said any journal write failure would stop the request, including
  completion writes after dispatch. That cannot undo a request already sent.
  The contract now fails closed before dispatch and classifies post-dispatch
  recording failure or crash ambiguity as incomplete/unknown, with no replay.
- P2: One matrix row combined pre-approval waiting with rejected terminal state.
  It now separates waiting Run/tool state from failed/denied state after rejected
  resume, consistent with the existing runtime contract.
- Evidence precision: Response headers are not proof of a fully consumed and
  validated body. The design now requires correlation with adapter completion
  without placing bodies in the independent journal.
- Status consistency: Updated the latest submission authorization and removed
  stale claims that content selection/redaction still needs acceptance. Provider
  transmission, reviewer roles, tool access and full PV1 sign-off remain pending.

The static review checked the adapter's primitive path/query schema validation,
required constant query argument, full untrusted JSON return, serialized bound,
and the guarded HTTP transport's origin/path, response-size, no-redirect and
zero-retry behavior. It does not establish anonymous GitHub access, payload size,
permissions or observability in a deployed environment. A client dispatch journal
is explicitly not GitHub server-side access logs or global exactly-once evidence.
Acceptance of that limited standard remains an explicit maintainer decision.

## Frozen Content and Remaining Gates

The content baseline remains `20b8dc8a41bc3ada5386566fcc346392fd599324`.
The manifest and its 12 corpus / three question-answer artifacts must remain
byte-identical. Preparation labels remain historical; later content acceptance is
recorded in the contract, without changing `not_run` results or their gold answers.
Account ownership/Beijing region are maintainer attestations, not authenticated
verification. The customer-assignment candidate remains withdrawn.

PV1 remains in progress; PV2-PV6 have not started. The observer is not implemented,
the response is not field-projected, and exact run IDs, payload permission,
access, limits, retention, participants and final contract admission remain open.
Tests check document contracts/integrity only; they are not live behavior evals.

## Pre-Submission Verification

A targeted document regression failed before the wording correction, as expected.
After correction, no unresolved blocking finding remains in this design/document
scope. Final local checks:

| Check | Observed result |
| --- | --- |
| Frozen Git objects vs working bytes | All 16 files identical: manifest, 12 summaries, three question/answer artifacts |
| Materials and document consistency | 90 passed |
| `ruff check .` | Passed |
| `mypy .` | Passed, 238 source files |
| Changed-file pre-commit and `git diff --check` | Passed |

Only short-lived static/offline commands ran locally; the test command removed
provider credentials and the PostgreSQL test URL. No current Docker or database
was accessed. Full runtime/backend verification is left to the existing isolated
CI jobs, not claimed as a local rerun. This is a pre-submission evidence checkpoint:
remote CI must be checked on the exact submitted SHA, with its final run link
reported separately rather than inferred from previous green commits. No new
tag or release is planned.
