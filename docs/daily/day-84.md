# Day 84: Clean-Machine Release Rehearsal Plan

Goal:

Define the v1.0 release candidate clean-machine rehearsal plan so Day 85 can
execute it, record failures, and fix release-blocking setup gaps.

Scope:

- Add a clean-machine rehearsal runbook.
- Define environment assumptions, clone/setup steps, verification gates,
  Docker checks, evidence capture, and failure handling.
- Link the runbook from quality and quickstart docs.
- Update docs index, daily index, and milestone tracking.
- Do not claim the clean-machine rehearsal has passed.
- Do not perform destructive local cleanup or delete existing development
  state.

Tasks:

- [x] Check current git status before editing.
- [x] Review existing quickstart, troubleshooting, release, and quality docs.
- [x] Add clean-machine rehearsal runbook.
- [x] Document required local tools and version checks.
- [x] Document SQLite, Docker Compose, Web, release gate, and evidence steps.
- [x] Document failure classification and Day 85 handoff rules.
- [x] Update quickstart and quality strategy links.
- [x] Update docs index, daily index, and milestones.

Acceptance:

- [x] A maintainer can follow one document for clean-machine rehearsal.
- [x] The runbook includes exact commands and expected outcomes.
- [x] The runbook separates required release blockers from optional checks.
- [x] The runbook explains how to record failures without hiding risk.
- [x] Milestones mark the Day 84 plan as complete but keep rehearsal pass
  acceptance open for Day 85.

Verification:

- [x] `git diff --check`

Notes:

- Day 84 is planning only. Day 85 owns executing the rehearsal and applying
  fixes from real clean-machine evidence.
