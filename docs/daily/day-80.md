# Day 80: Security Hardening Checklist

Goal:

Document the v1.0 release candidate security hardening checklist and update
security posture docs so release decisions use the current Beta-complete
baseline instead of older v0.1 wording.

Scope:

- Add a v1.0 RC security hardening checklist.
- Update `SECURITY.md` to describe the current security posture.
- Update Auth/RBAC docs from Beta wording to v1.0 RC wording.
- Link security hardening guidance from production docs.
- Update docs index, daily index, and milestone tracking.
- Do not add new security features unless a release blocker is found.

Tasks:

- [x] Check current git status before editing.
- [x] Review existing security policy, Auth/RBAC, production config, and
  security spec docs.
- [x] Add v1.0 RC security hardening checklist.
- [x] Update `SECURITY.md` current posture.
- [x] Update Auth/RBAC scope wording.
- [x] Link security hardening checklist from production config.
- [x] Update docs index and daily index.
- [x] Update v1.0 RC milestone tracking.

Acceptance:

- [x] Security hardening release gates are explicit.
- [x] Current implemented controls and known limitations are accurate.
- [x] Public hosted SaaS is explicitly out of scope without more controls.
- [x] Auth/RBAC docs no longer describe the current baseline as only Beta.
- [x] Release blockers and follow-up areas are clearly identified.
- [x] Day 80 does not introduce new runtime scope.

Verification:

- [x] `git diff --check`

Notes:

- Day 80 creates the security checklist. Day 85 can fix blockers discovered
  during clean-machine rehearsal or security checklist review.
