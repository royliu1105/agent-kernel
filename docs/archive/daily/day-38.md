# Day 38: v0.1 Final Release Verification

## Goal

Close the remaining v0.1 release-candidate verification gaps before deciding
whether to tag `v0.1.0`.

Day 38 should focus on:

```text
fresh Web install -> dependency audit -> CI status -> release checklist truth
```

## Scope

- Fresh-run Web `npm install` verification from a clean temporary checkout.
- Dependency audit risk review.
- GitHub CI remote status check.
- Release checklist and release-note updates based on verified results.

## Non-Scope

- New runtime features.
- New Web UI features.
- Publishing the `v0.1.0` tag.
- Creating the GitHub release.
- Changing dependency versions without a clear, reviewed reason.

## Tasks

- [x] Review current release checklist and Public Alpha milestone.
- [x] Add Day 38 daily plan.
- [x] Verify fresh-run Web dependency installation from a clean temporary checkout.
- [x] Review `npm audit` findings without applying forced upgrades.
- [x] Check GitHub CI remote status for the current branch or latest pushed commit.
- [x] Fix CI push trigger for the repository default branch.
- [x] Update release checklist with verified status.
- [x] Update release notes or v0.1 docs if release readiness changes.

## Acceptance

- [x] Fresh-run Web install is either confirmed or documented with concrete blocker output.
- [x] Dependency audit risk is reviewed and documented.
- [x] CI status is confirmed or documented with the reason it cannot be confirmed.
- [x] Release checklist reflects only verified facts.
- [x] Next release action is clear.

## Verification

- [x] Fresh temporary checkout `npm install`.
- [x] Fresh temporary checkout `npm run lint`.
- [x] Fresh temporary checkout `npm run build`.
- [x] `npm audit`.
- [x] GitHub CI status check.
- [x] Relevant local quality gates if docs or code change.

## Notes

- Day 38 is release verification, not product expansion.
- Do not use `npm audit fix --force` without an explicit dependency decision.
- Do not tag `v0.1.0` until the user explicitly decides to publish.
- Fresh-run Web install passed from
  `/private/tmp/agent-kernel-fresh-web-day38-XXJTuS`:
  `npm install`, `npm run lint`, and `npm run build`.
- `npm audit --json` still reports 3 high severity vulnerabilities through
  Next.js transitive `postcss` and optional transitive `sharp`.
- Latest stable Next.js was already installed on Day 38, so the reviewed
  decision is to document the risk instead of applying `npm audit fix --force`
  or overriding framework internals.
- GitHub API reported zero visible workflow runs for the repository. The
  workflow previously listened to `main` push while the default and only remote
  branch is `master`. Day 38 updates CI to listen to `master`, `main`, PRs, and
  manual dispatch.
- Local release-documentation gates passed: CI YAML parse, `git diff --check`,
  and stale blocker text search.
