# Day 82: Full Release Smoke Test Matrix

Goal:

Define and implement the v1.0 release candidate smoke test matrix for the
product's critical user-facing and operator-facing paths.

Scope:

- Add a maintainer-facing release smoke command.
- Cover API health, CLI, worker, run lifecycle, approvals, tool execution, RAG,
  memory, eval API, Web lint/build, Docker Compose config, and release evals.
- Document the smoke matrix, command ownership, and boundaries.
- Update quality docs, docs index, daily index, and milestone tracking.
- Do not add load/soak tests, clean-machine rehearsal, or live provider tests.

Tasks:

- [x] Check current git status before editing.
- [x] Review existing critical-path tests.
- [x] Add `make release-smoke`.
- [x] Keep `release-smoke` separate from the normal `verify` target.
- [x] Document the release smoke matrix.
- [x] Update quality strategy with release gate commands.
- [x] Update docs index and daily index.
- [x] Update v1.0 RC milestone tracking.

Acceptance:

- [x] Release smoke can be run with one command.
- [x] Release smoke includes release eval gates.
- [x] Release smoke includes API, worker, approval, tool, RAG, memory, eval, Web,
  and Docker configuration coverage.
- [x] Release smoke remains deterministic and credential-free.
- [x] Day 82 does not introduce load/soak or clean-machine scope.

Verification:

- [x] `make release-smoke`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `git diff --check`

Notes:

- `make release-smoke` is a release candidate confidence command. It is not a
  substitute for Day 83 load/soak testing or Day 84-85 clean-machine rehearsal.
