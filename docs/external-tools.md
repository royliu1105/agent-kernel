# External Tools: MCP and OpenAPI

## Integration Contract

External capabilities are ordinary registry tools. They use the existing schema
validation, executor timeout, risk policy, persisted approval and runtime event
paths. They do not get a separate execution API. The current Python stack is
retained.

```python
from kernel_tools.external import (
    external_tools_config_from_env,
    register_external_tools,
)

# API lifespan, or the worker's single top-level async main:
async with register_external_tools(registry, external_tools_config_from_env()) as loaded:
    # Existing runner and PolicyAwareToolExecutor must use this exact registry.
    # Serve requests / poll work here, then drain runs before leaving this block.
    ...
```

`AGENT_KERNEL_EXTERNAL_TOOLS_CONFIG` names an operator-owned local JSON file.
When unset, the loader is a no-op. Malformed config, unavailable servers,
unsupported schemas, missing allowlisted operations, or duplicate tool aliases
fail startup atomically. No partial catalog is published. The loader snapshots
configuration and metadata at startup; remote catalog changes require a restart
and operator review. Do not accept this configuration from model arguments,
workspace uploads, or an unauthenticated API.

`load_external_tools` and `register_external_tools` are aliases returning an
async context manager. `LoadedExternalTools.tool_names` contains registered
local aliases, not raw sessions. Each API process/worker owns its own sessions.
Each MCP connection has a dedicated owner task that enters/exits the SDK's
AnyIO cancel scopes. Transport failures must not cancel the API/worker lifespan.
Tool calls can run on other tasks in that event loop. Stop intake and
drain/cancel active runs before closing; closed handles reject further calls.
Never construct a session using one `asyncio.run` and use/close it in another.

Dependencies are declared by `kernel-tools`: official `mcp>=1.30.0,<2`,
`httpx>=0.28.1,<0.29`, and `httpcore>=1.0.9,<1.1`. The pin targets the tested SDK
1.x session API, not an assertion that it is the latest release. Dependency
audit and SDK upgrades remain release responsibilities. Root dependency lock,
API/worker bootstrap, env documentation and CI integration are owned by the
parent integration change, not by an adapter silently updating them.

## Trusted Configuration and Policy

Each binding has a local `contract` with a stable `name`, optional operator
description, `risk_level`, `read_only`, `idempotent`, `retry_safe`,
`policy_decision`, and `timeout_ms`. Remote MCP annotations, OpenAPI vendor extensions, descriptions,
server URLs and authentication hints cannot set these fields.

- Default risk is `network`, which requires approval under the default policy.
  `read_only=true` does not itself remove approval.
- Optional `policy_decision` is `allow`, `deny`, or `require_approval`. Omission
  retains the existing risk defaults. This is independent of risk: an operator
  can require approval for a read-only resource or prompt without lying about
  its risk. The normal `ToolPolicyEvaluator` reads trusted binding metadata, so
  the existing API/Worker execution and persisted approval/audit paths apply.
  An explicit central tool-name decision and binding decision compose using
  the stricter result (`deny` > `require_approval` > `allow`). An explicit
  binding `allow` overrides risk defaults only, not a central explicit denial
  or approval requirement. Treat it as a reviewed privilege grant. It does not
  override workspace access, schema validation, timeout, or retry vetoes.
- `read_only` is a reviewed semantic claim, not a server-supplied annotation.
  `RiskLevel.READ_ONLY` is rejected without that claim.
- Automatic retry eligibility requires both `read_only=true` and
  `idempotent=true`, plus `retry_safe=true`. All defaults are false. Mutating
  HTTP methods cannot be declared read-only. No adapter retries an invocation.
- Runtime must treat `ToolMetadata.retry_safe=False` as a hard retry veto,
  `None` as the existing internal-tool rule, and `True` only as eligibility
  subject to the existing risk/approval checks. Do not automatically replay
  writes, even when an external service supports idempotency keys.
- OpenAPI's optional `idempotency_header` requires an idempotent contract and
  `ToolExecutionContext.tool_call_id` from the persisted tool call. The stable
  UUID is reused for an explicitly resumed call. Never use a lease token.
  Only `Idempotency-Key` or `X-Idempotency-*` headers are accepted. It is the
  external service's responsibility to actually deduplicate the request.
- MCP has no universal side-effect deduplication promise here. Vendor-specific
  idempotency arguments are not injected or inferred. Ambiguous MCP write
  outcomes require reconciliation, not blind retries.

Server/API `access.workspace_ids` is an explicit allowlist checked against
trusted execution context before any operation I/O. It defaults to empty.
`allow_unscoped=true` is only for explicitly enabled local operator workflows.
It does not authorize arbitrary authenticated workspaces. API/worker must
populate workspace context from persisted run ownership. Shared allowed
workspaces use the same configured external credential; deploy separate
bindings/credentials where identities must remain distinct.

## MCP Support

