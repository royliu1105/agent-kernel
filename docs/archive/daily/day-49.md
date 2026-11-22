# Day 49: Web Polish and First-User UX Pass

## Goal

Make the Public Alpha Workbench clearer for early users by distinguishing live
API paths from preview data and making live API failures more actionable.

## Scope

- Update Workbench view status copy to match current Public Alpha reality.
- Add a Workbench data-scope banner.
- Improve live API error UI with next-step guidance.
- Clarify approval preview copy.
- Add smoke coverage for the data-scope banner.
- Update Public Alpha docs and milestone status.

## Tasks

- [x] Create Day 49 daily plan.
- [x] Update topbar status labels.
- [x] Add Public Alpha data-scope banner.
- [x] Add live API error helper UI.
- [x] Clarify live approvals versus preview approvals.
- [x] Add responsive CSS for the scope banner and error helper.
- [x] Update Playwright smoke coverage.
- [x] Update Public Alpha docs and milestones.

## Acceptance

- [x] Workbench clearly states which paths are live API-backed.
- [x] Workbench clearly states which areas are preview data.
- [x] Live API errors include next-step guidance.
- [x] Narrow layouts do not squeeze the scope banner or API URL.
- [x] Playwright smoke test covers the scope banner.

## Verification

- [x] `git diff --check`
- [x] `npm run lint`
- [x] `npm run test:e2e`

## Notes

- Day 49 does not replace all fixture-backed Workbench views.
- Day 49 does not add new backend list endpoints, auth/RBAC, durable execution,
  provider-native function calling, real embeddings, or persisted evals.
