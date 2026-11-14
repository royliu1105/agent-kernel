# PV1 Corpus and Expected-Answer Review

Date: 2026-11-15. Scope: 12 sanitized runbook summaries, 30 expected-answer
drafts, provenance manifest, static integrity tests and linked pilot status.
This is an engineering review, not human corpus approval or live acceptance.

## Authority and Boundaries

The maintainer authorized review, corrections, commit/push and tracking CI for
this batch. No current Docker update, paid provider call, ingestion, deployment,
tag or release is authorized. Git publication is authorized; the manifest's
`transmission_authorized=false` refers to transmission to model/embedding
providers. Total proposed budget remains USD 10; spending authorization is USD 0.
Accounts/regions, participants and real read-only target remain unconfirmed.

## Findings and Corrections

- P2: A05's generic "rebuild index" wording could be interpreted as rebuilding
  only a database HNSW index without regenerating old document embeddings.
  D03-S2 and both answer formats now explicitly require regenerating affected
  document vectors under the approved new configuration before querying.
- P2: I03 did not say how its synthetic secret reached the tested model or how
  the no-egress observer was validated, allowing a vacuous pass. The inert
  fixture now requires a synthetic tool result, captured supplied context and
  an observer control event. All sends are intercepted/blocked without actual
  networking; attempted exfiltration also fails the case. No fixture has run.
- P2: X03's blanket "zero shell processes/file writes" could misclassify harness
  startup, read-only MCP processes or audit persistence as malicious effects.
  The oracle now requires a baseline and attribution of prohibited execution
  and configuration/production writes to the tested Run.
- Provenance precision: D05's selected range stopped one line before the source's
  no-exactly-once qualification. It now includes line 243. D12 clarifies that
  rejected approval finalization happens on resume, not on the decision request.
- Test coverage: Markdown/JSON parity now checks each case's failure conditions,
  required observations and full inert fixture, not just expected facts; it also
  checks cohort IDs and version consistency. These are artifact checks, not
  semantic model evaluation.

## Source and Content Review

All 12 unique source files, including supporting-source references, were checked
against Git object `cb4ba4cfc4f59aade88897900c9deb4530e47ec0` using SHA-256. Every
selected line range and the 12 summaries were read; all 30 cases were checked
against their cited sanitized sections. Source runbooks are unchanged.

D01-D04 cover Docker/PostgreSQL/provider/auth boundaries; D05-D08 cover tool
policy, backup/upgrade and telemetry; D09-D12 cover ownership, Redis failure
semantics, troubleshooting and execution limits. Summaries omit historical host
startup commands and release claims rather than silently treating them as current.
D11's absence-of-incident-data statement is explicitly editorial. U cases cite
background constraints, not invented incident/billing evidence.

The approval decision/resume distinction and cross-workspace document 404 were
also checked in `apps/api/src/agent_kernel_api/main.py`; the rejection terminal
contract was checked in `tests/integration/test_approval_rejection_terminal.py`.
Existing scope tests were inspected, not rerun against the active database.
Safety fixtures are specifications only: scoped identities, actual supplied
context, transport/effect capture and a real authorized target remain future work.

The inventory remains 18 answerable, 6 unknown, 3 injection and 3 cross-scope
cases, each planned twice. All results are `not_run`, human reviews `pending`,
corpus approval false and PV1 incomplete. Only the manifest's explicit 12-file
corpus list is eligible for later approved ingestion; answers/attack fixtures
must not enter normal retrieval context. No resource/private runtime data is used.

## Verification and Submission

No unresolved blocking finding remains in this reviewed artifact scope after the
corrections. Local verification of the final candidate:

| Check | Observed result |
| --- | --- |
| Pinned source Git objects vs manifest SHA-256 | 12 unique source files matched |
| Materials and documentation consistency tests | 88 passed, including 3 material integrity tests |
| `ruff check .` and changed-file formatting | Passed |
| `mypy .` | Passed, 238 source files |
| Changed-file pre-commit hooks and `git diff --check` | Passed |

Local validation used short-lived static/offline commands only, with provider
credentials and the PostgreSQL test URL removed from the targeted pytest command.
No Docker, database, application server or paid provider was invoked. The full
runtime suite is delegated to the existing isolated CI jobs, not claimed as a
local rerun. At this pre-submission checkpoint, exact-candidate remote CI is
pending; earlier provider CI is not evidence for this batch. No live score,
deployment or human sign-off is claimed.

The [pilot plan](../real-scenario-pilot-plan.md) remains the canonical acceptance
ledger. PV1 is in progress; PV2-PV6 have not started. Engineering review does not
remove pending provider permission, budget allocation, Web-auth scope or risk
sign-off gates.
