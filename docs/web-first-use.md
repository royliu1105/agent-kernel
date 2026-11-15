# Authenticated Web First Use

Status: implementation candidate; remote Docker/browser verification pending.
See [PV2 evidence](pilots/pv2-web-acceptance.md) for the tested revision and scope.
These instructions do not authorize starting or changing a deployment.

## Access Boundary

The maintained entrypoint is `/`; sample screens are explicitly at `/preview`.
Use the workspace API key issued by your operator, never a model-provider key.
The key exists only in the current page's memory. Reloading requires sign-in
again; no local storage, session storage or authentication cookie is used.
The Web server forwards the caller's Bearer credential to its fixed configured
API. It does not have a shared privileged credential or select a workspace from
browser-supplied headers. The API rechecks key validity, membership and role on
every operation. Viewer accounts can inspect permitted records but cannot
create agents, write knowledge, submit Runs or review approvals.

`AGENT_KERNEL_API_URL` must be an explicit server-side HTTP(S) origin without
credentials, query or path. Never expose a key through `NEXT_PUBLIC_*` variables.
Behind a TLS-terminating reverse proxy, set `AGENT_KERNEL_WEB_ORIGIN` to the
canonical public HTTP(S) origin. Mutation Origin checks use that operator value,
not untrusted forwarded headers; otherwise they use the request protocol/Host.
Use TLS for any non-loopback deployment, and restrict API access at ingress.
This is bounded API-key access, not SSO, MFA, a password login or a server session.
Same-origin malicious script can access an in-memory key; do not use untrusted
extensions or third-party scripts with pilot credentials. Use narrowly scoped,
expiring keys and revoke them through existing operator procedures.

The default Docker localhost profile deliberately has authentication disabled;
the UI displays anonymous mode. It is only for a trusted single-user loopback
environment. A successful anonymous local visit is not authenticated acceptance.

## Workflow

1. Open the Web endpoint and sign in with the intended workspace key. Check the
   displayed principal, workspace and role before writing anything.
2. Create or select an Agent. Create or select a knowledge base. Upload a
   reviewed document, then ingest, chunk and index it in that order. Inspect the
   stored chunks and a retrieval result before submitting a knowledge task.
3. Choose the model, enter the task and, where required, the approved system
   prompt. The safe default is `mock:echo`; it does not exercise native tool
   planning or answer quality. A paid provider requires separate configuration
   and authorization. Selecting a KB does not itself force the model to search;
   include the KB ID and the required retrieval in the reviewed task.
4. Create the Run, retain its ID, then queue it. Refresh the Run to inspect Worker
   progress and the persisted event timeline. A created Run is not yet queued.
5. At `waiting_approval`, inspect the actual bound tool name, immutable arguments,
   Run ID and risk level. Approve or reject with a note. The decision alone does
   not execute the tool. Use **Resume run** explicitly: approved continuation may
   execute the original tool; rejected continuation finalizes a failed Run and
   a denied tool record without invoking it. Do not create a replacement Run
   simply because a request timed out.
6. Inspect the final output, citations and events for the same Run ID. A failed,
   denied or unavailable result must not be interpreted as a completed answer.
7. Sign out. This clears browser credentials and protected state; it does not
   revoke the API key, cancel queued work, undo tool effects or delete evidence.

## Errors and Recovery

401 clears the signed-in UI; use an authorized current credential. 403 means the
current role cannot perform the action, not that the proxy should use an admin
key. Cross-workspace IDs remain inaccessible. 409 requires a state refresh,
especially after an approval or competing resume. Upload/JSON and response size
limits can reject requests; inspect the stored state before any manual retry.

The proxy never retries mutations automatically. A timeout, disconnect or proxy
502 can leave the server outcome unknown; use the existing Run/approval ID and
refresh instead of blindly repeating the operation. UI logout cannot stop an
already admitted server request. Document processing and approval resume remain
synchronous API operations, not a new durable-resume queue.

## Verification Scope

The remote-only `python scripts/cf2_rehearsal.py --web` harness uses a fresh owned
Compose project, real Web/API/Worker/PostgreSQL/Redis and real tool execution
against a counted synthetic MCP fixture. No Playwright business-route mocking
stands in for this journey. Separate preview smoke tests are not its evidence.
The frozen PV1 prompt is checked at the initial and resumed provider boundaries.
The Web fixture uses `openai:cf2-offline`, mock embeddings, a synthetic document
and an eight-model-call ceiling to exercise retrieval, approval and final output.
It is not the two-call DeepSeek/DashScope paid profile; that profile has its
separate `--pv2-profile` offline checks. Neither fixture establishes live quality.

No active local Docker update, paid call or real-user admission is implied.
