# Day 89: v1.0 Release Notes

Goal:

Create the v1.0 release notes draft from the frozen v1.0 scope and release
checklist.

Scope:

- Add `docs/releases/v1.0.0.md`.
- List completed v1.0 capabilities and stable public surfaces.
- List accepted limitations and deferred non-blocking scope.
- Include verification commands, upgrade notes, dependency review expectations,
  and security posture.
- Update the v1.0 release checklist, docs index, daily index, and milestones.
- Do not tag, publish, or claim Day 90 final verification.

Tasks:

- [x] Check current git status before editing.
- [x] Review existing release-note style.
- [x] Review v1.0 scope freeze and release checklist.
- [x] Add v1.0 release notes draft.
- [x] Include completed capabilities.
- [x] Include stable public surfaces.
- [x] Include accepted limitations and deferred scope.
- [x] Include verification, upgrade, dependency, and security sections.
- [x] Update v1.0 release checklist release-note items.
- [x] Update docs index, daily index, and milestones.

Acceptance:

- [x] v1.0 release notes exist.
- [x] Release notes do not claim v1.0 is published.
- [x] Release notes match the Day 87 scope freeze.
- [x] Release notes point to Day 90 for final verification results.
- [x] Day 90 can update verification results without rewriting the release
  story.

Verification:

- [x] `uv run pytest tests/unit/test_docs_consistency.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `git diff --check`

Notes:

- Day 89 prepares the release notes. Day 90 decides whether the notes can be
  used for the actual GitHub Release.
