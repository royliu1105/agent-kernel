# Clean-Machine + Mock Happy-Path Rehearsal Results

Date: **2026-11-22 Asia/Shanghai** (UTC run window ~05:16–05:40).

Status: **required clean-machine gates passed on a clean worktree copy**; mock
showcase happy-path passed; **not** PV1–PV6 acceptance and **not** a claim that
`origin/master` alone already contains the uncommitted showcase files.

## Scope

This run follows [clean-machine-rehearsal.md](../clean-machine-rehearsal.md) and
additionally executes the [mock happy-path](mock-happy-path.md) on the
`docker-showcase-up` overlay.

It is **not**:

- Formal PV pilot acceptance
- Paid-provider / real GitHub evidence
- Proof that a pristine `git clone` of `origin/master` already includes showcase
  (those files were still dirty in the source worktree at rehearsal time)

## Baseline

| Field | Value |
| --- | --- |
| Source commit | `4cc43cf48f4ef230651f4176d39ada5d17bd9b33` |
| Source dirty | **yes** (showcase overlay + happy-path script/tests present in copy) |
| Temporary tree | `/tmp/agent-kernel-rehearsal-20261122T131655/agent-kernel` |
| Host | macOS 26.5.2, arm64 |
| uv | 0.11.32 |
| Node / npm | v24.16.0 / 11.13.0 |
| Docker / Compose | 29.7.2 / v5.5.0 |
| Docker Desktop | available (stack `agent-kernel-local`) |

Copy method: `rsync` of the maintainer worktree excluding `.venv`,
`node_modules`, `.agent-kernel`, `.git`, caches. This matches “no hidden local
runtime state” better than reusing the dirty checkout in place, while still
including uncommitted showcase files under test.

## Blocker found and fixed during rehearsal

`uv run mypy .` initially failed:

```text
Duplicate module named "mcp_server"
(examples/external-tools/mcp_server.py vs deploy/local-showcase-tools/mcp_server.py)
```

Classification: **blocker** introduced by the showcase MCP filename.

Fix applied in both the source worktree and the rehearsal tree: rename to
`deploy/local-showcase-tools/showcase_mcp_server.py` and update
`tools.json` / tests. After the rename, mypy reported success on 257 files.

## Passed gates

| Gate | Result |
| --- | --- |
| `uv sync --dev` | passed |
| `npm install` (workspace) | passed (0 vulnerabilities reported) |
| `uv run ruff check .` | passed |
| `uv run mypy .` | passed after rename fix |
| `uv run agent-kernel --version` | `agent-kernel 1.0.0` |
| `uv run agent-kernel-worker --help` | passed |
| `make test-db-up` + `uv run pytest` | **1428 passed**, 35 skipped, 1 warning (~4m18s) |
| `make release-eval` | passed (incl. timeline regression 7/7) |
| `make release-load-soak` | `"passed": true`, 25/25 burst successes |
| `make docker-check` / local-stack config | passed |
| `make release-smoke` | passed (API/CLI smoke + `npm run lint` + `npm run build`) |
| `make docker-showcase-up` | API/Worker/Web healthy; showcase overlay active |
| `curl /healthz` | `{"status":"ok","service":"agent-kernel-api"}` |
| `curl -I` Web `/` | HTTP 200 |
| `make showcase-happy-path` | succeeded |
| `npm run test:e2e` | **9 passed**, 2 skipped (opt-in docker/PV2 specs) |

Skips were environment-gated (Docker-local acceptance opt-in, monitoring,
observability full stack, Redis DB15, self-hosted URL, etc.), not silent
failures.

## Showcase happy-path evidence

Evidence file (gitignored runtime path on the rehearsal tree; copy also under
the maintainer `.agent-kernel/showcase-evidence/`):

```text
evidence-20261122T054012Z.json
evidence_sha256=bd8c3e0345c41b073bc71e3e2795abe26e3156fbed143acdc4064bf193888443
tools_config_sha256=28755c8e0d3afa0bf9f6e5bd5ebf3a227b0673c546b28baa938fbaf201e89412
run_id=a6827999-2cbc-4a82-aa0d-aa65a10b5834
approval_id=f9904257-e7cc-43f8-903a-6549b699cf38
```

Observed:

- `tool_dispatches_before_resume = 0`
- final status `succeeded`
- event order includes `approval_approved` → `run_resuming` → `tool_call_completed` → `run_completed`
- `memory_did_not_bypass_approval = true`
- `cf1_disposition_claimed = false`
- `paid_providers = false`, `real_github = false`

## Remaining honesty limits

1. **Commit/push**: showcase files + the mypy rename fix must be committed before
   a stranger’s `git clone origin/master` can reproduce this exact path.
2. **Not PV**: no CF1 maintainer disposition, no paid cohort, no independent users.
3. **Compose project**: reused project name `agent-kernel-local` on the host
   Docker engine (standard local profile), not a disposable CF2 CI project.
4. Historical [archive results](../archive/clean-machine-rehearsal-results.md)
   remain historical (SQLite-era notes); this file is the 2026-11-22 record.

## Command log location

Host-side transcripts (not committed):

```text
/tmp/ak-rehearsal-uv.log
/tmp/ak-rehearsal-npm.log
/tmp/ak-rehearsal-ruff.log
/tmp/ak-rehearsal-mypy.log
/tmp/ak-rehearsal-pytest.log
/tmp/ak-rehearsal-release-eval.log
/tmp/ak-rehearsal-load-soak.log
/tmp/ak-rehearsal-release-smoke.log
/tmp/ak-rehearsal-docker-up.log
/tmp/ak-rehearsal-happy.log
/tmp/ak-rehearsal-e2e.log
/tmp/agent-kernel-rehearsal-20261122T131655/tool-versions.txt
```
