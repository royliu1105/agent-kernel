# Observability Operations

This is the P0 operational contract for the Python API and worker. It supersedes
historical Day 25-73 notes where those describe unbounded samples, public metrics,
millisecond Prometheus metrics, or an exporter without operation spans. It does
not claim an external collector, alert delivery, or production SLO has been
provisioned. Keep monitoring on a private network.

## Process Integration

Create one `AggregatingMetricsRecorder` per process. Pass the same instance to
`RunExecutionService`, `Retriever`, and any worker-owned execution service or
RAG tool registry. API `/metrics` returns `recorder.prometheus_text()` with
`PROMETHEUS_CONTENT_TYPE`. The `ExposableMetricsRecorder` protocol also accepts
the existing `InMemoryMetricsRecorder` used by tests. Do not use that test
recorder in a long-running production process: it retains every observation.

The worker may expose its recorder through `MetricsHttpServer`. The listener
defaults to loopback, supports only `/metrics`, does not log access, and requires
a monitoring token when binding to a non-loopback address. Create/start once at
worker startup and call `close()` in `finally`. The overlay enables this with
`AGENT_KERNEL_WORKER_METRICS_ENABLED=true`, host `0.0.0.0`, port `9001`.

API integration uses `AGENT_KERNEL_MONITORING_TOKEN`, separate from tenant API
keys. Authenticated deployments must not allow ordinary workspace keys to read
process-wide metrics. The worker token must contain at least 32 ASCII characters.
The scrape file and environment value must contain the same token. Use TLS
between hosts; the provided HTTP targets assume one trusted Compose network.

Each process has independent counters. Scrape every API/worker instance directly,
not a load-balanced service that returns a different process on each scrape.
Use `sum(rate(...))` across replicas. Process restarts reset counters. One API
process per container avoids unsynchronized in-process metrics under a
multi-process ASGI server. Scraping the API does not include worker execution.

## Metric Inventory

`METRIC_DEFINITIONS` is the executable registry. Runtime callers keep the legacy
`*_latency_ms` inputs; only the production exporter converts their values and
bucket boundaries to seconds and exports the names below. Test recorder output
is deliberately compatible with older unit tests. Existing custom dashboards
must migrate; production does not emit duplicate millisecond aliases.

| Exported family | Kind and unit | Labels |
| --- | --- | --- |
| `llm_model_calls_total` | Counter, completed attempts | provider, model, status, error_type |
| `llm_model_call_duration_seconds` | Histogram, seconds | provider, model, status, error_type |
| `llm_tokens_input_total`, `llm_tokens_output_total`, `llm_tokens_total` | Counter, reported tokens | provider, model |
| `llm_estimated_cost_total` | Counter, estimated USD | provider, model |
| `tool_calls_total`, `tool_call_failure_total` | Counter, calls | tool_name, status, error_type |
| `tool_call_duration_seconds` | Histogram, seconds | tool_name, status, error_type |
| `rag_retrievals_total`, `rag_retrieval_failure_total` | Counter, retrievals | model, status, error_type |
| `rag_retrieval_duration_seconds` | Histogram, seconds | model, status, error_type |
| `rag_retrieval_result_count` | Histogram, result count | model, status, error_type |
| `run_queue_errors_total` | Counter, queue errors | operation: enqueue or dequeue |
| `agent_kernel_metrics_dropped_total` | Counter, rejected updates | reason: invalid_metric, invalid_value, invalid_labels, capacity |
| `agent_kernel_metrics_series` | Gauge, retained label combinations | none |

Prometheus supplies `up`; blackbox supplies `probe_success`. These are not
application-emitted metrics. Run outcome metrics, lease backlog, approval wait,
and workspace costs are not fabricated by this registry. In particular model
call failure rate measures attempts, including recovered retries, not final run
failure rate. A tool call may include retries; inspect the runtime event timeline
for attempt-level investigation. Provider errors may lack billed usage; estimated
cost is not an invoice. The explicit failure counters are convenient but the
dashboard ratios use `status="failed"` in the corresponding total counter.

