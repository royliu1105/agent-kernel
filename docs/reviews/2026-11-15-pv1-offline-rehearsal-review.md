# PV1 Offline Operation Sheet Review

Date: 2026-11-15. Scope: draft-9 offline operation sheet, request template,
pilot-plan linkage and focused tests. No business code or runtime settings changed.

## Authority and Scope

The maintainer authorized review, scoped commit/push after review passes and
exact-submission CI tracking. No pilot/model API invocation, local environment
creation, current Docker update, provider transmission or spending is authorized.
Existing remote CI disposable services are not a pilot deployment. DeepSeek's
official reply and external transmission permission remain pending; USD 0 is
authorized. This review does not contact support or assume an inquiry was sent.

## Findings and Disposition

No blocking correctness issue was found in this document/template/test scope.
Source inspection covered API schemas and handlers, CLI request wrapping,
runtime message mapping, the Responses serializer and the RBAC permission table.

- The JSON artifact is not an API body or installed execution harness. The
  tests substitute synthetic IDs and construct requests only in memory.
- API Run creation takes an input envelope; CLI --input takes its inner object.
  RunCreateRequest validates the envelope and memory selection, not the full
  execution contract. Subsequent runtime/serialization checks add shape evidence,
  not HTTP, authorization, live provider or behavior evidence.
- Explicit messages override task. Agent creation has no prompt binding field.
  The frozen prompt is supplied explicitly, not automatically loaded by a registry.
- Approval records a decision. Resume executes in the API process; both that
  process and Worker need observer coverage. Clarified this in the operation sheet.
- Operator can submit and approve; viewer cannot submit or inspect approvals.
  No separation of duties, participant admission or HTTP isolation is claimed.
- Strengthened the artifact test to require all six distinct planned case IDs,
  not merely six entries. All outcomes remain not_run.

The selected DeepSeek adapter reuses the Responses serializer. Serializing a mock
request here neither routes it to that adapter nor establishes provider/model
availability, tool binding, resumed history or no-training behavior. The template
contains no credential and has no external transport or substitution runner.

## Verification and Remaining Gates

Observed pre-submission results:

| Check | Result |
| --- | --- |
| Offline preparation/materials/document tests | 104 passed; test DB/provider key variables unset, live smoke disabled |
| Frozen baseline comparison | All 16 material files byte-identical |
| Frozen task prompt | SHA-256 verified by the focused tests; unchanged |
| Ruff / mypy | Passed; 239 source files typechecked |
| Changed-file pre-commit / diff whitespace | Passed |

Only short-lived offline checks ran locally, with no database/server creation.
Current authorization is updated; the preceding offline preparation checkpoint
remains historical.

PV1 remains in progress, PV2-PV6 not started, authenticated Web acceptance
incomplete and GitHub observer unimplemented. Actual response inspection,
run_attempt, provider terms, participant admission and trial dates remain open.
No pilot checklist item is marked complete. The submitted SHA and remote CI URL
will be reported separately; green CI is not pilot sign-off. No tag/release.
