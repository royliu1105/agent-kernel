# Daily Plans

This directory tracks daily execution plans.

Use daily plans for short-lived implementation checklists. Use [Milestones](../milestones.md) for phase-level progress and [Development Plan](../development-plan.md) for the overall delivery method.

## Rules

- Create one file per active development day.
- Do not pre-create all 45 days.
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
