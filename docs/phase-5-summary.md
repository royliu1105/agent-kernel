# Phase 5 Summary: Agent Workbench Web UI

## Status

Phase 5 is complete as a production-grade Web UI foundation:

```text
Day 30-33: Web UI
```

Phase 5 delivered the first Agent Workbench product surface, including an
operator dashboard, navigable runtime views, run timeline inspection, tool-call
detail, approval inbox interactions, knowledge ingestion visibility, eval report
visibility, read-only settings, a typed API client, and Playwright smoke tests.

## What Users Can Do Now

Users can open a browser-based Agent Workbench and inspect the operational shape
of the Agent Kernel runtime.

Current user-facing shape:

```text
Workbench shell:
Dashboard -> Agents -> Runs -> Approvals -> Knowledge -> Evals -> Settings

Run inspection:
select run -> inspect timeline -> inspect tool call -> inspect trace metadata

Human review:
approval inbox -> approve/reject locally -> decision history

RAG operations:
knowledge base -> documents -> ingestion progress -> index status

Quality operations:
eval report -> behavior cases -> pass/fail detail
```

This makes the project feel like an operator console rather than a simple chat
demo. Chat remains a future input mode, but the primary product shape is an
Agent operations workbench.

## Completed Capabilities

- Next.js Web workspace.
- Agent Workbench shell.
- Sidebar navigation.
- Dashboard metrics.
- Agent registry view.
- Agent operational status cards.
- Run execution queue.
- Selectable run rows.
- Run-specific timeline data.
- Trace ID visibility.
- Tool-call detail panel.
- Tool-call status and risk badges.
- Approval inbox.
- Local approve/reject interactions.
- Local decision history.
- Knowledge base view.
- Document ingestion status view.
- Ingestion progress indicators.
- Eval report view.
- Eval behavior case details.
- Read-only runtime settings view.
- Safety posture settings view.
- Observability settings view.
- Typed Web API client foundation.
- Responsive Workbench styling.
- Playwright configuration.
- Browser smoke tests for core Workbench flows.
- CI smoke test integration.

## Web Surface

Available Workbench views:

```text
Dashboard  - runtime metrics and high-level operational cards
Agents     - agent status, model/provider, queue, tools, memory profile
Runs       - execution queue, timeline, tool-call detail
Approvals  - pending approvals, local approve/reject, decision history
Knowledge  - knowledge bases and document ingestion status
Evals      - eval reports and behavior case details
Settings   - read-only runtime, safety, and observability configuration
```

## Test Coverage

Phase 5 added Web coverage for:

- TypeScript Web typecheck.
- Next.js production build.
- Playwright smoke test startup through a managed Web server.
- Workbench navigation across core views.
- Agent operational status visibility.
- Knowledge ingestion status visibility.
- Eval report and behavior case visibility.
- Run timeline inspection.
- Tool-call detail inspection.
- Local approval decision interaction.
- Decision history visibility.

## Commands

Web development:

```bash
npm run web:dev
```

Web quality gates:

```bash
npm run lint
npm run build
npm run test:e2e
```

The root `npm run test:e2e` delegates to the Web workspace.

## CI Coverage

The Web CI job now runs:

```text
npm install
npm run lint
npm run build
npm --workspace apps/web exec playwright install --with-deps chromium
npm run test:e2e
```

## Known Limitations

These limitations are intentional for Phase 5:

- Workbench data is fixture-backed, not live API-backed.
- Approval decisions in the Web UI are local browser state only.
- Settings are read-only and cannot mutate runtime configuration.
- Authentication and authorization are not implemented in the Web UI yet.
- Route-per-page navigation is not implemented yet.
- Web views do not yet call every backend API.
- Live run streaming is not implemented yet.
- Web UI does not yet persist user preferences.
- Playwright coverage is smoke-level only.
- Cross-browser Playwright matrix is not implemented yet.
- Visual regression testing is not implemented yet.
- Accessibility checks are not automated yet.
- The Web UI is operator-console oriented; chat is not implemented as a
  first-class interaction mode yet.

## Engineering Notes

Phase 5 intentionally used a fixture-backed UI because the backend runtime
surface is still moving quickly. This keeps Web development useful without
coupling every UI step to a live integration contract too early.

The API client exists as a typed boundary for the future live data path. Phase 6
should keep the release experience honest: document what is live, what is local,
and what is a preview surface.

The lint script now runs Next type generation before TypeScript:

```bash
next typegen && tsc --noEmit
```

This avoids relying on stale `.next` type artifacts in clean environments.

## Closure Verification

Day 33 verification:

```bash
npm run lint
npm run build
npm run test:e2e
git diff --check
```

Playwright result:

```text
2 passed
```

## Known Dependency Risk

`npm install` currently reports:

```text
3 high severity vulnerabilities
```

No automatic `npm audit fix --force` was applied during Phase 5 because it may
perform breaking dependency upgrades. This should be reviewed during Phase 6
release hardening.

## Next Phase

Phase 6 starts on Day 34:

```text
Deployment, Docs, and v0.1 Release
```

The next focus is making the project usable from a fresh clone:

- Full Docker Compose verification.
- Environment configuration review.
- Quickstart hardening.
- Production configuration guide.
- Architecture and feature documentation updates.
- Examples.
- CONTRIBUTING.
- SECURITY.
- ROADMAP.
- Release checklist.
- v0.1.0 release notes.
