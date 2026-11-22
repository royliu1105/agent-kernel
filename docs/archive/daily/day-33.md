# Day 33: Playwright Smoke Tests and Phase 5 Verification

## Goal

Close Phase 5 by adding browser-level smoke tests for the Agent Workbench.

Day 33 should establish this quality gate:

```text
build Web -> launch browser -> navigate Workbench -> verify critical operator flows
```

## Scope

Day 33 should cover:

- Playwright dependency and Web test script.
- Playwright configuration for the Web workspace.
- Smoke tests for Workbench navigation.
- Smoke tests for run timeline and tool-call inspection.
- Smoke tests for local approval decisions.
- Smoke tests for knowledge ingestion and eval report views.
- CI integration for Web smoke tests.
- Phase 5 milestone updates.

Day 33 should not cover:

- Full visual regression testing.
- Cross-browser matrix.
- Authenticated Web flows.
- Live API-backed Web data fetching.
- Route-per-page navigation.
- Phase 5 summary documentation.

## Tasks

- [x] Check current git status.
- [x] Read Phase 5 milestones and Web package setup.
- [x] Create Day 33 daily plan.
- [x] Add Playwright dependency and scripts.
- [x] Add Playwright config.
- [x] Add Workbench smoke tests.
- [x] Add CI smoke test step.
- [x] Update docs and milestones.
- [x] Run web lint/typecheck.
- [x] Run web build.
- [x] Run Playwright smoke tests.

## Acceptance

- [x] `npm run test:e2e` launches the Web app and runs smoke tests.
- [x] Smoke tests verify Workbench view navigation.
- [x] Smoke tests verify run timeline and tool-call inspection.
- [x] Smoke tests verify local approval decision interaction.
- [x] Smoke tests verify knowledge ingestion status.
- [x] Smoke tests verify eval report details.
- [x] CI runs Web smoke tests.
- [x] Web build passes.

## Verification

Run:

```bash
npm run lint
npm run build
npm run test:e2e
git diff --check
```

## Notes

- Keep the initial Playwright gate small and deterministic.
- Use Chromium only for Day 33 to avoid turning Phase 5 closure into a browser matrix project.
- Keep screenshot and visual regression testing for a later enhancement.
