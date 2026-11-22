# Mock Troubleshooting Showcase

Status: **local operator demo** (2026-11-23). Uses mock models and a
credential-free MCP TraceId log tool. Not a real log platform, not paid-provider
acceptance, and not PV1–PV6 pilot closure.

Goal: one reproducible chain that shows **log tool → fault KB → evidence /
refuse-when-thin**, aligned with the resume “线上排障” story shape.

```text
make docker-showcase-up
  → index examples/docs/troubleshooting/*
  → TRACE-OK → showcase_trace_logs → fingerprint + Redis error spans
  → KB search hits redis_timeout_checkout_cart runbook
  → TRACE-THIN → evidence_sufficient=false (refuse root cause)
  → evidence JSON under .agent-kernel/showcase-evidence/
```

## Prerequisites

- Docker stack with the **showcase overlay**: `make docker-showcase-up`
- No paid keys and no company log-platform credentials

Ordinary `make docker-up` does **not** load showcase MCP tools.

## One-command rehearsal

```bash
make showcase-troubleshooting
```

This runs `scripts/showcase_troubleshooting_demo.sh` via the Docker API
container. It:

1. Creates an Agent and a troubleshooting KB.
2. Uploads / ingest / chunk / indexes:
   - `examples/docs/troubleshooting/redis-cart-timeout.md`
   - `examples/docs/troubleshooting/insufficient-evidence.md`
3. Searches the KB for fingerprint `redis_timeout_checkout_cart`.
4. Queues an explicit-tool Run for `showcase_trace_logs` with `TRACE-OK`
   (policy `allow`, no approval gate).
5. Asserts structured tool output: sufficient evidence + Redis cart fingerprint.
6. Queues a second Run for `TRACE-THIN` and asserts insufficient evidence.
7. Writes sanitized evidence under `.agent-kernel/showcase-evidence/`.

## Fixture TraceIds

| TraceId | Meaning |
| --- | --- |
| `TRACE-OK` | Denoised spans include checkout-api → redis-cart timeout |
| `TRACE-THIN` | Gateway-only span; refuse root cause |
| anything else | Not found; refuse root cause |

Tool binding name: `showcase_trace_logs` (MCP remote `trace_logs_lookup`).
Server: `deploy/local-showcase-tools/troubleshooting_mcp_server.py`.

## Workbench (optional manual)

With the showcase overlay up:

1. Open `http://127.0.0.1:3000`, continue anonymously.
2. Create an agent; create a KB; upload the two troubleshooting markdown files;
   Prepare for retrieval (or stepped ingest/chunk/index).
3. Create a run whose task mentions `TRACE-OK`, model `mock:echo` (or paid
   DeepSeek if you intentionally switch profiles), and use Advanced / explicit
   tool wiring from CLI if the UI path is create-run-only — the automated script
   remains the supported closed loop.
4. Prefer `make showcase-troubleshooting` for a deterministic check.

## Boundaries

- Inventory approval demo (`make showcase-happy-path`) remains separate; both
  tools share the same showcase overlay `tools.json`.
- Do not claim this replaces an internal log platform MCP.
- Mock model answers are not quality evidence; the gate here is tool + KB +
  refuse-when-thin behavior.
