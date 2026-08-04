# Day 41: Live Run Lookup and Timeline

## Goal

Extend the Public Alpha live Web API integration from health status to real run
inspection.

## Scope

- Add same-origin Web proxies for run detail and run events.
- Add a Workbench live run lookup panel.
- Preserve existing fixture-backed run list and product preview.
- Update Playwright smoke coverage.
- Update Public Alpha docs and milestones.

## Tasks

- [x] Create Day 41 daily plan.
- [x] Add Web route handler for run detail.
- [x] Add Web route handler for run events.
- [x] Add API response types for live run lookup.
- [x] Add Workbench run lookup form and result state.
- [x] Render live run summary and timeline events.
- [x] Update Playwright smoke coverage.
- [x] Update Public Alpha guide and milestones.

## Acceptance

- [x] Operator can enter a run ID in the Runs view.
- [x] Workbench fetches live run detail and events through same-origin Web routes.
- [x] Missing or invalid run IDs show a clear non-blocking error.
- [x] Existing fixture-backed run preview remains usable.
- [x] Public Alpha docs record run detail and timeline live integration.

## Verification

- [x] `git diff --check`
- [x] `npm run lint`
- [x] `npm run test:e2e`

## Notes

- This day does not add a backend list-runs endpoint.
- The live lookup is intentionally explicit until the backend supports a
  first-class runs list API.
