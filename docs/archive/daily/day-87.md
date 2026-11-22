# Day 87: Known Limitations Review and Scope Freeze

Goal:

Review all remaining v1.0 release candidate limitations, decide which ones
block release readiness, which ones are acceptable documented limitations, and
which ones are explicitly deferred beyond v1.0.

Scope:

- Create the v1.0 scope freeze document.
- Classify remaining limitations as blockers, accepted limitations, deferred
  enhancements, or final verification items.
- Update security and planning docs to point at the scope freeze.
- Update daily index and milestone tracking.
- Do not add new runtime features unless a release-blocking mismatch is found.

Tasks:

- [x] Check current git status before editing.
- [x] Review known limitation sources across v1.0 RC docs.
- [x] Create v1.0 scope freeze document.
- [x] Classify fresh Docker restart, release checklist, release notes, and final
  verification as remaining release work.
- [x] Classify self-hosted security limitations as acceptable only when
  documented and operator-controlled.
- [x] Classify SaaS, marketplace, SSO, visual builder, and advanced eval/retrieval
  surfaces as beyond v1.0.
- [x] Update security hardening docs with the Day 87 decision.
- [x] Update docs index, daily index, and milestones.

Acceptance:

- [x] v1.0 scope is frozen around a self-hosted production runtime.
- [x] Remaining release blockers are explicit.
- [x] Accepted limitations are explicit and operator-facing.
- [x] Deferred features are not allowed to block v1.0.
- [x] Day 88 can build the final release checklist from the frozen scope.

Verification:

- [x] `uv run pytest tests/unit/test_docs_consistency.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `git diff --check`

Notes:

- Day 87 is intentionally a scope-control day. The release risk here is
  uncontrolled expansion, not missing another feature sprint.
