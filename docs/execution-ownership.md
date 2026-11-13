# Execution Ownership and Recovery

Post-v1.0 P2 contract, superseding lease-integration gaps in the historical
[Day 59-63 summary](durable-execution-summary.md). See the
[canonical plan](capability-hardening-plan.md) for acceptance status.

## Claim and Fencing

Every `RunExecutionService.execute` and `resume` acquires a database lease,
including direct calls, queued workers and API approval resume. Queued runs and
waiting-approval runs have separate expected starting states. All claim/state/
event writers serialize on the Run row; an unreleased-lease partial unique
index adds a database invariant. PostgreSQL is the multi-worker target. SQLite
serializes writes and remains a local/test option, not a high-throughput backend.

Lease TTL defaults to 60 seconds, with renewal every TTL/3 using an independent
SQLAlchemy session. No Session is shared between execution and heartbeat tasks.
Run state, usage, tool results and audit events require the current unexpired
token. Lost ownership cancels execution and fences later writes. Cancellation
revokes the lease atomically; a late model/tool result cannot overwrite canceled
state. Repeated claim failures do not count as worker execution failures.

The heartbeat uses the async event loop. Tool/provider implementations must not
block it with CPU work or synchronous I/O; offload that work or isolate it in a
process. A stalled event loop can lose ownership, which is preferable to a late
writer silently succeeding. Database outages fail closed.

The built-in `kb_search` offloads synchronous retrieval to a thread and creates
and closes its read-only database Session there. Its tool deadline cancels the
await and prevents a late result from completing the Run; it does not kill a
Python thread or undo an embedding request. Underlying database/provider I/O
still needs finite timeouts. The deadline, lease-renewal and late-result contracts
are exercised together in `test_rag_execution_deadlines.py`.

## Approval and Side Effects

Approval decisions lock the parent Run and recheck persisted state. Repeating
the same decision returns the original reviewer/note/timestamp without a second
event. An opposing decision returns a conflict. Concurrent resume requests have
one lease winner and execute the persisted tool arguments once.

Unreleased native approval continuation adds private, versioned
`runs.execution_checkpoint` state (migration `0019_execution_checkpoint`).
Both reads and writes require the active lease. The saved model history, batch
cursor and budgets allow a new executor to continue without replaying earlier
tools. The original provider route and tool contracts must still match; legacy
native approvals with no checkpoint fail closed. Explicit-tool approvals retain
their tool-only behavior. See [bounded execution](specs/bounded-native-execution.md).

Database fencing is **not exactly-once external side effects**. Cancellation or
process death cannot undo an already accepted remote request. The stable
persisted `tool_call_id` is available as downstream idempotency context; use an
explicit reviewed OpenAPI idempotency header when supported. A lease token is
never a downstream idempotency key. Writes are not automatically retried.

`agent-kernel-worker --recover-stuck` locks each run and rechecks expiry, so a
stale scan cannot fail a renewed/replaced owner. Expired running/resuming work
is failed with `worker_lease_expired`, retaining tool state for review. Expired
queued claims are released without losing the queued run. Recovery never
blindly repeats uncertain external work. Unexpected task cancellation immediately
expires the lease before canceling and awaiting the operation, retaining the
unreleased record for this recovery path. Even a provider/tool that suppresses
`CancelledError` cannot persist a late result or renew the invalidated lease.
If persisting invalidation fails, the execution session also revokes local write
ownership before awaiting canceled work; the error propagates and the durable
lease remains eligible for ordinary expiry/recovery. This does not fence an
unrelated process without a successful database write; its lease token and
expiry rules still apply.
Cancellation cannot forcibly terminate arbitrary Python code; a non-cooperative
tool still needs process-level termination or an external execution sandbox.
For bounded native calls, the runtime stops waiting at its active deadline and
discards cancellation-resistant late adapter results. It fails/fences the run
without keeping its heartbeat alive; this does not stop a remote side effect or
force-kill that adapter code. Such abandoned responses have unknown billing.

## Queue and Session Boundaries

Database run state remains authoritative. Redis contains bounded UUID hints;
API enqueue happens after commit, and Workers poll the database every pass even
when hints are lost, duplicated or Redis is unavailable. No queue ACK implies
completion. PostgreSQL owns coordination and fencing, not a second Redis lock.

Runs are independent. There is no conversation/session entity or cross-run
ordering guarantee. Same-session serialization is explicitly deferred until a
session identity and ordering contract exist. Applications needing ordered
conversation mutation must not launch concurrent runs against mutable shared
conversation state without their own serialization.

## Verification

`tests/integration/test_execution_ownership.py` exercises independent processes,
stale result/event writes, heartbeat and concurrent approval/resume against
SQLite and real PostgreSQL. `test_stuck_run_recovery.py` covers recovery without
replay; `test_execution_cancellation.py` covers late results after cancellation,
recovery and owner replacement, including cancellation-resistant operations.
`test_operational_scope.py` covers queue-outage database recovery and
workspace-authorized operational queries. Real-backend tests are mandatory in
CI and require explicit disposable backend settings locally.
