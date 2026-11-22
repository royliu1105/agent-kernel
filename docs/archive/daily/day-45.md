# Day 45: Live Retrieval Search Flow

## Goal

Extend the Workbench Knowledge view from live knowledge-base listing to live
retrieval search with cited chunk results.

## Scope

- Add same-origin Web route for knowledge-base retrieval.
- Add live retrieval response types.
- Add Knowledge view search form for knowledge base ID and query.
- Render raw retrieval results, scores, and citations.
- Keep fixture-backed ingestion preview intact.
- Update Playwright smoke coverage.
- Update Public Alpha docs and milestones.

## Tasks

- [x] Create Day 45 daily plan.
- [x] Add Web route handler for retrieval search.
- [x] Add live retrieval response types.
- [x] Add retrieval form and state to the Workbench.
- [x] Render cited retrieval results and empty/error states.
- [x] Update smoke coverage.
- [x] Update Public Alpha guide and milestones.

## Acceptance

- [x] Workbench can call retrieval through the Web app.
- [x] Users can paste or select a live knowledge base ID and submit a query.
- [x] Results show raw chunk content, score, document title, chunk index, and
  source URI.
- [x] Unreachable retrieval API state is visible without breaking
  fixture-backed knowledge views.

## Verification

- [x] `git diff --check`
- [x] `npm run lint`
- [x] `npm run test:e2e`

## Notes

- Day 45 does not implement final answer synthesis.
- Day 45 does not add real embeddings, pgvector-native indexes, or persisted
  retrieval sessions.
