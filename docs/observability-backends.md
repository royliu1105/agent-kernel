# Observability Backends and SMTP

Implementation/acceptance status lives in the
[completion ledger](observability-completion-plan.md). This runbook is not proof
that its deployment checks or external email gate passed. The existing
[operations guide](observability-operations.md) remains authoritative for metrics,
redaction, readiness and operator response.

For the default local runtime, use `make docker-up` and the
[Docker-only guide](docker-local.md). It composes the profiles below into one
persistent stack including Web/PostgreSQL/Redis. The manual Compose commands
below remain useful for custom deployments, not a second local startup default.

## Deployment Contract

```text
API/Worker -- sanitized rotating JSON files --> Alloy --> Loki --> Grafana
API/Worker -- redacted OTLP/HTTP spans -------> Alloy --> Tempo --> Grafana
API/Worker -- private metrics --> Prometheus --> Alertmanager --> SMTP
                                                              --> Mailpit (local test only)
```

The additional Compose overlay is `deploy/observability/full-stack.compose.yml`.
It composes with the base project and the existing metrics overlay. The API and
Worker image build enables the optional `observability` extra; the base image
does not silently depend on development-only SDK installation. Existing routes,
storage and model behavior are unchanged. All new images are fixed versions,
not `latest`; this does not replace a release dependency/security audit.

Alloy is the collector for both signals; a second OTel Collector is unnecessary
for this profile. It reads only a read-only named application log volume, not
Docker's API socket, host `/var/log`, other projects, task objects or credentials.
API and Worker use different filenames and one writer per file. Its root UID is
needed to read private root-owned application files in this volume; it has no
extra Linux capabilities or privilege escalation and does not mount the host root.

Loki and Tempo are single-process, local-volume backends. This is a reproducible
trusted single-host profile, not distributed/HA storage, cloud backup, tenant
isolation or a production SLO claim. A production installation can instead point
the collector and Grafana to existing managed backends.

## Local SMTP Capture

Mailpit requires no account, password or real mailbox. It receives actual SMTP
messages and presents a web inbox. The local overlay has no relay configuration
and publishes only its HTTP UI to loopback, never SMTP to the host. All local
addresses end in `.invalid`; it cannot establish delivery to a real inbox.

Prepare a private directory such as `.agent-kernel/telemetry-secrets` (mode 0700).
Set the following outside Git, using the existing metrics credentials if present:

```text
AGENT_KERNEL_MONITORING_TOKEN=<dedicated random token, minimum 32 ASCII characters>
AGENT_KERNEL_MONITORING_TOKEN_FILE=<absolute path to matching token file>
AGENT_KERNEL_GRAFANA_ADMIN_PASSWORD=<random local Grafana password>
AGENT_KERNEL_ALERTMANAGER_CONFIG_FILE=<absolute repo path>/deploy/observability/alertmanager.local.json
AGENT_KERNEL_SMTP_PASSWORD_FILE=<absolute path to empty local-test file>
```

Container UIDs must be able to read the mounted secret files. A 0644 file inside
an owner-only 0700 host directory is supported by this local bind-mount profile.
Use platform secret management and reviewed ownership for deployed installations.
Do not print or commit their contents. Do not reuse a workspace API key as a
monitoring token. The local SMTP password file is empty and is not an SMTP account.

```bash
docker compose -f docker-compose.yml \
  -f deploy/observability/docker-compose.yml \
  -f deploy/observability/full-stack.compose.yml \
  -f deploy/observability/local-mail.compose.yml \
  --profile observability up --build -d \
  api worker prometheus blackbox grafana loki tempo alloy alertmanager mailpit
```

Do not run this over unrelated containers or point it at the active local
experience database. The base Compose profile has its own PostgreSQL/object volumes.
Choose another Compose project/ports when an existing stack is running. The
rehearsal command below does this automatically and owns only its random project.

| Default loopback endpoint | Purpose |
| --- | --- |
| `http://127.0.0.1:3090` | Authenticated Grafana; Explore data sources `Agent Kernel Logs` and `Agent Kernel Traces`. |
| `http://127.0.0.1:9090` | Prometheus targets/rules; additional telemetry scrape job. |
| `http://127.0.0.1:9093` | Operator-only Alertmanager groups/silences. |
| `http://127.0.0.1:8025` | Local Mailpit inbox; not an external mailbox. |
| `http://127.0.0.1:3100` / `:3200` | Loki / Tempo diagnostic APIs, no built-in tenant authentication in this profile. |
| `http://127.0.0.1:4318/v1/traces` | Alloy OTLP/HTTP receiver for host-local producers. |

Override ports with `AGENT_KERNEL_{GRAFANA,PROMETHEUS,ALERTMANAGER,MAILPIT,LOKI,TEMPO,OTLP}_PORT`.
Only Grafana has login protection here. Loopback endpoints trust all local users;
do not publish these ports or forward them to an untrusted machine. For a shared
host/network, remove diagnostic port mappings and provision authenticated TLS
ingress. The backend data is cross-workspace and must remain operator-only.

## Log and Trace Investigation

In Grafana Explore, select `Agent Kernel Logs` and query:

```logql
{job="agent-kernel"} | json | run_id="<run UUID>"
```

The stored `trace_id` has a derived-field link to `Agent Kernel Traces`. The
trace data source also provides a reverse log query. Look up a known Run's trace
ID, not a fabricated span. Inspect `agent.run`, `llm.model_call` and `tool.call`.
Approval continuation may contain multiple roots with the same persisted trace
ID; this is not one continuously running span across restarts. The application
does not claim automatic HTTP-to-queue distributed context propagation for every
framework/library operation. Native runtime operation correlation is the scope.