Duration boundaries in seconds: `0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1,
2.5, 5, 10, 30, 60, +Inf`. Result count boundaries: `0, 1, 3, 5, 10, 20, 50,
100, +Inf`. Histograms emit cumulative buckets, `_count`, and `_sum`. No raw
samples or quantiles are retained. Aggregate p95 from buckets, not by averaging
per-instance p95s. Values above the highest finite bucket cannot yield an accurate
tail percentile; tune the versioned buckets to the measured workload.

The default bounds are 1,024 label combinations in total and 32 distinct values
per label key across the registry. Each histogram needs at most 13 finite bucket
counters plus sum/count. There is no growing observation list. One lock protects
updates and snapshot copies; text formatting occurs after releasing it. Metric
names and label keys are registry-only; values are short identifiers. Missing
labels become `none`. Tenant/run/document IDs and arbitrary tool arguments are
not accepted labels. Unknown names, invalid values (including NaN/infinity and
negative increments), credential-like labels, and excess cardinality are dropped
without echoing their contents. Monitor the diagnostic counter before raising
limits. A high-cardinality source must be fixed, not hidden by increasing limits.

## Readiness

`create_readiness_checker(session_factory, env=...)` is created once per process.
`await checker.check()` returns a result with `status_code` and `to_dict()`.
`checker.close()` belongs in application shutdown. `/healthz` remains liveness;
`/readyz` uses this dependency result and is exempt from tenant authentication.
Responses contain only fixed dependency names, required flags, statuses and
sanitized categories. Never return connection strings, exception text, bucket
names, credentials, SQL, or a stack trace.

| Dependency | Default | Probe and meaning |
| --- | --- | --- |
| Database | Always required | `SELECT 1` and zero-row query of `runs`; verifies connection and baseline schema, not all migrations, write rights, pgvector dimensions, or storage capacity. |
| Redis | Optional if `REDIS_URL` is set; otherwise disabled | Real authenticated `PING`; becomes required whenever `AGENT_KERNEL_RATE_LIMIT_REQUESTS>0`. |
| S3 | Required when `AGENT_KERNEL_OBJECT_STORE_BACKEND=s3`; otherwise disabled | Real authenticated `HeadBucket` with the configured bucket, endpoint and region. |

`AGENT_KERNEL_READINESS_REDIS` and `AGENT_KERNEL_READINESS_S3` accept `required`,
`optional`, or `disabled`. An active Redis limiter or selected S3 backend cannot
be downgraded to optional/disabled: startup rejects that configuration. An
auxiliary, unused backend may be explicitly checked as optional. Required but
unconfigured dependencies fail readiness. Missing optional SDKs report
`missing_client`, not success. Required failure returns 503; optional-only failure
returns 200 with `status=degraded`. Blackbox therefore alerts on required failure,
not auxiliary degradation. Inspect the sanitized response for optional failures.

Checks run concurrently, are cached for two seconds, and have a two-second HTTP
deadline by default. At most one in-flight future per dependency is reused across
requests; a hung dependency cannot enqueue unlimited threads. Redis/S3 clients
are lazily created, reused, and closed after outstanding checks finish. Their
socket/connect timeouts are 0.5 seconds; S3 retries are disabled for this probe.
An HTTP deadline cannot terminate synchronous DNS, credential discovery or a DB
driver call. Configure database connect/pool/statement timeouts and bounded AWS
credential-provider timeouts in the deployment too. Readiness cannot certify
PutObject/GetObject/DeleteObject permissions: validate those through an isolated
operator canary and real-backend tests. `HeadBucket` requires suitable bucket
authorization; do not grant broad object access just to make a probe green.

Production Redis and S3 checks need the already-optional `redis` and `boto3`
clients in the image. They are not imported in the SQLite/mock startup path.

## Logs and Traces

Attach `JsonLogFormatter` to all application-owned handlers; `log_event` builds
sanitized records before dispatch. The formatter also sanitizes direct
`extra={"structured": ...}` calls. Only reviewed identifier/count fields survive.
Prompts, messages, arguments, results, documents, unknown fields and all nested
containers are opaque/redacted. Free-text ordinary log messages become
`log.unstructured`; exception text, source snippets and stack traces are omitted,
while the exception class is retained. Event names have an explicit allowlist.
Values are not recursively stringified. Maximum output is 64 fields with bounded
identifier strings. Applications must not put content into a field intended for
a trusted model/tool/provider identifier. This is a structural boundary, not a
general natural-language PII classifier. Do not enable SDK wire/debug logging.

