# Bounded Native Execution

Status: accepted within scope after local and remote verification (2026-11-14),
implementation `cb25484`; unreleased. Canonical progress and exact CI evidence are N1-N5
in [capability hardening](../capability-hardening-plan.md).

## Scope

Extend the existing leased runtime, not replace it with another orchestration
framework. Preserve explicit-tool runs, model routing before native history,
workspace authority, policy/approval checks and conservative crash recovery.

- Repeat model -> tools -> model until a terminal answer or a bounded failure.
- Execute multiple calls in a model response serially, in response order.
- Preserve call IDs, prior results and provider-native reasoning history.
- Pin the chosen provider/model once native history exists; no cross-provider
  continuation fallback and no automatic replay of completed/uncertain writes.
- Persist an internal checkpoint before entering approval wait. Reopening the
  database and constructing a new executor must still continue the conversation.
- Keep the checkpoint out of public Run schemas, logs, traces and metric labels.
  It contains sensitive task/history data and needs the same access/backup
  controls as persisted tool arguments/results.

## Bounds and Recovery

Use trusted server configuration for model-attempt/tool-call limits, active-run
time, transcript bytes and observed token/cost budgets. Run input cannot raise
these limits. Persist counters/limits across approvals; a restarted executor may
tighten, not expand, a stored budget. Approval waiting time is not active work.
Output-token requests must be bounded too; observed token/cost limits are not a
guarantee against provider billing for failed or in-flight requests.
The default OpenAI adapter has no pricing table and reports zero estimated cost;
its monetary ceiling is not real billing enforcement. Token/time/call bounds
still apply, and adapters reporting nonzero costs are checked against that budget.

Reject missing, duplicate or inconsistent call IDs before side effects. Each
tool still passes schema validation and current policy. A rejected approval
ends the run without calling its tool or the model. An approved native call
continues the pending batch and then the model; explicit-tool approval behavior
remains tool-only. Legacy native approvals without a checkpoint fail closed with
an actionable error rather than inventing lost history.

All checkpoint writes use the existing lease/fencing guard. Concurrent resume
has one owner. Process death during uncertain work remains a failed/reviewable
run, not an automatic retry of the whole checkpoint. Sequential batches can have
partial external effects if a later call fails; this is not an atomic transaction.

An active deadline cancels the adapter task without waiting indefinitely for
code that suppresses cancellation, then fails/fences the run. Late results cannot
write checkpoints, usage or tools. This is not process isolation: an uncooperative
in-process adapter may keep running until it exits or its process is stopped.
Normally returned valid usage is recorded before enforcing the elapsed-time
limit; usage from abandoned late responses is unknown, not a claim of zero cost.

## Retry Contract

Bound attempts and delays; use exponential backoff plus jitter and validated
Retry-After delta-seconds or HTTP-date. Never sleep less than a valid server hint.
Hints beyond the configured wait budget fail explicitly rather than sleeping
indefinitely or sending early. Sleep is asynchronous/cancellable and lease
heartbeat continues; ownership/budgets are checked before every subsequent call.
Initial fallback also observes the final failed attempt's cooldown/hint. It
cannot bypass throttling by immediately selecting another model.
Only eligible transient errors retry. Permanent failures, denied tools and
side-effecting or approval-protected tools never gain retries from this change.

## Required Evidence

- Multi-round read-only chain, ordered multi-call batch and terminal answer.
- Endless model/tool requests stop at limits without an extra side effect.
- Missing/duplicate IDs, invalid history, unknown/denied tools fail safely.
- New-session/new-executor approval continuation retains original task, every
  completed result and native reasoning; multiple approval rounds work.
- Rejection, repeated resume, concurrency, cancellation, expired ownership and
  budget persistence cannot duplicate a completed external write.
- Checkpoint migration/legacy compatibility and ownership guards on real
  PostgreSQL; API workspace boundary remains in force.
- Deterministic delay tests cover caps, jitter, valid/invalid Retry-After,
  permanent errors, cancellation and no tool replay during model retries.
- Update operator guides, regression scenarios and actual OpenAI wire fixtures;
  do not weaken request/history assertions merely to make old tests pass.

No paid provider call is authorized by this spec. Full local and remote gates
are separate statuses; fixture evidence is not live-model quality evidence.

`make release-eval` includes credential-free bounded-loop, approval wire,
backoff and deadline-edge contracts on isolated PostgreSQL. Start the dedicated
test service first. API and Worker share the default route factory
so HTTP approval continuation can resolve the provider selected by the Worker.
