# PV1 No-Training and Offline Preparation Review

Date: 2026-11-15. Scope: draft-8 provider evidence gate, offline configuration/
budget preparation, planning/provider guides and focused documentation tests.

## Authority and Scope

The maintainer authorized review, scoped commit/push after review passes and
exact-submission CI tracking. No pilot/model API invocation, local environment
creation, current Docker update, provider transmission or spending is authorized.
Existing remote CI uses disposable test services, not a pilot deployment.
No business code, runtime configuration, credentials or frozen content changed.
This review does not contact support or accept a provider agreement.

## Findings and Disposition

No blocking correctness issue was found in the reviewed document/test scope.
The draft correctly distinguishes a maintainer requirement from an applicable
provider commitment, and both from final transmission/spending authorization.
Not finding a setting is not evidence of an opt-out. Inquiry submission is not
confirmed; no official reply or account agreement is asserted. Alibaba's public
statement is likewise not treated as account-specific sign-off or zero retention.
Public-policy summaries were checked against the official excerpts inspected in
the preceding preparation, not a new account/API inquiry or legal conclusion.

The six documented limits match ExecutionLimits and both API/Worker environment
blocks in docker-compose.yml. RetryPolicy defaults to two attempts, while the
candidate's retry_safe=false remains required. No assertion is made about the
currently running containers. Added a regression guard that parses the six table
rows, compares source defaults and applies an explicit in-memory pilot map through
ExecutionLimits.from_env; it never reads host environment values or starts services.

File counts/Unicode counts are reproducible from the frozen inputs and explicitly
not provider tokens or a price estimate. Model availability, tariff, currency,
batch feasibility and provider controls remain unresolved. No silent model alias,
free quota, account balance or hard spending cap is assumed.

Current submission authority is updated; the documentation-only preparation
checkpoint remains historical. No policy, threshold or safety gate is weakened.

## Evidence and Remaining Gates

The prompt hash and all 16 frozen material files must remain unchanged. The
no-training requirement blocks affected provider transmission until verified;
verification itself is not permission to transmit. PV1 remains in progress,
PV2-PV6 not started, full authenticated Web acceptance incomplete, and spending
authorization USD 0. No additional pilot checklist item is marked complete.

Observed pre-submission results:

| Check | Result |
| --- | --- |
| Focused materials/document tests | 95 passed; test DB/provider key variables unset, live smoke disabled |
| Frozen baseline comparison | All 16 material files byte-identical |
| Accepted task prompt | Pinned hash verified by the focused test |
| Ruff / mypy | Passed; 238 source files typechecked |
| Changed-file pre-commit / diff whitespace | Passed |

Only short-lived offline checks ran locally; no local backend/environment suite
was started. Remote CI must match the submitted SHA and its run URL is reported
separately. A green
CI is not a provider promise, live-model result or pilot sign-off. No release/tag
is authorized.
