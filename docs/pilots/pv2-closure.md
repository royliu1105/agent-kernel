# PV2 Evidence and Remaining Gates

Date: 2026-11-15. Status: **in progress; full PV2 not accepted**.
The canonical checklist remains [the pilot plan](../real-scenario-pilot-plan.md).
This records evidence, not a replacement or a relaxation of its requirements.

The authorized API/CLI offline technical work is verified on cbe8c42. **Five of
seven canonical checklist items are checked**; the remaining two are full
authenticated Web/first-run acceptance and CF1 residual-risk disposition with
full CF2 closure. This is not another implementation/preparation loop for the
completed offline harness, and no PV3 paid calls or PV5 user sessions are claimed.

The bounded Web implementation candidate is now available; its
[acceptance matrix](pv2-web-acceptance.md) is entirely pending main-agent
exact-candidate CI. The consolidated
[CF1 decision list](../reviews/cf1-risk-disposition.md) is pending the maintainer's
explicit disposition. These are the two remaining closure paths, not new passes.

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
Both container steps passed on cbe8c42 in
[CI 43674964968](https://github.com/royliu1105/agent-kernel/actions/runs/43674964968).
The profile log explicitly records v3/1024 indexing, three persisted approvals,
zero pre-approval dispatches, all three closed executor journals and final
approved/rejected/concurrent HTTP counts **1/0/1**. The retry-only task finishes
without a tool. Full candidate checks are tracked separately from this job.

The two-call runtime ceiling counts failed provider attempts too. Therefore the
pre-dispatch retry case must finish without a lookup on its second model call;
it cannot assume a third synthesis call remains. Approved lookup cases use one
initial call and one continuation. This is an intentional frozen-budget limit,
not a reason to increase limits or claim a retried lookup flow succeeded.

Full authenticated Web acceptance remains pending. The candidate implements
the in-memory workspace API key, Bearer proxy, backend per-request RBAC path and
actual UI create-agent/KB/upload/ingest/chunk/index/Run/queue/approval/resume/output/
logout journey. Real Docker fixture-provider plus browser verification is planned
in remote CI; all new checks in the [Web record](pv2-web-acceptance.md) are pending.
The accepted API/CLI-first route does not waive full Web acceptance, and the
historical rehearsal did not implement or verify this new path. Do not mark all
seven canonical PV2 boxes done because an earlier job or general CI is green.

The other non-test gate is the maintainer's CF1 residual-risk disposition. The
[reviewed repair](../reviews/2026-11-14-cf1-minimal-repair.md) and adversarial
memory fixture establish bounded implementation evidence, not that disposition.
The [consolidated risk list](../reviews/cf1-risk-disposition.md) separates exact
risks, consequences, existing mitigations and evidence limits; every decision
remains pending. Even a future Web CI pass cannot supply maintainer acceptance.
The accepted retrieval/memory scope was explicitly not a general risk waiver.
Do not invent a maintainer sign-off or admit real pilot users from these results.
Two independent participants and dates remain PV5 inputs, not extra PV2 coding.

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

Verification checkpoint: 276 focused offline tests, Ruff and mypy (251 source
files) passed locally. A wider local unit run was not a clean pass: 823 passed,
178 PostgreSQL setup errors and five failures without the required DB/listener
permissions; one logging assertion passed in isolation. Use the full remote
backend suite as the acceptance evidence, not that blocked local run.

CI history is retained rather than replaced by optimistic status:

- c416add / 43674217209: container controls passed, but evidence cleanup failed
  because Linux retained root ownership of private bind-mounted files. The fix
  transfers ownership only inside the owned evidence mount, retaining 0600/0700.
- a6bc97a / 43674646669: control/cleanup step passed; the profile matrix's retry
  case incorrectly expected lookup after exhausting both model attempts. Corrected
  to finish the retry case without a tool; production limits remain unchanged.
- cbe8c42 / 43674964968: **all five CI jobs passed** (python, web, compose,
  observability, pv2). Python: **1394 passed, 15 skipped**, including all six
  API/Worker cases, both persisted approval observation cases and eight profile
  hook unit cases. Both container steps passed with complete cleanup/sealing.
  Web smoke: two passed/one explicitly skipped. Dedicated Compose and observability
  jobs separately cover their opted-in deployment checks. Skips are not passes.
  This remains fixture evidence, not a live-model or authenticated Web pass.

Commands for reproduction on an authorized disposable **remote CI runner**:

```sh
python scripts/cf2_rehearsal.py --pv2
python scripts/cf2_rehearsal.py --pv2-profile
uv run pytest --ignore=tests/integration/test_real_backend_drill.py
```

The Python job supplies its guarded test PostgreSQL/Redis URLs and runs the
restore/eval gates separately; do not copy these commands against an active DB.
The container modes reject non-CI execution before touching Docker. See
`.github/workflows/ci.yml` for the exact environment and separate deployment jobs.

No local environment, current Docker or paid provider was used by this work.
