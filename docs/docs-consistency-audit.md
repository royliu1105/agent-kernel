# v1.0 Docs Consistency Audit

This document records the v1.0 release candidate documentation consistency
audit.

## Day 86 Result

Date:

```text
2026-08-07 Asia/Shanghai
```

Baseline commit before Day 86:

```text
9d87ebf fix(api): support configurable bind port
```

## Audit Scope

Day 86 checked the v1.0 RC documentation set for consistency across:

- Release candidate planning and milestone docs.
- Public API, CLI, worker, Web, and configuration contracts.
- Clean-machine rehearsal docs and Day 85 rehearsal evidence.
- Release smoke, eval, load/soak, backup, migration, and security guidance.
- Documentation index links.
- `.env.example` variables versus the versioned configuration reference.

## Automated Guards Added

Day 86 adds `tests/unit/test_docs_consistency.py`.

The test currently enforces:

- Local links in `docs/README.md` resolve to existing files.
- Local links in `docs/daily/README.md` resolve to existing files.
- Every uppercase environment variable assigned in `.env.example` is mentioned
  with code formatting in `docs/configuration.md`.

These checks intentionally stay lightweight so they can run in the normal Python
test suite without external services.

## Consistency Decisions

The docs should continue to state:

- v0.1.0 is published and complete.
- Public Alpha is complete.
- Beta hardening is complete.
- v1.0 RC is still in progress.
- Fresh checkout application gates passed during Day 85.
- A fresh full-stack Docker Compose restart remains unclaimed until executed or
  explicitly waived.
- Known limitations remain release inputs for Day 87 scope freeze.
- v1.0 final readiness is not claimed before Day 90 verification.

## Known Follow-Ups

Day 87 should review whether every remaining limitation is acceptable for v1.0
or must block the release.

Day 88 should convert the accepted Day 87 scope into the final v1.0 release
checklist.

Day 89 should write v1.0 release notes from the final accepted scope, not from
aspirational roadmap language.

Day 90 should run final verification and decide whether to publish, block, or
waive specific remaining items.