`configure_opentelemetry()` remains opt-in and wraps both OTLP/HTTP and console
exporters with `RedactingSpanExporter`. It creates sanitized SDK snapshots of
attributes, events, links, resource, name, instrumentation scope and status.
Exception messages/stack traces and trace-state are not exported. It does not
mutate a shared SDK snapshot. Do not attach an additional raw exporter that
bypasses this wrapper. Third-party handlers/exporters are not automatically
secured by configuring this package.

Use the operation helper at the execution boundary:

```python
configure_opentelemetry()
with trace_operation("agent.run", trace_id=run.trace_id, attributes={"run.id": str(run.id)}):
    with trace_operation("llm.model_call", attributes={"provider.name": provider_name}):
        response = await provider.generate(request)
```

With telemetry disabled, the helper yields `None` and imports no SDK. The
configured ID generator uses the persisted ID for a new root without inventing a
parent span. Child spans preserve real context; `ContextVar` prevents cross-task
leakage. A different incoming trace is detached for an explicitly supplied run
trace ID. Error handling records only exception category and ERROR status, then
re-raises the original exception. A terminal failure returned as a normal value
must be explicitly marked ERROR by the runtime integration. Wrap actual model
and tool attempts, including retries, not just route dispatch. Approval resume
may create another root operation in the same persisted trace; that is not proof
of one continuously live span across a process restart.

Dev/CI should install `opentelemetry-sdk>=1.39,<2` and
`opentelemetry-exporter-otlp-proto-http>=1.39,<2` so the real SDK tests run. Default
runtime telemetry remains disabled. Real SDK validation has been run on 1.45.2.

## Cost Attribution Boundary

Prometheus estimates are operational, process-local and resettable. Do not use
them for tenant billing. Runtime persists token/cost totals on each Run after
each actual model response, before downstream tool/approval failures can discard
that response's usage. Ownership derives from the persisted Run, never model
arguments. `GET /v1/usage` requires run-read permission and aggregates the
authenticated workspace's Run totals into one bounded response. It is an
all-time summary, not a time-filtered per-attempt accounting ledger. Cross-
workspace denial is tested; monitoring tokens do not authorize this API.

Amounts are adapter-provided estimates. The current OpenAI adapter reports
tokens but leaves estimated cost at zero when pricing is not supplied; that
zero must not be presented as verified free usage or an invoice. The opt-in
live smoke has a separate explicit pricing/budget contract. A future billing
ledger would need per-call identity, pricing version, timestamp, unknown-price
representation, persistence idempotency and invoice reconciliation. Those
stronger financial guarantees are not provided by this operational summary.

## Monitoring Stack

The optional overlay is `deploy/observability/docker-compose.yml`. JSON files are
valid YAML documents and are intentionally checked with native Prometheus tools.
Grafana provisioning pins the datasource UID used by all 14 dashboard panels.

Before starting, provide a dedicated `AGENT_KERNEL_MONITORING_TOKEN`, a matching
`AGENT_KERNEL_MONITORING_TOKEN_FILE`, and `AGENT_KERNEL_GRAFANA_ADMIN_PASSWORD`.
Do not commit secret files or print tokens. The token file must be readable by
the Prometheus container UID (65534); protect its parent directory on the host.
These values are required by Compose, not insecure defaults. The template uses
API port 8000 and worker metrics port 9001; edit the scrape targets if changing
the deployment ports. It requires the API/worker integration described above.

```bash
docker compose -f docker-compose.yml -f deploy/observability/docker-compose.yml \
  --profile observability up -d
```

Grafana is localhost-only at `http://127.0.0.1:3090`, Prometheus at
`http://127.0.0.1:9090`; blackbox has no published port. Grafana anonymous access
and signup are disabled. Images are fixed validation versions, not a claim that
their current security advisories have been reviewed for a release. Pin reviewed
digests in the actual deployment. Prometheus retention is 15 days; protect its
volume and size storage for workload/cardinality. The blackbox probe service must
remain private because its target parameter can access internal URLs.

