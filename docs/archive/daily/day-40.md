# Day 40: Workbench Live API Health

## Goal

Implement the first Public Alpha live Web API integration path by showing real
Agent Kernel API health in the Workbench.

## Scope

- Add a same-origin Web health proxy for the Agent Kernel API.
- Render live API health in the Workbench topbar.
- Preserve fixture-backed Workbench preview data for other views.
- Update Playwright smoke coverage.
- Update Public Alpha documentation and milestones.

## Tasks

- [x] Create Day 40 daily plan.
- [x] Add Web route handler for API health.
- [x] Add runtime health type and client UI state.
- [x] Render checking, reachable, and unreachable health states.
- [x] Update CSS for runtime status variants.
- [x] Update Playwright smoke assertion.
- [x] Update Public Alpha guide and milestones.

## Acceptance

- [x] Workbench topbar attempts a real health check through the Web app.
- [x] API unreachable state is visible without breaking fixture-backed views.
- [x] Playwright smoke test accepts live health states.
- [x] Public Alpha docs record the first live Web API integration.

## Verification

- [x] `git diff --check`
- [x] `npm run lint`
- [x] `npm run test:e2e`

## Notes

- This day intentionally avoids enabling browser-to-API CORS.
- The Web app uses a same-origin route handler as the first integration seam.
- Playwright now defaults to port `3100` to avoid reusing the Docker Compose Web
  service on port `3000` during local tests.