The official SDK owns JSON-RPC, initialization, cancellation, session IDs and
transport framing. Supported transports are stdio and Streamable HTTP, not the
legacy SSE transport. Explicit `bindings` expose selected tools, exact resource
URIs and named prompts. All three become normal tools with the same policy,
approval, timeout, workspace and result-size controls. Resource reads accept
no caller URI; prompt arguments are validated strings. No resource/prompt
prefetch bypasses policy. Discovery lists metadata only.

`stdio.command` must be an absolute operator-approved executable; `args` are
an argument vector, never a shell command. Only the SDK's minimal inherited
environment and explicit `stdio.env` values reach the child. Stderr is not
forwarded into application logs. SDK lifecycle closes and reaps the subprocess.
This is **not an OS sandbox**: approved executables can access host files/network.
Use a restricted service account or a container with resource and egress limits.

`discovery_timeout_ms` bounds connection initialization plus catalog discovery.
It is not installed as the session-wide read timeout. Each tool/resource/prompt
uses its own `contract.timeout_ms`, covering reconnect, local queue wait and RPC.
HTTP endpoint timeouts separately bound network I/O and can be shorter. Calls on
one MCP connection are serialized with at most 64 queued invocations; overflow
fails without dispatch. This deliberately trades per-server concurrency for a
bounded failure/ownership boundary. Separate configured servers have independent
owners. Timeout/cancellation does not prove that a remote write was rolled back.

All HTTP redirects are rejected in the guarded transport, before the SDK can
follow a 307/308 and resend a POST. Setting HTTPX `follow_redirects=False` alone
is insufficient for SDK 1.30.0. Configure the exact canonical MCP endpoint,
including its trailing slash. HTTP failure tears down only that connection;
its in-flight/queued calls fail without replay. A later explicit invocation can
reconnect and rediscover, but the selected sanitized input/output contracts must
match the startup snapshot. A changed catalog fails before operation dispatch
and requires operator review/restart. Never treat reconnect as permission to
retry an ambiguous external write.

The SDK logs raw initialization results, malformed notifications and exception
details, including via Python's root logger. A scoped diagnostic filter is
installed before transport startup on SDK loggers and configured handlers. SDK
owner/child tasks replace diagnostic payloads with a fixed message and remove
exception/stack text **before formatting**; unrelated application tasks retain
their logs. Lazy HTTP transport loggers are covered by root-handler filters.
This is defense in depth alongside central API/Worker logging configuration,
not a replacement for it. Configure logging before loading external tools;
hot replacement of handlers during active sessions is not supported. Operational
failure information remains in normal bounded tool errors and persisted events,
not raw SDK message bodies. Child stderr remains discarded.

Catalogs have entry/page/time bounds. Remote descriptions, titles, defaults and
examples are removed from exposed schemas. Input schemas support bounded
object/array/primitive constraints and composition, with non-cyclic local
references only. External references, regex patterns, unknown validation
keywords and excessive depth/size fail closed. Selected output schemas are
checked too, before the SDK can validate returned structured output. No remote
instructions, sampling callbacks, elicitation handlers, roots, OAuth discovery,
resource templates or completion endpoints are enabled.

Results are labeled `untrusted` and bounded; they remain data, not system or
developer instructions. Sanitization cannot prove arbitrary returned text or
schema enum values are free of prompt injection. Permission checks and model
instruction boundaries must remain intact.

## OpenAPI Support

The structured parser accepts a local JSON OpenAPI 3.0/3.1 document, up to 1 MiB.
It exposes only `bindings[].operation_id`, rejects duplicate IDs and resolves
bounded local references. It is deliberately a fail-closed subset:

- Primitive path/query parameters, simple/form serialization and JSON bodies.
- Parameter types, required values, unknown argument groups and body schemas
  are validated before I/O; encoded path traversal is rejected.
- Header/cookie parameters, external refs, multipart, YAML and advanced array
  serialization are unsupported. Credential headers are operator-owned, not
  model-controlled arguments. Unsupported operations fail startup.
- Server URLs from the specification are ignored. The trusted `endpoint.url`
  fixes origin and path prefix. TLS verification is enabled. Redirects, ambient
  proxies and transparent compression are disabled. HTTP response streams are
  byte-bounded, including responses without Content-Length.
- A custom HTTPX transport uses HTTPCore's public network backend extension.
  DNS is resolved and checked at TCP connection creation; only the vetted IP
  reaches the socket backend. Original Host and TLS SNI remain the configured
  hostname. Mixed public/private answers are rejected, and fresh connections
  revalidate DNS, closing the check/second-resolution rebinding window.
- Private, loopback, link-local and non-global addresses are denied unless
  `allow_private_network=true` explicitly permits an operator-managed internal
  endpoint. Plain HTTP also requires that opt-in. Do not enable it for
  user-supplied hosts; enforce network egress at deployment as defense in depth.

HTTP failures expose status/classification, not remote error bodies, credential
headers or arbitrary SDK exception text. Config secrets use `SecretStr` and are
excluded from model representations. Use tightly permissioned secret-mounted
config or build configuration from a secret manager in trusted bootstrap code;
never commit real tokens in example JSON. Incoming user/API credentials are
never forwarded automatically, and redirects cannot carry credentials away.

