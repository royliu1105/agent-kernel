# Day 78: Upgrade and Migration Policy

Goal:

Document the v1.0 release candidate upgrade and database migration policy so
operators know how to move between releases without guessing.

Scope:

- Add an upgrade and migration policy document.
- Define version upgrade rules, migration rules, and rollback expectations.
- Document SQLite and Postgres support boundaries.
- Define migration test expectations and release blockers.
- Update production docs, docs index, daily index, and milestone tracking.
- Do not change migration code or runtime behavior unless a blocker is found.

Tasks:

- [x] Check current git status before editing.
- [x] Review existing Alembic migration guidance and release docs.
- [x] Add upgrade and migration policy.
- [x] Link upgrade policy from production configuration docs.
- [x] Update docs index and daily index.
- [x] Update v1.0 RC milestone tracking.

Acceptance:

- [x] Supported upgrade path and unsupported paths are explicit.
- [x] Alembic migration rules are documented.
- [x] SQLite and Postgres migration expectations are explicit.
- [x] Rollback and downgrade expectations are honest.
- [x] Release-blocking migration checks are listed.
- [x] Day 78 does not introduce new runtime scope.

Verification:

- [x] `git diff --check`

Notes:

- Day 79 will add detailed backup and restore guidance. Day 78 only states that
  production upgrades must have a verified backup or restore point before
  running migrations.
