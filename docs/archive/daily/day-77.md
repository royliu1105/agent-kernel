# Day 77: Versioned Configuration Documentation

Goal:

Document the v1.0 release candidate configuration contract so operators know
which environment variables are stable, preview, internal, or deferred.

Scope:

- Add a versioned configuration reference.
- Define configuration compatibility rules.
- List stable environment variables with defaults, owners, and secret status.
- Call out preview and intentionally undocumented internal settings.
- Update production docs and milestone tracking.
- Do not add new runtime configuration behavior.

Tasks:

- [x] Check current git status before editing.
- [x] Audit `.env.example`, Docker Compose, API, CLI, Web, provider, RAG,
  storage, auth, and observability configuration variables.
- [x] Add versioned configuration reference documentation.
- [x] Update production configuration guide to point to the new contract.
- [x] Update docs index and daily index.
- [x] Update v1.0 RC milestone tracking.

Acceptance:

- [x] Stable v1.0 configuration variables are listed in one reference.
- [x] Defaults and required production values are explicit.
- [x] Secret-bearing variables are identified.
- [x] Preview/internal/deferred configuration boundaries are explicit.
- [x] Configuration change-control rules are documented.
- [x] Day 77 does not introduce new runtime config behavior.

Verification:

- [x] `git diff --check`

Notes:

- The configuration contract version is a documentation and release contract,
  not a new runtime `CONFIG_VERSION` variable.
