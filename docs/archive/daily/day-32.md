# Day 32: Workbench Navigation and Operational Views

## Goal

Expand the Agent Workbench from a dashboard-only screen into a navigable
operator workspace.

Day 32 should establish this UI baseline:

```text
select workspace view -> inspect agents / knowledge / evals / settings
```

## Scope

Day 32 should cover:

- Client-side Workbench navigation.
- Agents view with runtime, model, queue, and capability summaries.
- Knowledge view with document ingestion status.
- Eval view with report detail and regression case summaries.
- Settings view with runtime configuration, safety posture, and API endpoint summary.
- Responsive styling for the expanded views.
- Phase 5 milestone updates.
- Web typecheck/build verification.

Day 32 should not cover:

- Route-per-page navigation.
- Live API-backed Web data fetching.
- Settings mutation.
- Authentication.
- Playwright smoke tests.
- Deployment changes.

## Tasks

- [x] Check current git status.
- [x] Read Phase 5 milestones and current Web dashboard.
- [x] Create Day 32 daily plan.
- [x] Add client-side Workbench navigation.
- [x] Add Agents view.
- [x] Add Knowledge view with ingestion status.
- [x] Add Eval reports view.
- [x] Add Settings view.
- [x] Update responsive styles.
- [x] Update docs and milestones.
- [x] Run web lint/typecheck.
- [x] Run web build.
- [x] Start local web dev server.

## Acceptance

- [x] User can switch between Workbench views.
- [x] User can inspect agent operational status.
- [x] User can inspect document ingestion status.
- [x] User can view eval report details.
- [x] User can inspect runtime settings and safety posture.
- [x] UI clearly labels fixture-backed local Web state.
- [x] Web build passes.

## Verification

Run:

```bash
npm run lint
npm run build
git diff --check
```

## Notes

- Keep Day 32 data fixture-backed and deterministic.
- Do not represent settings, approval, knowledge, or eval UI state as live backend mutation.
- Keep Playwright smoke tests for Day 33 so Phase 5 closes with browser-level verification.
