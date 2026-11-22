# Day 43: Live Approval Mutation UI

## Goal

Wire the Workbench live approval list to the live approve/reject proxy routes
added on Day 42.

## Scope

- Add live approval approve/reject UI actions.
- Keep fixture-backed local approval preview intact.
- Add mutation loading and error status.
- Add Playwright coverage with mocked live approval API responses.
- Update Public Alpha docs and milestones.

## Tasks

- [x] Create Day 43 daily plan.
- [x] Add live approval mutation state.
- [x] Wire live approve action to the same-origin Web proxy.
- [x] Wire live reject action to the same-origin Web proxy.
- [x] Render live approval decision results.
- [x] Add smoke coverage for live approval mutation UI.
- [x] Update Public Alpha guide and milestones.

## Acceptance

- [x] Requested live approvals expose approve/reject controls.
- [x] Approve/reject calls the Web proxy and updates the visible live approval.
- [x] Mutation errors are visible and non-blocking.
- [x] Fixture-backed local approval interactions still work.
- [x] Public Alpha docs record live approval mutation wiring.

## Verification

- [x] `git diff --check`
- [x] `npm run lint`
- [x] `npm run test:e2e`

## Notes

- This day does not add backend approval capabilities; it wires existing API
  routes into the Workbench.
