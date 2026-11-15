# PV1 Offline API/CLI Preparation

Date: 2026-11-15. Status: **prepared, not executed or accepted**. This supporting
specification belongs to the [PV1 contract](pv1-2026-11-15-runbook-assistant.md),
not a new phase or a second progress ledger. DeepSeek no-training evidence and
external transmission permission remain pending; spending authorization USD 0.
No support submission is assumed. No local environment, request, key or identity
is created. Existing CI/review permissions do not authorize rehearsal execution.

## Request Assembly Contract

The [JSON template](pv1-offline-request-template.json) is a preparation artifact,
not an API body or runnable client. No substitution/runner is installed. Its
status, provenance and evidence-case fields must never be posted as Run input.
Use only the separately assembled run_create_body_template as the future API
body. Reject unresolved placeholders before any later authorized submission.

Offline tests assemble only in memory:

1. Read the exact frozen task prompt bytes and verify its recorded SHA-256.
   Replace TASK_PROMPT_UTF8 with the decoded text, preserving the final newline.
2. Select A01 from questions.json, not the reviewer answer key. Replace
   QUESTION_TEXT in task_template, and bind PILOT_KB_UUID to a synthetic UUID in
   unit tests or the approved workspace-A KB in a future authorized environment.
3. JSON-serialize task_template to the user message TASK_JSON; do not concatenate
   unescaped question text into JSON. top_k=5 is requested, not server-enforced
   by this message. No KB is created or searched by assembly.
4. Validate the API envelope and build the provider-facing request in memory.
   The template intentionally uses mock:pv1-offline and an empty fallback list.
   This is not the live DeepSeek profile, a model availability check or evidence
   that the mock will perform retrieval/tool calls.

Source: [API schemas](../../apps/api/src/agent_kernel_api/schemas.py),
[runtime input mapping](../../packages/kernel-runtime/src/kernel_runtime/execution.py),
[Responses serializer](../../packages/kernel-providers/src/kernel_providers/openai.py).

The runtime uses input.messages when it is a list; input.task is then ignored.
Never supply both and assume task is appended. Agent creation accepts name and
description, not a prompt_id/version binding. A saved prompt artifact or registry
entry is not automatically loaded by this API path. The operator-controlled
template supplies the exact instruction explicitly; this does not enforce it on
arbitrary client requests. The same applies to requested top_k and no fallback.

Do not pass privileged request JSON construction to untrusted participants and
claim the instruction/model scope is enforced. The API/CLI subset needs an
explicit supervised admission procedure before user tasks, without adding a new
gateway or UI here. Memory is omitted from this base example only; this does not
disable memory or pass the existing adversarial memory cases.

## API and CLI Shape

The following are future operation mappings, not commands to execute now. A run
must be created, queued, inspected and separately resumed where applicable.
Creating a Run is a persisted write even when it does not invoke a model yet.

| Purpose | Existing HTTP path | CLI command shape / request body |
| --- | --- | --- |
| Create Agent | POST /v1/agents | agent create --name; name/description only |
| Create Run | POST /v1/agents/{agent_id}/runs | run create AGENT_ID --input @FILE; API body is {input: FILE_CONTENT} |
| Queue Run | POST /v1/runs/{run_id}/queue | run queue RUN_ID; may enable Worker execution |
| Inspect Run/events | GET /v1/runs/{run_id} and /events | run inspect / run events RUN_ID |
| Inspect approval | GET /v1/approvals/{approval_id} | approval inspect APPROVAL_ID |
| Approve | POST /v1/approvals/{approval_id}/approve | approval approve APPROVAL_ID --note; body decision_note |
| Reject | POST /v1/approvals/{approval_id}/reject | approval reject APPROVAL_ID --reason; body reason |
| Resume | POST /v1/runs/{run_id}/resume | run resume RUN_ID --approval-id APPROVAL_ID; body approval_id |

CLI --input takes the inner input object, NOT the whole API {input: ...} envelope.
Source: [CLI](../../apps/cli/src/agent_kernel_cli/main.py). Its API URL comes from
--api-url / AGENT_KERNEL_API_URL; future execution must explicitly use the
isolated endpoint, never silently fall back to the active local port. Credentials
come from private configuration (AGENT_KERNEL_API_KEY), not command arguments or
this artifact. A missing/invalid credential and cross-workspace request require
their own future HTTP evidence; schema validation does not prove authorization.

