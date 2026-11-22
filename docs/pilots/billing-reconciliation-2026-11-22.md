# Billing Reconciliation (2026-11-22)

Status: **reconciled with labeled unknowns** (documentation evidence only — not
a product billing feature). Maintainer-directed pass after PV3/PV4 closure.

Private machine evidence (gitignored):
`.agent-kernel/billing-reconciliation-20261122/`.

## Scope

| In scope | Out of scope |
| --- | --- |
| Same-day PV3 admissions (first → R4) generation token ledgers | Mock PV4 drills (no paid calls) |
| Earlier same-day paid GitHub approve→resume Run | Building in-app invoicing |
| DeepSeek wallet API balance snapshots | Claiming provider invoices we did not open |
| DashScope/Aliyun as labeled unknown | Treating unknowns as zero |

Authorized envelope for the paid cohort day: **CNY 200 DeepSeek** +
**CNY 200 Aliyun** (top-up intent recorded in PV3 authorizations).

## DeepSeek (generation)

### Observed wallet (API `/user/balance`)

| When (local evidence) | Total CNY |
| --- | --- |
| After first cohort snapshot | 206.76 |
| After re-run | 205.45 |
| After R2 | 203.84 |
| After R3 | 202.23 |
| After R4 | 199.38 |
| Fresh re-check (this reconciliation) | **199.38** (unchanged) |

- Snapshot-window **decrease: CNY 7.38** (206.76 → 199.38).
- Remaining **CNY 199.38** is still under the CNY 200 DeepSeek top-up intent;
  wallet never showed a zeroed or over-envelope balance in these captures.
- Fresh capture equals the R4 snapshot → no further DeepSeek spend detected
  since R4 under this key.

### Token / tariff labels (not invoices)

Cohort ledgers (sum of `input_tokens_total` / `output_tokens_total`):

| Admission | Attempts (ok) | Input | Output | Tariff label CNY* |
| --- | --- | --- | --- | --- |
| First | 60 (53) | 1,077,292 | 77,142 | 2.79 |
| Re-run | 60 (57) | 1,265,139 | 82,712 | 3.24 |
| Preflight v2 | 6 (5) | 108,425 | 9,455 | 0.29 |
| R2 | 60 (60) | 1,091,726 | 82,981 | 2.85 |
| R3 | 60 (54) | 2,040,953 | 107,003 | 5.11 |
| R4 (accepted) | 60 (60) | 1,148,276 | 82,176 | 2.97 |
| **Cohort sum** | | **6,731,811** | **441,469** | **~17.24** |
| Paid GitHub resume (extra) | 1 | 6,464 | 884 | ~0.02 |

\*Tariff label uses rates **fitted so R2's published ~CNY 2.85 matches that
cohort's tokens** (output≈2× input per 1M). It is a **generation-side estimate**,
not a DeepSeek invoice line.

**Material inconsistency (kept explicit):** wallet decrease (~**7.38**) is much
smaller than the summed tariff labels (~**17.2**). Prefer the **wallet series**
as spend evidence for envelope checks; treat tariff sums as **over-estimates /
non-authoritative** for `deepseek-flash` until console day-lines are pasted.
Do **not** average them into a fake “true cost.”

## Aliyun / DashScope (embeddings)

| Item | Status |
| --- | --- |
| API key present in paid overlay | yes (not printed) |
| In-repo balance or day-line pull | **not available / not performed** |
| Prior pilot label for index smoke | ≤ CNY ~0.0022 estimate (historical note) |
| Console itemized day-lines | **unknown** (manual console still required) |

No DashScope charge is booked as zero. Embedding spend remains an **open
unknown** pending console evidence.

## Envelope decision

| Check | Result |
| --- | --- |
| DeepSeek wallet remaining | CNY 199.38 |
| Evidence of breach of CNY 200 DeepSeek top-up intent | **no** (from snapshots) |
| Aliyun CNY 200 | **inconclusive** (no line items captured) |
| Overall | **DeepSeek side OK with unknowns labeled; Aliyun still unknown** |

## What this does / does not close

- Closes the “do a maintainer reconciliation pass” follow-up as **docs + private
  snapshots**, with honest tariff-vs-wallet mismatch.
- Does **not** replace Aliyun console review.
- Does **not** implement product billing features.
- Does **not** reopen PV3/PV4.

## Follow-ups (optional)

1. Paste DeepSeek and Aliyun **console day-lines** for 2026-11-22 into the
   private evidence dir (no secrets in git).
2. If day-lines disagree with the wallet series, amend this note — do not delete
   the mismatch.
