# Daily Plans

This directory tracks daily execution plans.

Use daily plans for short-lived implementation checklists. Use [Milestones](../milestones.md) for phase-level progress and [Development Plan](../development-plan.md) for the overall delivery method.

## Rules

- Create one file per active development day.
- Do not pre-create all planned future days.
- Create the next day only when that day starts.
- Keep each daily plan small enough to execute.
- Update checkboxes as work completes.
- Record blockers and follow-ups.
- Update `../milestones.md` when a phase-level item changes.
- Update specs or ADRs when implementation changes behavior or decisions.

## File Naming

Use:

```text
day-01.md
day-02.md
day-03.md
```

## Template

```text
# Day XX: Title

## Goal

## Scope

## Tasks
- [ ] ...

## Acceptance
- [ ] ...

## Verification
- [ ] ...

## Notes
```

## Existing Daily Plans

- [Day 01: Project Skeleton and Engineering Baseline](day-01.md)
- [Day 02: Run Lifecycle and Storage Foundation](day-02.md)
- [Day 03: Run State Machine and CLI Operations](day-03.md)
- [Day 04: LLM Provider Interface and Deterministic Execution](day-04.md)
- [Day 05: Model Router and OpenAI Provider Baseline](day-05.md)
- [Day 06: Worker Execution Loop](day-06.md)
- [Day 07: Phase 1 Runtime Closure](day-07.md)
- [Day 08: Tool Interface and Safe Execution Foundation](day-08.md)
- [Day 09: Policy Decisions for Tool Execution](day-09.md)
- [Day 10: Persisted Tool Calls and Audit Timeline](day-10.md)
- [Day 11: Approval Records, API, and CLI](day-11.md)
- [Day 12: Approval Interrupt and Resume](day-12.md)
- [Day 13: Phase 2 Retry and Fallback Closure](day-13.md)
- [Day 14: Knowledge Base and Document Storage Foundation](day-14.md)
- [Day 15: Document Upload and Local Object Store Foundation](day-15.md)
- [Day 16: Ingestion Job and Text Parser Foundation](day-16.md)
- [Day 17: Chunker and DocumentChunk Storage Foundation](day-17.md)
- [Day 18: Embedding Interface and Vector Store Foundation](day-18.md)
- [Day 19: Retriever, Citation Builder, Retrieval API, and CLI](day-19.md)
- [Day 20: kb_search Tool and Agent Runtime Integration](day-20.md)
- [Day 21: RAG Behavior Evals and Regression Cases](day-21.md)
- [Day 22: Memory Domain, Storage, API, and CLI](day-22.md)
- [Day 23: Memory Retrieval and Agent Context Integration](day-23.md)
- [Day 24: Phase 3 Closure and Full Verification](day-24.md)
- [Day 25: Trace and Correlation Foundation](day-25.md)
- [Day 26: Structured Runtime Logs](day-26.md)
- [Day 27: Latency and Metrics Foundation](day-27.md)
- [Day 28: Retrieval Metrics and RAG Eval Dataset Runner](day-28.md)
- [Day 29: Phase 4 Closure and Cheap Eval CI](day-29.md)
- [Day 30: Agent Workbench Shell and Dashboard](day-30.md)
- [Day 31: Run Timeline and Approval Inbox Interactions](day-31.md)
- [Day 32: Workbench Navigation and Operational Views](day-32.md)
- [Day 33: Playwright Smoke Tests and Phase 5 Verification](day-33.md)
- [Day 34: Docker Compose and Fresh Clone Runtime Path](day-34.md)
- [Day 35: Release Documentation and Examples](day-35.md)
- [Day 36: v0.1 Release Closure](day-36.md)
- [Day 37: Public Alpha Release Blocker Triage](day-37.md)
- [Day 38: v0.1 Final Release Verification](day-38.md)
- [Day 39: Public Alpha Kickoff](day-39.md)
- [Day 40: Workbench Live API Health](day-40.md)
- [Day 41: Live Run Lookup and Timeline](day-41.md)
- [Day 42: Live Approval Inbox](day-42.md)
- [Day 43: Live Approval Mutation UI](day-43.md)
- [Day 44: Live Knowledge Base List](day-44.md)
- [Day 45: Live Retrieval Search Flow](day-45.md)
- [Day 46: Public Alpha Examples Refresh](day-46.md)
- [Day 47: Behavior Eval Coverage Expansion](day-47.md)