Approving records a decision; it does not prove execution. Resume is an active
execution endpoint, not inspection or merely a queue notification. The approving
API (which also executes resume) and Worker must share the approved configuration
and instrumented transport; observing only Worker dispatches is incomplete.
CLI HTTP timeout does not change server limits. Do not replay resume
automatically after a client timeout; inspect evidence and disposition first.

## Proposed Identity Matrix

These are labels, not created accounts, keys, memberships or final assignments.
All UUIDs/roles/endpoints must be recorded privately before authorized setup.

| Label | Proposed workspace/role | Scope of evidence |
| --- | --- | --- |
| operator-A | A / operator, held by maintainer | Agent/run creation, approval review and resume |
| viewer-A | A / viewer | Read access; run writes and approval review denied |
| operator-B | B / operator | Known A object IDs must not reveal A objects or allow decisions |
| no-key | None | Authenticated API rejects unauthenticated access |

Source: [role permissions](../../packages/kernel-identity/src/kernel_identity/authorizer.py)
and [API auth](../../apps/api/src/agent_kernel_api/auth.py). Operator includes both
run:write and approval:review. There is no claimed submitter/approver separation
or dedicated submit-only participant role. Viewer cannot submit tasks or inspect
approvals. Do not hand operator credentials to trial users as a least-privilege
solution; participant admission remains pending. Local RBAC table tests are not
HTTP/authentication or cross-workspace database evidence.

## Future Evidence Capture

All six evidence cases in the JSON artifact remain not_run. Their pass criteria
are the existing [independent invocation matrix](pv1-2026-11-15-runbook-assistant.md#independent-invocation-evidence),
not a newly relaxed definition. The GitHub observer is still unimplemented.

| Step | Evidence required later | Prohibition / incomplete condition |
| --- | --- | --- |
| Before submission | Candidate SHA, image/lock/config and harness hashes; workspace/principal/KB map; exact prompt version/hash | No active-stack reuse or unreviewed binding |
| Initial request | Actual composed messages/tool definitions, model route, effective limits and admitted context | A template hash alone is not runtime proof |
| Waiting/rejected | Persisted run/tool/approval IDs plus complete zero-dispatch window | Missing observer coverage is unknown, not zero |
| Approved continuation | Matching approval and tool_call_id, one dispatch and validated complete response | approved alone is not successful execution |
| Repeated/concurrent/new executor | Combined durable journal, prior calls and persisted counters across all participating executors | Do not count only the winning executor |
| Actual model request after resume | Prompt/context/history and counters preserved; tool output treated as untrusted | In-memory serialization is not persisted resume evidence |
| Failure/timeout | Dispatch-start/completion correlation and run/tool error disposition | Unknown remote outcome never justifies automatic retry |

Private evidence retains raw artifacts under the accepted retention rule. Publish
only sanitized summaries/references. The observer journal must not log bodies or
credentials; do not mix its metadata with separately reviewed private response
inspection. No raw GitHub response has been retrieved or approved for external
transmission. run_attempt, API-version choice and tool timeout freeze remain open.

## Remaining Preparation and Verification

Source/request-shape checks can proceed offline. A real deployed prompt binding,
HTTP auth, admission workflow, tool observer, actual provider continuation, RAG
quality and cost controls cannot pass through these tests. They remain in PV1-PV6
at their original gates; this file does not authorize implementation or execution
of those future components. No runtime feature or provider choice is changed.

Next offline work can finalize the harness specification and evidence form;
operator confirmation is still needed for participant admission and the final
configuration. Provider terms/reply, actual billing constraints, real response
inspection, two trial participants and dates remain unresolved. Do not invent
answers or ask for final external transmission approval while evidence is absent.

Offline verification is in
[test_pv1_offline_preparation.py](../../tests/unit/test_pv1_offline_preparation.py).
It checks template authority flags, all 30 question shapes, frozen prompt bytes
through the existing serializer, messages/task precedence, unsupported Agent
prompt binding, CLI envelope construction, decision body schemas and the role
permission table. Socket connections are forbidden in these tests and the CLI
request helper is replaced with an in-memory capture. No provider completion,
HTTP request, Run execution, database or application server is used. Checking
all 30 shapes does not execute or score any of the 30 behavioral cases.
