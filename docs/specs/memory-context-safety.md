# Bounded Untrusted Memory Context

Contract version: **1**, introduced by the unreleased CF1 minimal repair.
Implementation is in the working tree; verification and remaining acceptance
gates are recorded in the [CF1 repair record](../reviews/2026-11-14-cf1-minimal-repair.md).
The [follow-up ledger](../reference-follow-up-plan.md) owns CF1 status.

## Trust Model

- Memory is explicit, workspace-shared data, never an instruction or permission.
  Authenticated workspace ownership is authoritative; business `scope` labels
  such as `user:roy` are filters, not per-user ACLs. Members with memory-read
  permission can read that workspace's memory, regardless of those labels.
- Owner/admin/operator may write/delete memory; viewer may read. Write access
  does not make stored content trusted. Operator also has approval-review rights:
  this is not independent two-person authorization. Auth-disabled local access
  is trusted single-user operation, not tenant isolation.
- A constant SYSTEM message named `memory_policy` establishes the handling rule.
  A separate USER message named `memory_context` contains a versioned JSON
  envelope with `version: 1`, `trust: "untrusted"` and `items`. Each item includes
  ID, type, scope, source Run ID, confidence and content. Values are serialized
  as data; forged delimiters and role claims are not interpolated into policy.
  Empty recall produces the same envelope with an empty items array.
- The actual task follows this data message. This intentionally does not invent
  a TOOL result without a matching provider call ID. OpenAI Responses transport
  tests verify SYSTEM/USER/USER placement, not only internal message metadata.
- Trusted tool metadata, static policy, persisted approval and original tool
  arguments remain the authorization boundary. A model proposing a write cannot
  authorize it. Memory provenance/confidence are descriptive, not authority.

This reduces inappropriate instruction priority; it does not prove a model
will always ignore malicious text or return a correct answer. A model may still
propose an allowed-but-unwanted tool or produce misleading output. Tool scopes,
least privilege, approval review and PV3 live behavior evaluation remain necessary.

## Fixed Admission Limits

| Input | Limit |
| --- | --- |
| Memory `content` | 16 KiB compact JSON, UTF-8 bytes |
| Memory `metadata` | 4 KiB compact JSON, UTF-8 bytes |
| Each content/metadata JSON tree | Depth 16 from root depth 0; 4096 visited values/keys |
| `input.memory.scopes` | 1-8 strings, each 1-255 characters |
| `input.memory.types` | Optional, at most 4 valid MemoryType entries; empty means no matches |
| `input.memory.limit` | Strict integer 1-20; default 10; bool/string values rejected |
| Rendered memory envelope | At most 20 items and 64 KiB UTF-8 including provenance |

Limits use `ensure_ascii=False`, compact separators and finite JSON numbers.
Quotes/control-character escaping counts toward bytes. Non-JSON Python values,
excessive width/depth and non-finite numbers are rejected. These are semantic
JSON/context limits, not PostgreSQL physical-storage sizes or token estimates.

API schemas reject invalid memory writes/selections with HTTP 422 before
persistence. Unknown selection fields are rejected rather than silently ignored.
Request-validation responses retain `detail[].loc`, `msg` and `type`, but omit
raw `input` and exception `ctx`. ASCII-safe JSON error encoding also ensures
rejected non-finite numbers or lone Unicode surrogates do not turn a 422 into a
500. This validation-error response contract applies across the API.
Repository writes independently validate content/metadata; runtime
revalidates selections from existing Runs before retrieval. Recall performs one
workspace-scoped SQL query, ordered by newest creation time then ID descending,
with one global limit. It does not issue an unbounded query per input scope.

Existing oversized rows remain inspectable/deletable. If selected, invalid rows
or excessive aggregate context fail the Run before any model/tool call. There
is no silent truncation or automatic deletion. Reduce the selection or explicitly
replace the data after review. Existing execution-history/token budgets still apply.
HTTP/proxy body-size limits are a separate deployment concern: this validation
occurs after JSON parsing and is not a general denial-of-service defense.

## Checkpoint Compatibility

- New memory-bearing NativeState checkpoints record `memory_context_version=1`.
  Their saved requests contain the exact constant policy and bounded data
  envelope; message trust/version/item IDs and output provenance must agree.
- Resume validates this boundary before executing an approved pending tool or
  calling a provider. Legacy memory checkpoints (including empty recall), a
  forged version with SYSTEM memory, missing policy, malformed/oversized data,
  or inconsistent IDs fail closed with `unsupported_memory_checkpoint`.
  Invalid overall checkpoint structure/unknown versions can instead produce
  `invalid_execution_checkpoint`.
- Valid legacy checkpoints without memory remain compatible. Existing approval,
  provider/tool-contract, lease and execution-budget checks are unchanged.
- No automatic legacy conversion, replay, or refetch occurs. Safe version-1
  context remains the original snapshot across resume, even if memory rows were
  subsequently deleted. Deleting a memory is not erasure from checkpoints,
  earlier provider requests or backups; retention/erasure needs separate review.
- These checks detect unsupported formats and structural inconsistency, not
  cryptographic tamper protection against a database administrator.

There is no schema migration or active-data rewrite. Before deploying, review
pending memory-bearing approvals and possible earlier side effects. Stop all
old executors, back up, and replace API/Worker together. Do not mix versions or
manually stamp old checkpoints as version 1. A blocked legacy Run requires a
deliberately reviewed new Run; never blindly replay an earlier external write.
Future policy/envelope changes require a deliberate continuation-version decision;
the exact policy is part of this saved-context contract, not mutable prompt text.
See [upgrade policy](../upgrade-migration-policy.md).

## Non-Goals and Evidence

No automatic memory extraction, summaries, semantic recall, RRF, new policy
engine, sandbox, per-user ACL, or live-model safety certification is introduced.

Maintained regressions:

- `tests/unit/test_memory_context_contract.py`: byte/shape/selection bounds,
  forged delimiters, exact UTF-8 boundaries, OpenAI wire placement.
- `tests/integration/test_memory_context_security.py`: deny/approval/reject,
  effect counters/events, reopened-session resume, deleted memory snapshots,
  unsafe checkpoints, legacy no-memory compatibility and external result data.
- `tests/unit/test_memory_retrieval.py`: one bounded newest-first recall query.
- `tests/unit/test_api_auth.py` and
  `tests/integration/test_memory_eval_isolation.py`: role and workspace boundaries.

All model responses in this evidence are deterministic fixtures; HTTP transport
is mocked, not a paid service. Local regression results do not close CF2 or PV1-PV6.
