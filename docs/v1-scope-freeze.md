# v1.0 Scope Freeze

This document freezes the Agent Kernel v1.0 release scope.

## Decision

Agent Kernel v1.0 is a stable, self-hosted AI Agent runtime and operator
workbench.

It is not a hosted SaaS platform, marketplace, no-code workflow builder,
enterprise identity platform, benchmark product, or managed cloud service.

The v1.0 release should ship when the frozen self-hosted runtime contract is
verified, documented, and reproducible from a clean checkout.

## Release Blockers

These items must be completed, fixed, or explicitly waived before v1.0 final:

- Fresh full-stack Docker Compose restart from a clean checkout, or an explicit
  release-owner waiver with evidence.
- Final v1.0 release checklist.
- Final v1.0 release notes.
- Day 90 final verification across release smoke, release eval, load/soak,
  Python checks, Web checks, and migration checks.
- No silent security limitation. Any remaining security limitation must be
  either fixed, removed from stable scope, or listed in this document and the
  release notes.
- No stable public API, CLI, configuration, migration, or deployment behavior
  may contradict the v1.0 docs.

## Accepted v1.0 Limitations

These limitations are acceptable for v1.0 only because the project is scoped as
a self-hosted runtime and the limitations are documented for operators:

- API-key authentication is disabled by default for local quickstart
  compatibility. Production deployments must set
  `AGENT_KERNEL_API_KEY_AUTH_ENABLED=true`.
- Browser login, OIDC, SSO, and password auth are not included.
- The Web Workbench supports core operator workflows, but it is not a complete
  administration console.
- Public hosted SaaS tenant isolation is out of scope.
- `/metrics` has no built-in authentication and must be protected by network,
  reverse proxy, gateway, or platform controls.
- Secrets manager integration is deployment-specific.
- Remote sandbox execution is not implemented.
- Browser session automation is not implemented.
- Redis queue adapter support exists, but database-backed polling remains the
  default worker execution path.
- Stuck-run recovery is conservative and fails expired in-flight runs instead
  of automatically replaying every run.
- Server-side eval dataset upload, eval job scheduling, LLM-as-judge, and live
  provider eval execution are not part of the stable v1.0 surface.
- OpenTelemetry configuration exists, but collector deployment, trace retention,
  dashboards, and alert policies remain operator responsibilities.
- Dependency advisories must be reviewed at release time and either resolved or
  explicitly accepted in release notes.

## Deferred Beyond v1.0

These are intentionally outside the v1.0 release and must not block it:

- Hosted multi-tenant SaaS.
- Multi-region managed cloud deployment.
- Full enterprise SSO and identity-provider administration.
- Fine-grained billing, quota, and usage-plan management.
- Third-party tool marketplace.
- Advanced multi-agent marketplace.
- Visual no-code workflow builder.
- Browser session automation product surface.
- Remote sandbox execution service.
- Cross-browser Web test matrix.
- Public performance dashboard.
- Large-scale benchmark leaderboard.
- Stable APIs for hybrid retrieval, RRF, reranking, query rewriting, and
  advanced retrieval pipelines.
- Stable APIs for server-side eval dataset management and eval job execution.

## Scope Change Rules

After Day 87, v1.0 scope changes must follow these rules:

- A change can be added before v1.0 only when it fixes a release blocker,
  removes a documented contradiction, or completes Day 88-90 release work.
- A new product feature should move to v1.x unless it is required to make the
  documented v1.0 contract true.
- A preview surface may remain preview if it is documented and does not weaken
  the stable contract.
- A stable surface may be demoted only if docs, tests, release notes, and
  compatibility policy are updated together.
- Any waiver must name the waived item, the evidence reviewed, the risk owner,
  and the follow-up milestone.

## Day 88 Handoff

Day 88 should turn this scope freeze into the final v1.0 release checklist.

The checklist should have separate sections for:

- Required final verification.
- Required documentation.
- Security and dependency review.
- Clean-machine rehearsal status.
- Accepted limitations.
- Deferred work that must not block v1.0.
