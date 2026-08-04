# Day 44: Live Knowledge Base List

## Goal

Extend Workbench live API integration to the knowledge base list.

## Scope

- Add same-origin Web route for knowledge base list.
- Add live knowledge base response types and state.
- Render live knowledge base status in the Knowledge view.
- Keep fixture-backed document ingestion preview intact.
- Update Playwright smoke coverage.
- Update Public Alpha docs and milestones.

## Tasks

- [x] Create Day 44 daily plan.
- [x] Add Web route handler for knowledge base list.
- [x] Add live knowledge base response types.
- [x] Load live knowledge bases in the Workbench.
- [x] Render live knowledge base list and error fallback.
- [x] Update smoke coverage.
- [x] Update Public Alpha guide and milestones.

## Acceptance

- [x] Workbench attempts to load live knowledge bases through the Web app.
- [x] API unreachable state is visible without breaking fixture-backed knowledge
  views.
- [x] Live knowledge base data is visible when the API returns results.
- [x] Public Alpha docs record knowledge base live list integration.

## Verification

- [x] `git diff --check`
- [x] `npm run lint`
- [x] `npm run test:e2e`

## Notes

- This day does not implement live retrieval search.
- Retrieval search is reserved for Day 45.
