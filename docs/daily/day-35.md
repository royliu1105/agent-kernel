# Day 35: Release Documentation and Examples

## Goal

Make Agent Kernel easier to evaluate, configure, contribute to, and discuss as
a v0.1 open-source project.

Day 35 should establish this documentation baseline:

```text
production config -> examples -> contribution guide -> security policy -> roadmap
```

## Scope

Day 35 should cover:

- Production configuration guide.
- Example workflows and fixture files.
- CONTRIBUTING guide.
- SECURITY policy.
- ROADMAP.
- Documentation index updates.
- Phase 6 milestone updates.
- Documentation syntax and diff checks.
- Existing Python and Web quality gates where practical.

Day 35 should not cover:

- v0.1 release notes.
- Final release checklist.
- Full Docker Compose startup verification.
- New runtime features.
- Public Alpha feature expansion.

## Tasks

- [x] Check current git status.
- [x] Read Phase 6 milestones and current docs.
- [x] Create Day 35 daily plan.
- [x] Add production configuration guide.
- [x] Add examples README and fixture files.
- [x] Add CONTRIBUTING guide.
- [x] Add SECURITY policy.
- [x] Add ROADMAP.
- [x] Update documentation indexes.
- [x] Update milestones.
- [x] Run docs/diff checks.
- [x] Run Python quality gates.
- [x] Run Web quality gates.

## Acceptance

- [x] Production configuration expectations are documented.
- [x] Examples explain at least one runnable local workflow.
- [x] Contribution workflow and quality gates are documented.
- [x] Security reporting and current security posture are documented.
- [x] Roadmap separates v0.1, Public Alpha, and later work.
- [x] Docs explain architecture, usage, tradeoffs, and next steps.
- [x] Quality gates pass.

## Verification

Run:

```bash
uv run ruff check .
uv run mypy .
uv run pytest
npm run lint
npm run build
npm run test:e2e
git diff --check
```

## Notes

- Keep release docs honest about fixture-backed Web UI and deferred production
  hardening.
- Do not claim a cloud-ready production deployment before Phase 6 final
  verification.
