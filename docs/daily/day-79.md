# Day 79: Backup and Restore Guidance

Goal:

Document backup and restore guidance for self-hosted Agent Kernel deployments
before the v1.0 release candidate hardening work moves into security and smoke
test gates.

Scope:

- Add backup and restore guidance for Postgres, SQLite local development, local
  object storage, and S3/MinIO-compatible object storage.
- Define restore validation and rehearsal expectations.
- Link backup guidance from production and upgrade docs.
- Update docs index, daily index, and milestone tracking.
- Do not add backup automation code yet.

Tasks:

- [x] Check current git status before editing.
- [x] Review storage, production configuration, and upgrade policy docs.
- [x] Add backup and restore guidance.
- [x] Link backup guidance from production configuration docs.
- [x] Link backup guidance from upgrade and migration policy.
- [x] Update docs index and daily index.
- [x] Update v1.0 RC milestone tracking.

Acceptance:

- [x] Postgres backup and restore expectations are explicit.
- [x] Object storage backup and restore expectations are explicit.
- [x] SQLite local-development backup expectations are explicit.
- [x] Restore validation checklist is documented.
- [x] Upgrade policy points to backup guidance.
- [x] Day 79 does not introduce new runtime scope.

Verification:

- [x] `git diff --check`

Notes:

- Backup automation, retention enforcement, encrypted backup pipelines, and
  disaster-recovery drills remain deployment-specific until a later dedicated
  automation track.
