# Day 31: Run Timeline and Approval Inbox Interactions

## Goal

Turn the Day 30 dashboard previews into interactive Workbench views for run
inspection, tool-call detail, and approval decisions.

Day 31 should establish this UI baseline:

```text
select run -> inspect timeline -> inspect tool call -> approve/reject locally
```

## Scope

Day 31 should cover:

- Client-side run selection.
- Run-specific timeline data.
- Tool call detail panel.
- Approval inbox with local approve/reject decisions.
- Approval decision history.
- Clear non-live API labeling for local UI state.
- Responsive styling for the new interactive controls.
- Web typecheck/build verification.

Day 31 should not cover:

- Live API mutation for approvals.
- Authentication.
- Route-per-page navigation.
- Playwright smoke tests.
- Knowledge base detail page.
- Eval report detail page.

## Tasks

- [x] Check current git status.
- [x] Read Phase 5 milestones and current Web dashboard.
- [x] Create Day 31 daily plan.
- [x] Add client-side run selection.
- [x] Add run-specific timeline data.
- [x] Add tool call detail panel.
- [x] Add approval inbox decisions.
- [x] Add decision history.
- [x] Update responsive styles.
- [x] Update docs and milestones.
- [x] Run web lint/typecheck.
- [x] Run web build.
- [x] Start local web dev server.

## Acceptance

- [x] User can switch selected runs.
- [x] User can inspect a selected run timeline.
- [x] User can inspect selected tool call details.
- [x] User can approve or reject approval items locally.
- [x] UI clearly avoids claiming live API mutation.
- [x] Web build passes.

## Verification

Run:

```bash
npm run lint
npm run build
git diff --check
```

## Notes

- Keep approval actions local to the browser for Day 31.
- Do not represent local approval decisions as persisted backend decisions.
- Preserve the operational dashboard density from Day 30.
