# Runbook: insufficient Trace evidence

## When to refuse a root cause

Refuse a definite root cause when any of the following is true:

- The TraceId is unknown / returns no spans.
- Only an edge-gateway accept span exists (no downstream error body).
- Denoised notes say evidence is insufficient.

## Safe reply pattern

State what was observed, list missing evidence (downstream spans, error
fingerprint, service name), and ask for a fuller TraceId export. Do not invent
services, Redis faults, or database culprits.
