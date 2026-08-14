<!-- markdownlint-disable MD013 MD060 -->

# Bengal Plan Index

Updated: 2026-08-14

## Start here

| Question | Answer |
|----------|--------|
| **What should we work on?** | [GitHub Issues](https://github.com/lbliii/bengal/issues) — `gh issue list --label saga --state open` |
| **How do we plan work?** | [`ROADMAP.md`](ROADMAP.md) — planning handbook (epic/saga/task, labels, templates) |
| **How do I execute a saga?** | [`AGENTS.md`](AGENTS.md) — branch hygiene, proof rings, close checklist |
| **How do agents work in parallel?** | [`BACKLOG.md`](BACKLOG.md) — `drive` / `board` / `claim`, magnet serialize list |
| **Issue lease / Path scope?** | [`issue-lifecycle.md`](issue-lifecycle.md) — `lifecycle-ready` Tasks |
| **2026-08 peel inventory?** | [`agent-parallelization.md`](agent-parallelization.md) — Wave 1–4 notes; magnets now in `BACKLOG.md` |
| **Why was this designed this way?** | Root `plan/<rfc>.md` or `plan/complete/` |

**The issue tracker is the living roadmap.** This directory holds design memory and
process — not a duplicate queue that will rot.

## `plan/` layout

| Path | Purpose |
|------|---------|
| `ROADMAP.md` | Planning taxonomy + GH queries + issue templates (not a priority list) |
| `AGENTS.md` | Saga execution workflow for agents |
| `*.md` (root) | Active RFCs — design intent for open epics |
| `complete/` | Shipped plans (pointer; verify against `CHANGELOG.md`) |
| `superseded/` | Replaced designs |
| `stale/` | Ideas needing fresh audit |
| `evaluated/` | Historical evidence |

## Active RFCs (design memory)

Status is in **GitHub**, not this table. See [`ROADMAP.md` § Active design memory](ROADMAP.md#active-design-memory-plan-root).

## Issue templates

`.github/ISSUE_TEMPLATE/` — `epic.yml`, `saga.yml`, `bug.yml` — enforce the
taxonomy defined in `ROADMAP.md`.
