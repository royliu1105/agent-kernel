# Day 30: Agent Workbench Shell and Dashboard

## Goal

Start Phase 5 by turning the placeholder web page into a usable Agent Workbench
dashboard foundation.

Day 30 should establish this UI baseline:

```text
workbench shell -> dashboard -> run visibility preview -> approval/eval/kb previews
```

## Scope

Day 30 should cover:

- Workbench layout shell.
- Navigation surface for Phase 5 areas.
- Dashboard metrics.
- Run queue preview.
- Run timeline preview.
- Approval inbox preview.
- Knowledge base status preview.
- Eval report preview.
- Settings/status preview.
- Typed Web API client foundation.
- Responsive CSS.
- Web typecheck/build verification.

Day 30 should not cover:

- Live API integration.
- Mutating approval actions.
- Real authentication UI.
- Full route-per-page navigation.
- Playwright smoke tests.
- Web deployment.

## Tasks

- [x] Check current git status.
- [x] Read Phase 5 plan and current web app.
- [x] Create Day 30 daily plan.
- [x] Add typed Web API client foundation.
- [x] Replace placeholder page with Workbench dashboard.
- [x] Add run, approval, knowledge base, eval, and settings preview sections.
- [x] Add responsive operational UI styling.
- [x] Update docs and milestones.
- [x] Run web lint/typecheck.
- [x] Run web build.
- [x] Start local web dev server.

## Acceptance

- [x] Web app opens to a useful Agent Workbench dashboard.
- [x] User can inspect a run timeline preview.
- [x] User can see pending approvals preview.
- [x] User can see knowledge base ingestion status preview.
- [x] User can see eval report preview.
- [x] Web build passes.
- [x] Day 30 does not claim live API integration or real approval mutations.

## Verification

Run:

```bash
npm run lint
npm run build
git diff --check
```

## Notes

- Keep the UI operational and scan-friendly rather than marketing-oriented.
- Use static fixture data for Day 30.
- Treat `src/lib/api.ts` as the future seam for replacing fixtures with API calls.

## Completion Notes

- Added typed Web API client foundation.
- Replaced placeholder page with an Agent Workbench dashboard.
- Added metrics, execution queue, run timeline, approval inbox, knowledge base,
  eval report, and runtime settings preview sections.
- Added responsive operational UI styling.
- Updated daily index and Phase 5 milestones.
- Kept live API integration, real approval mutations, full route navigation,
  authentication UI, and Playwright smoke tests deferred.

Verification passed:

- `npm run lint`
- `npm run build`
- `npm --workspace apps/web run dev`
- `git diff --check`
