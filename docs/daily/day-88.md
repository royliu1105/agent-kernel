# Day 88: v1.0 Release Checklist

Goal:

Convert the Day 87 scope freeze into a concrete v1.0 final release checklist.

Scope:

- Add a dedicated v1.0 release checklist.
- Separate required gates, waivable items, accepted limitations, deferred scope,
  publication steps, and post-release follow-up.
- Update docs index, daily index, milestones, and scope-freeze handoff.
- Do not mark v1.0 final readiness or create release notes.

Tasks:

- [x] Check current git status before editing.
- [x] Review Day 87 scope freeze.
- [x] Add dedicated v1.0 release checklist.
- [x] Include clean-machine rehearsal status and waiver rules.
- [x] Include release smoke, release eval, load/soak, Python, Web, migration,
  security, dependency, docs, and publication gates.
- [x] Include accepted limitations and deferred non-blocking scope.
- [x] Update docs index.
- [x] Update daily index and milestones.

Acceptance:

- [x] Day 88 produces a checklist that Day 90 can execute directly.
- [x] Checklist distinguishes required gates from accepted limitations.
- [x] Checklist does not claim v1.0 final readiness.
- [x] Checklist preserves the Day 87 scope freeze.
- [x] Remaining Day 89-90 work is clear.

Verification:

- [x] `uv run pytest tests/unit/test_docs_consistency.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `git diff --check`

Notes:

- The v0.1 release checklist remains historical. The new checklist is the v1.0
  release-candidate gate.