`AGENT_KERNEL_LOG_FILE` is optional and absolute. Default file bounds are 10 MiB
and 5 rotated backups per process; configure `AGENT_KERNEL_LOG_MAX_BYTES`
(1024-104857600) and `AGENT_KERNEL_LOG_BACKUP_COUNT` (1-20). Zero is rejected.
The same safe formatter applies to stderr and files, including Uvicorn. New files
are 0600. Do not write raw SDK wire output or arbitrary strings into these files.
Rotation requires one writer per path; multiple replicas need distinct files.
The byte limit is a rotation threshold, not an OS-enforced quota: a single
oversized, still formatter-bounded record can exceed that threshold. Reserve
headroom rather than treating `max_bytes * backup_count` as an exact disk cap.
These limits cover the application file sink only. Docker also captures stdout
and stderr. The default `deploy/local.compose.yml` sets the `local` logging driver
to 10 MB / 3 files per container; custom deployments must set their own policy.
Backend retention and source rotation alone do not bound Docker container logs,
volumes, or total host disk consumption.

Alloy discovers the two exact paths once per second, including files created
after the collector starts, and keeps file positions in its volume. It tails the active file and follows
rotation while running. Rotation during a long collector outage can discard
unread old files; resumption is not a lossless audit guarantee. Loki/Tempo retain
72 hours by asynchronous backend retention, not an exact deletion deadline or
disk-space quota. Monitor disk capacity. Mailpit keeps at most 200 messages and
3 days. Stop with `docker compose ... stop`; `down` removes containers/network,
and **`down --volumes` also deletes stored telemetry**. Use the latter only for
explicitly disposable rehearsals, not ongoing evidence.

Alloy limits trace processing memory to 128 MiB, batches up to 512 spans and
queues 256 export requests with bounded retry. The SDK uses its bounded batch
queue and exports all recorded spans by default; there is no tail-sampling
service in this profile. A prolonged exporter outage, queue exhaustion, host
crash or source-file rotation can lose data. Runtime success is independent of
successful telemetry export; a persisted Run timeline remains separate evidence.

## Real SMTP Setup

Do not invent an SMTP account. Once the maintainer supplies an approved service,
sender and recipient, create a private copy of
`deploy/observability/alertmanager.smtp.example.json` outside Git. Set its actual
host/port, username, from/to addresses and a separate password/authorization-code
file. Keep TLS required and certificate validation enabled. Port 587 STARTTLS is
the example; select the provider's documented TLS settings, not guessed values.
Set `AGENT_KERNEL_ALERTMANAGER_CONFIG_FILE` to this private config and
`AGENT_KERNEL_SMTP_PASSWORD_FILE` to its credential file; omit the Mailpit overlay.

Changing notification recipients is an external communication boundary. Confirm
the intended destination before a real test. Do not send task input, secrets,
documents or raw exception messages. The supplied template contains only fixed
alert metadata, target identifiers, summary and times. The production defaults
group by alert name/job, wait 30 seconds, regroup after 5 minutes and repeat after
4 hours. Local rehearsal uses 5 seconds/10 seconds/1 hour. `send_resolved` is
explicitly enabled for email.

Acceptance requires both firing and resolved messages at the intended inbox,
including spam/quarantine checks. An SMTP 250 response is not inbox evidence.
Alertmanager retries failed notification attempts, but delivery is not exactly
once or guaranteed indefinitely. The same broken SMTP route cannot report its
own outage reliably: inspect Prometheus/Alertmanager independently and provide
an independent escalation path for a real on-call deployment.

## Reproducible Rehearsal

```bash
uv sync --dev --extra observability
uv run python scripts/observability_rehearsal.py
```

This builds real API/Worker images and creates a random
`agent-kernel-observability-<hex>` project, private temporary credentials, isolated
PostgreSQL/Redis/object/log/telemetry volumes and loopback ports in the 25000-39000
range. It runs existing HTTP coverage plus the opt-in full-backend tests, then
removes only its own project and volumes in `finally`. No model credentials are
inherited. Keep Docker running; failures are failures, not silently passed skips.
Do not use Ctrl-C repeatedly during cleanup. If the host crashes, inspect the
exact random project before explicitly removing its resources.

The script first runs native configuration validators and alert-rule tests.
The test suite verifies actual stored logs/traces through Grafana, file rotation, collector and
backend recovery, a real Worker scrape fault, SMTP receiver failure/retry and
firing/resolved messages in Mailpit. These are local deployment tests, not real
provider quality, external inbox, cloud capacity or long-duration retention tests.

## Troubleshooting

- Empty logs: check the per-process file setting, read-only mount ownership,
  safe JSON output, Alloy positions and Loki readiness; do not enable raw logging.
- Missing traces: confirm the runtime SDK extra, telemetry enabled flag,
  service name and receiver endpoint; allow batch flush time, then query the Run's ID.
- Empty Grafana data source: inspect authenticated data source health and internal
  service DNS, not only the Grafana login page.
- Firing without mail: inspect Alertmanager's selected receiver, SMTP delivery
  counters and local inbox; local receipt is not evidence of external delivery.
- Repeated emails: compare group key, repeat interval and collector/deployment
  restarts; notification grouping is not an exactly-once event bus.

Implementation references: [Alloy file collection](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.file/),
[Loki configuration](https://grafana.com/docs/loki/latest/configure/examples/configuration-examples/),
[Tempo configuration](https://grafana.com/docs/tempo/latest/configuration/),
[Alertmanager SMTP](https://prometheus.io/docs/alerting/latest/configuration/),
[Mailpit](https://mailpit.axllent.org/).