Alerts cover unreachable API/worker metrics, required readiness failure, probe
exporter outage, model/tool/retrieval error ratios, model p95 latency, metric
rejections and queue errors. Failure ratios have a minimum 20-event/5-minute
volume guard; latency requires the same volume. Thresholds are starting policy,
not a workload-specific SLO. Missing application metrics before the first event
are expected; do not interpret them as zero failures. `up` and probe alerts cover
missing scrape targets. Configure Alertmanager separately for notification
routing; these rules evaluate but do not deliver pages by themselves.

When alerts fire:

1. Target/probe down: verify private networking, token file access/value, listener
   enablement and target ports before investigating application failures.
2. Not ready: inspect `/readyz`, then the required backend and its connection,
   schema or permissions. Do not disable the requirement to restore green status.
3. Model/tool/retrieval errors: inspect authorized run timelines and correlated
   traces. Compare retry/fallback outcomes before declaring an end-user outage.
4. Latency: compare provider/model buckets and traffic volume; queue time is not
   included in this model-call histogram.
5. Dropped metrics: check reason labels, accidental IDs/content in labels, and
   model/tool churn. A capacity alert means monitoring coverage is incomplete.
6. Queue errors: verify Redis availability and durability/fallback behavior; the
   database remains the task source of truth, not this metric.

## Verification

The default tests cover bounds, concurrent updates, cumulative histograms,
redaction bypasses, readiness failure/recovery/configuration and HTTP token checks.
Real SDK tests verify exported redaction, persisted IDs and parent relationships.
Native Prometheus validation is opt-in because it uses Docker:

```bash
AGENT_KERNEL_TEST_PROMTOOL=1 uv run pytest -q \
  tests/integration/test_observability_prometheus.py
```

This checks exposition with `promtool check metrics`, scrape config with
`check config --syntax-only`, every dashboard PromQL as a recording rule, and
all nine alerts using the checked-in firing/pending/recovery/low-volume cases.
Syntax-only scrape validation does not prove connectivity or readable secret
files. Inspect `/targets` after deployment and perform a controlled failure drill.

### Local Verification Record

2026-11-13, uncommitted P0 implementation:

| Check | Result |
| --- | --- |
| Observability unit tests, real SDK integration, native promtool tests and the parent-owned runtime tracing integration | 51 passed; includes a real loopback metrics listener and all nine alert scenarios. |
| Scoped Ruff and mypy | Passed; mypy checked 20 source/test files. |
| Prometheus v3.5.0 | 3 native integration tests passed: exposition, config/alert tests, all 14 dashboard queries. No abbreviated-unit lint exemption; production histograms use seconds. |
| Blackbox exporter v0.27.0 `--config.check` | Passed against the checked-in readiness module. |
| Base Compose plus monitoring overlay `config --quiet` | Passed with non-secret syntax-validation values; not a live scrape/auth check. |
| Git whitespace check | Passed within this task's paths. |

The follow-up integrated rehearsal on 2026-11-13 also passed: Grafana 12.1.0
loaded the provisioned dashboard and datasource, authenticated API/Worker
scrapes and readiness probes were healthy, and all 14 panel queries succeeded.
Chromium login and upper/lower panel rendering were inspected without page
errors. `tests/integration/test_monitoring_deployment.py` adds three opt-in
deployment checks and is run by the CI Compose job after HTTP smoke.

A real Worker stop drove `AgentKernelTargetDown` through pending to firing after
the configured two-minute hold. Database outage produced readiness HTTP 503 and
probe failure. With Worker restart supervision, database recovery restored the
Worker without a manual Worker start, and the target alert cleared. The full
record and repeat commands are in [hardening verification](hardening-verification.md).
Earlier download failures cleared on retry without proxy changes. No Alertmanager
notification delivery, external hosted deployment or production SLO is claimed.

References: [Prometheus exposition](https://prometheus.io/docs/instrumenting/exposition_formats/),
[rule tests](https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/),
[Grafana provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/),
[OpenTelemetry SDK](https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.html).
