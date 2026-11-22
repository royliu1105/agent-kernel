# Day 76: API/CLI Contract Audit and Compatibility Policy

Goal:

Start the v1.0 release candidate track by documenting which API, CLI, worker,
and Web proxy surfaces are stable, preview, internal, or deferred.

Scope:

- Create the v1.0 API/CLI compatibility policy.
- Audit the current implemented API and CLI surfaces.
- Update product interface docs that still describe older v0.1 behavior.
- Mark the v1.0 RC milestone as started.
- Do not add new runtime features.

Tasks:

- [x] Check current git status before editing.
- [x] Review Stage 9 and milestone acceptance criteria.
- [x] Audit implemented API endpoints.
- [x] Audit implemented CLI and worker commands.
- [x] Audit current Web same-origin proxy routes.
- [x] Add compatibility policy and stability levels.
- [x] Update `docs/interfaces.md` with the current contract baseline.
- [x] Update docs index and milestone tracking.

Acceptance:

- [x] Stable API and CLI surfaces are explicitly listed.
- [x] Preview and internal surfaces are explicitly called out.
- [x] Breaking-change and deprecation rules are documented.
- [x] v1.0 RC has a concrete contract baseline for later release checks.
- [x] Day 76 does not introduce new product scope.

Verification:

- [x] `git diff --check`

Notes:

- Day 76 freezes the contract baseline for review. Later v1.0 RC days may still
  promote, demote, or remove surfaces before the final v1.0 tag, but they must
  update the compatibility policy when they do.
