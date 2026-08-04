# Day 42: Live Approval Inbox

## Goal

Extend Workbench live API integration to the approval inbox.

## Scope

- Add same-origin Web routes for approval list, approve, and reject.
- Add live approval types and state.
- Render live approval inbox status without removing fixture-backed approval
  preview behavior.
- Update Playwright smoke coverage.
- Update Public Alpha docs and milestones.

## Tasks

- [x] Create Day 42 daily plan.
- [x] Add Web route handler for approval list.
- [x] Add Web route handlers for approve and reject.
- [x] Add live approval response types.
- [x] Load live approvals in the Workbench.
- [x] Render live approval status and error fallback.
- [x] Update smoke coverage.
- [x] Update Public Alpha guide and milestones.

## Acceptance

- [x] Workbench attempts to load live approvals through the Web app.
- [x] API unreachable state is visible without breaking fixture-backed approval
  interactions.
- [x] Live approval approve/reject proxy routes exist for the next mutation UI
  step.
- [x] Public Alpha docs record approval inbox live integration.

## Verification

- [x] `git diff --check`
- [x] `npm run lint`
- [x] `npm run test:e2e`

## Notes

- This day adds approve/reject proxy routes but keeps the existing visible
  approval buttons on fixture-backed local UI state.
- Full mutation wiring can happen after live list behavior is stable.
