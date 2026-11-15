# PV2 Evidence and Remaining Gates

Date: 2026-11-15. Status: **in progress; full PV2 not accepted**.
The canonical checklist remains [the pilot plan](../real-scenario-pilot-plan.md).
This records evidence, not a replacement or a relaxation of its requirements.

## Verified Baseline

- [CI 43671367900](https://github.com/royliu1105/agent-kernel/actions/runs/43671367900),
  commit dd2ace3: both PostgreSQL approval observation cases passed, not skipped.
- [CI 43672700313](https://github.com/royliu1105/agent-kernel/actions/runs/43672700313),
  commit 1aa7ace: six API/Worker retry/resume cases and the two prior approval cases
  passed; Python 1382 passed/15 environment-gated skips; all four jobs passed.
- Those are in-process ASGI/Worker fixtures. They establish real repository,
  lease, decision, native continuation and retry behavior, not installed container
  hooks or live provider results. Existing remote Compose/observability jobs cover
  fresh migration/readiness, private monitoring and the default Web proxy separately.

## Container Rehearsal

The dedicated CI job runs `python scripts/cf2_rehearsal.py --pv2`. This mode refuses
execution outside GitHub Actions before creating files or touching Docker. It uses
a random owned CF2 project, internal-only network, private generated credentials,
fresh PostgreSQL/Redis/object volumes and real API/Worker entrypoints. It removes
only that disposable project's resources. No active local data is used.

The existing CF2 rehearsal is retained: actual authenticated CLI/API, ingestion,
retrieval, malicious-memory fixture, scoped denial, approval, API restart, native
continuation, rejection and independent MCP invocation counts. PV2 additions:

- Mount the unchanged frozen task prompt read-only, verify its SHA-256 and assert
  its exact bytes occur in each effective initial/resumed serialized request.
- Give each API/Worker start a fresh identity; reconcile captured requests with
  registered identities and compare effective API/Worker settings.
- Stop the Worker, create/queue a task, and verify the persisted queued state and
  unchanged provider-call count while it is stopped.
- Stop the API too and verify both processes are stopped. Restart only the owned
  project; the same queued task reaches approval without an extra tool effect.
- Revoke the operator API key through the maintained repository. Assert new
  submissions, reads and resume are denied; a same-workspace viewer can still
  inspect retained evidence. Cross-workspace and viewer-write denial are exercised
  by the preceding CF2 scenario.

Stops occur at quiescent boundaries. Revocation prevents subsequent requests; it
does not cancel an already-running call. Force-kill with uncertain external effects
is not exactly-once proof and is not claimed here. Raw scenario evidence and
generated keys are not uploaded; sanitized pass/failure output stays in CI logs.

## Scope That Remains Open

Container verification above is **CF2 synthetic API/CLI acceptance**, not the full
PV1 profile. It uses mock embeddings, an OpenAI-compatible fixture and counted MCP
inventory calls, with a larger model-call ceiling for its three-response RAG flow.
That job alone does not install the PV1 GitHub guarded-HTTP observer/shared budget
transport across all container executors or attest the frozen two-response paid
profile. The task prompt hash alone cannot establish those bindings.

The additional `--pv2-profile` rehearsal now implements that **offline binding**
in a second owned remote project. It uses the real DeepSeek Responses and DashScope
embedding adapters with synthetic transports, v3/1024 indexing, frozen model ID
and execution limits, authenticated API/CLI and Redis Worker, guarded GitHub HTTP
with a synthetic pool below its origin/path/size checks, and one shared durable
admission ledger. Initial, restarted API, concurrent/repeated resume, rejection,
pre-dispatch retry and unknown-charge retry are separate assertions. Per-process
journals must all close before counts reconcile. An expected unknown charge is
asserted to remain unknown and block redispatch; it never becomes a successful
budget window. Fixture charges are conservative reservations, not actual billing.
This new matrix remains pending exact-submission remote verification.

The two-call runtime ceiling counts failed provider attempts too. Therefore the
pre-dispatch retry case must finish without a lookup on its second model call;
it cannot assume a third synthesis call remains. Approved lookup cases use one
initial call and one continuation. This is an intentional frozen-budget limit,
not a reason to increase limits or claim a retried lookup flow succeeded.

Full authenticated Web still lacks its approved credential bridge. The accepted
API/CLI-first route does not waive full Web acceptance. No new Web/auth feature
is implemented by this rehearsal. Do not mark all seven canonical PV2 boxes done
because this job or the general CI is green.

Before paid admission, verify the exact-profile/container observer and budget
binding on the candidate, including its request and approval case matrix.
Use the existing frozen data and permissions; do not issue paid calls as a way
to test these safety controls. Human participants belong to PV5, not these gates.

## Operator Instructions

For the admitted API/CLI subset, use the maintained authenticated CLI commands
in the CF2 scenario as the executable reference. Do not copy older Alpha embedding
examples into the pilot. Apply `pv1-config-v1` explicitly for future pilot setup;
its intended model/embedding settings are not the CF2 mock defaults. Keep each
workspace's key private. A successful approve decision does not execute the tool:
resume is a separate action. Inspect Run, tool and independent observer evidence.
Do not expose the default local unauthenticated Workbench to participants.

Current checkpoint: local static/offline tests only for these container additions;
the new CI job must pass on the exact submitted SHA before its controls are accepted.
Neither a local environment nor current Docker is updated by this work.