An OpenAPI configuration entry (replace the endpoint and workspace ID with
operator-approved values) looks like:

```json
{
  "openapi": [{
    "name": "inventory",
    "document": "examples/external-tools/openapi.json",
    "endpoint": {"url": "https://inventory.example.org/v1"},
    "access": {"workspace_ids": ["11111111-1111-4111-8111-111111111111"]},
    "bindings": [
      {"operation_id": "get_item", "contract": {
        "name": "get_item", "read_only": true, "idempotent": true,
        "risk_level": "read_only", "policy_decision": "require_approval"
      }},
      {"operation_id": "create_item", "idempotency_header": "Idempotency-Key",
       "contract": {"name": "create_item", "idempotent": true}}
    ]
  }]
}
```

## Running the Fixture

From the repository root after dependency synchronization, start:

```bash
uv run python examples/external-tools/mcp_server.py --http
```

In another terminal:

```bash
uv run python examples/external-tools/invoke.py examples/external-tools/config.json inventory_lookup '{"item_id":"sample"}'
uv run python examples/external-tools/invoke.py examples/external-tools/config.json inventory_lookup '{"item_id":"sample"}' --allow-this-call
```

The first command reports approval required without calling the operation.
The second deliberately allows the single selected operation in this local
operator harness. It does **not** simulate persisted production approval;
production runs use the existing approval/resume API. To exercise stdio, replace
`http` with `stdio` containing the absolute venv Python path and an argument
pointing to `mcp_server.py`; omit `--http`. The supplied `openapi.json` illustrates
the supported contract; its service URL must be supplied separately.

## Verification and Remaining Limits

Credential-free tests live in `test_external_metadata.py`,
`test_external_http_transport.py`, `test_external_mcp.py` and
`test_external_openapi.py`. They cover official SDK stdio and real loopback
Streamable HTTP, subprocess cleanup, policy denial, resources/prompts, workspace
denial, malformed metadata, typed arguments, timeout, stable idempotency identity,
redirect refusal, bounded responses and DNS rebinding with Host/SNI preservation.
`test_external_bootstrap.py` additionally exercises the actual API lifespan and
worker bootstrap: API-created run, worker queue execution, persisted approval,
then API resume executing the real MCP subprocess operation exactly once in
that successful test path (not an exactly-once guarantee under failure).

Reopened R1/R2/R8 regression coverage additionally includes:

- `test_external_mcp_failures.py`: the actual SDK plus guarded transport with
  only the HTTPCore peer replaced. 307/308/500 are tested for tools, resources and
  prompts: one send, owner survival, and a subsequent successful explicit call.
  Changed reconnect catalogs fail before a second dispatch. Separate discovery
  and invocation deadlines, timeout classification, and subsequent calls are
  checked. Malformed initialization and notifications exercise SDK diagnostic
  paths with plain log capture, for HTTP and a real stdio subprocess.
- `test_external_mcp.py`: real stdio and loopback HTTP tests persist denial,
  approval, resume and audit events for all three binding kinds. Server-side
  counters establish zero invocation before approval and one after resume.
- `test_external_bootstrap.py`: the API-created/Worker-executed/read-only-risk
  binding still waits for its independently configured approval before API
  resume. No separate API/Worker policy loader is required.

These are local regression contracts, not blanket acceptance of the reopened
hardening plan or evidence of remote CI/release verification.

Run the focused suite together with existing tool/context regressions:

```bash
uv run pytest -q tests/unit/test_external_metadata.py tests/unit/test_external_http_transport.py tests/integration/test_external_mcp.py tests/integration/test_external_mcp_failures.py tests/integration/test_external_openapi.py tests/integration/test_external_bootstrap.py tests/unit/test_tools.py tests/unit/test_policy.py tests/unit/test_kb_search_tool.py
```

The SDK's stdio framing can allocate a remote frame before application-level
result bounds run. A hostile subprocess requires OS-level memory/CPU limits;
do not claim this loader is a complete sandbox. HTTP caps apply per exchange,
so long-lived SSE responses exceeding the cap are disconnected. There is no
automatic reconnect-and-replay for writes. Only the first vetted DNS address is
attempted; connection failure is surfaced rather than implicitly retried.
Resource templates, OAuth flows, per-user external credential delegation and
full OpenAPI serialization remain explicit future scope. This feature does not
claim exactly-once external side effects or complete prompt-injection prevention.

## Primary References

- [Official MCP Python SDK v1.30.0](https://github.com/modelcontextprotocol/python-sdk/tree/v1.30.0)
- [MCP security best practices](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices)
- [OpenAPI 3.1.1 specification](https://spec.openapis.org/oas/v3.1.1.html)
- [HTTPCore network backends](https://www.encode.io/httpcore/network-backends/)
- [HTTPX custom transports](https://www.python-httpx.org/advanced/transports/)
