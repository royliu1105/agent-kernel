# PV4 Operations Authorization (2026-11-22)

Status: **executed and accepted** (PV4 ops gate closed 2026-11-22). See
[pv4-2026-11-22-results.md](pv4-2026-11-22-results.md) and
[pv4-closure.md](pv4-closure.md).

## Maintainer authorization

- Decision maker: maintainer (`royliu1105`)
- Date: 2026-11-22
- Goal: close PV4 ops gates for the admitted local Docker candidate after PV3
  R4 acceptance — startup/restart, disposable fault recovery, matched
  PostgreSQL+local-object backup/restore, upgrade/rollback from a **copied**
  v1.0.0-era schema fixture, and bounded mock concurrency. Not PV5/PV6.

## Candidate profile

- Compose project: `agent-kernel-local` (default mock models/embeddings).
- Storage: PostgreSQL/pgvector + **local object store** (not S3/MinIO).
- Redis: enabled for queue hints.
- Same candidate family as PV2/PV3 local path; paid overlay **not** required for
  mock load. Any live-model burst needs a separate line-item approval.

## Authorized actions

1. **Startup/restart rehearsal** on `agent-kernel-local`: `docker-stop` /
   `docker-up` (or equivalent). Inspect queue, approvals, ownership, alerts.
   **No** `down --volumes`, no deletion of `.agent-kernel/docker-local`.
2. **Disposable fault/recovery drills** only on labeled drill containers
   (`agent-kernel.drill=true`) or `agent-kernel-test` — never against the active
   runtime DB/Redis data plane. Includes Worker/Redis/provider-style failure via
   `scripts.backend_drill` and documented integration contracts.
3. **Backup/restore**: `backend_drill backup` (+ matching object manifest) on
   disposable PostgreSQL; record RTO wall-clock and row/object hash checks.
4. **Upgrade/rollback**: build a **copied** fixture database at the v1.0.0
   schema baseline, upgrade to current head with writers stopped on that
   fixture, verify ownership/approvals/checkpoints; prefer verified
   restore-based rollback. Do not mix old/new Workers against one live DB.
5. **Bounded concurrency**: mock burst (`release-load-soak` quick profile or
   equivalent); record queue wait / active latency / errors. No production-scale
   claim. Live paid tasks only if explicitly added later under budget.

## Explicit non-goals / safety

- Do not wipe or restore into `agent-kernel-local` volumes.
- Do not claim S3/MinIO object-version restore (N/A for this local-object
  candidate; gate text requires that drill only when S3 is selected).
- Do not invent checkpoint history; do not cherry-pick failed drills.
- Do not start PV5 or rewrite PV3 gold.

## Evidence

Private: `.agent-kernel/pv4-evidence-20261122/` (gitignored).
Public: `docs/pilots/pv4-2026-11-22-results.md` after execution; ledger
[real-scenario-pilot-plan.md](../real-scenario-pilot-plan.md) § PV4.

## Budget

Mock-first. Paid calls: **none** under this authorization unless amended.
