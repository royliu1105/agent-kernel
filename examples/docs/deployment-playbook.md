# Deployment Playbook

## Rollback Policy

Rollback is preferred when a release causes customer-visible errors, sustained
latency regression, failed health checks, or data-integrity risk.

Operators should:

1. Confirm the impacted service and release version.
2. Notify the incident channel.
3. Roll back to the last known healthy release.
4. Verify health checks, logs, and business metrics.
5. Record the decision and follow-up owner.

## Approval Rule

Any action that writes to an external system requires human approval before the
agent continues execution.

## Post-Incident Notes

After mitigation, summarize the timeline, contributing factors, customer impact,
and prevention tasks.
