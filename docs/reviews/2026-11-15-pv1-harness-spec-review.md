# PV1 Harness Specification Review

Date: 2026-11-15. Scope: draft-10 harness specification, unpopulated evidence
template, pilot-plan links and structural regression tests. No business code,
runtime configuration, frozen materials or prompt bytes changed.

## Authority

The maintainer authorized review, scoped commit/push after review passes and
exact-submission CI tracking. No harness implementation, pilot/model API call,
local environment creation or current Docker update is authorized. DeepSeek
reply and external transmission remain pending; spending authorization USD 0.
No support submission or account commitment is assumed. Remote CI disposable
test services are not a pilot deployment. No release/tag is authorized.

## Findings and Disposition

Two specification ambiguities were corrected before submission:

1. The blanket rejection of new executors conflicted with the planned replacement
   executor case. A replacement must be registered and its hooks/configuration
   attested before receiving work, while preserving predecessor journals and
   counters. Unregistered/uninstrumented executors still invalidate coverage.
2. Flush alone did not specify crash durability. The protocol now requires buffer
   flush plus fsync/equivalent durable acknowledgement and directory durability
   where needed, including manifest updates and terminal markers. Failed
   acknowledgement prevents dispatch or leaves already-started work unknown.

Added regression assertions for both rules and required correlation/coverage
fields. Previously, the all-null check alone could pass after deleting such
fields. The journal field allowlist is exact and excludes bodies, credentials
and free-form errors. This is a template test, not a runtime log-safety guarantee.

No remaining blocking issue was found in this document/template scope. Source
inspection confirmed origin/path checks precede pool delegation, retries=0,
pinned network resolution, no ambient proxies/redirects and bounded response
streaming. OpenAPI separately reads/parses the response and bounds the serialized
result; it does not enforce GitHub identity or presentation-field projection.
The specification therefore requires later identity validation and full response
review rather than claiming those properties from the adapter alone.

The proposed observation hooks do not exist. Structural tests do not prove hook
coverage, concurrent durability, exactly-once behavior, auth or live response
quality. Seven case records cover the existing six groups plus the already
required second legitimate call; eight fixture controls remain planned/not_run.
Missing observations remain null, and a timeout is not scored as lookup success.

## Verification and Remaining Gates

Observed pre-submission results:

| Check | Result |
| --- | --- |
| Offline preparation/materials/document tests | 110 passed; test DB/provider key variables unset, live smoke disabled |
| Frozen baseline comparison | All 16 material files byte-identical |
| Frozen task prompt | Pinned SHA-256 verified by the focused tests; unchanged |
| Ruff / mypy | Passed; 239 source files typechecked |
| Changed-file pre-commit / diff whitespace | Passed |

Only short-lived offline checks ran locally; no database, application server or
test environment was started. Actual harness
implementation and controls remain future separately authorized work; effective
runtime evidence belongs to PV2/PV3, not falsely claimed PV1 preparation evidence.
The submitted SHA and CI URL are reported separately after push. PV1 remains in
progress, PV2-PV6 not started, full authenticated Web incomplete. run_attempt,
API version, effective timeout, provider terms, transmission, billing readiness,
participants and dates remain open. No pilot checklist item is marked complete.
