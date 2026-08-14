# Plan: Bengal issue lifecycle (drive-ready specs)

**Lifecycle: Active**

**Complements:** [`BACKLOG.md`](BACKLOG.md), root + scoped `AGENTS.md`,
[`ROADMAP.md`](ROADMAP.md)  
**Adapted from:** DORI `plan/issue-lifecycle.md` (itself from Lantern / Orrery)

This document governs *how we track and burn down work*. It is **not** contract
law. Steward `AGENTS.md` maps remain the invariant layer.

`no collateral: contributor process experiment; not user-facing product`

## Why this matters

Large tasks are trees. A planner that also implements drifts. A worker that also
designs re-decides frozen questions. Without a lifecycle freeze:

1. Epics stay prose; workers invent schema mid-flight.
2. Two Tasks thrash the same megafile.
3. Exit criteria are ungradable checkboxes.
4. Design decisions reappear in every subtree.

**Fix:** Treat the GitHub issue graph as the task tree. Planners own epics,
sagas, and investigations. Workers only claim issues labeled `task` **and**
`lifecycle-ready`.

## Bengal names vs DORI names

Bengal already shipped epic/saga templates. Do **not** invert them.

| Bengal (keep) | DORI analogue | Claimable? |
| --- | --- | --- |
| Epic (`epic`) | DORI saga (umbrella) | No |
| Saga (`saga`) | DORI epic (one PR / workstream) | No — orchestrator may split it into Tasks |
| Investigation (`investigation`) | DORI investigation | No (planner) |
| Task (`task`) | DORI task | Yes iff `lifecycle-ready` |
| Commit inside a saga | DORI task (when no Task issue exists) | Only via `claim` on a ready Task, or a saga the user named |

A saga may land as one PR with several Task issues as commits. A Task may be
standalone under an epic when the Path scope is one magnet peel.

## Principles

1. **Specs as prompts** — Issue bodies are the unit of work, not chat history.
2. **Planner never implements; worker never plans.**
3. **One decision owner per subtree** — Ambiguity → investigation first.
4. **Owned paths** — Every Task names Path scope (repo-relative allowlist).
5. **Machine exit criteria** — Prefer `uv run pytest …`, `uv run lint-imports`,
   `uv run poe proof-pr` over prose-only checkboxes.
6. **`lifecycle-ready` is the lease** — `saga` / `enhancement` alone is never a
   worker lease.
7. **Stigmergy over ceremony** — Surprises in PR notes; lasting decisions in
   `plan/` RFCs / Steward Notes.
8. **Contract law ≠ court calendar** — Steward maps stay outside this harness.

## Issue tree

```text
epic (umbrella)
 └── saga (one PR-sized workstream)
      ├── investigation (freeze one decision / contract question)
      └── task (Path scope + machine Acceptance)
```

| Kind | Title prefix | Labels | Claimable? |
| --- | --- | --- | --- |
| Epic | `Epic: ` | `epic` | No |
| Saga | `Saga: ` | `saga` | No |
| Investigation | `Investigation: ` | `investigation` | No (planner) |
| Task | `Task: ` | `task` + `lifecycle-ready` when leased | Yes |

## Required fields

### Epic

- Problem / why now
- Child sagas checklist
- Gradable exit criteria
- Plan reference when design memory exists

### Saga

- Parent epic (if any)
- Scope / non-goals
- Acceptance + proof command
- Child Task issues when the saga will be driven in parallel

### Investigation

- Parent epic or saga
- Question being frozen
- Options + decision + consequences
- What Tasks may assume after close
- Steward Notes when contracts move

### Task

- Parent saga or epic
- Outcome (one sentence)
- **Path scope** — allowlist of files/dirs
- Decisions frozen (cite investigation — do not re-decide)
- **Acceptance** — at least one machine check
- **Not now** when useful
- Magnet overlap: name the magnet from [`BACKLOG.md`](BACKLOG.md) or `none`

## Steward ↔ lifecycle composition

| Lifecycle moment | Steward obligation |
| --- | --- |
| Investigation opens | Name affected steward ids / `AGENTS.md` maps |
| Investigation closes | Decision freeze; RFC or Steward Notes when contracts move |
| Task Path scope | Prefer paths inside steward Own; magnet carve-outs explicit |
| Task Acceptance | Prefer machine checks (domain pytest, `lint-imports`, `poe proof-pr`) |
| Worker in flight | Read nearest `AGENTS.md` for Stop & Ask |
| PR integrate | Steward Notes + parity matrix when cross-surface |

## Verb disambiguation

| Say | Means | Do not confuse with |
| --- | --- | --- |
| `drive` / `board` / `burndown` / `claim #N` | Backlog lifecycle | Steward review |
| `ask stewards` / `review swarm` / `bugbash` | Steward synthesis | Backlog drive |
| Bare `swarm` | **Avoid** | Prefer `drive` for backlog |

## Ownership and megafiles

Tasks that would edit any file on the **edit-magnet serialize list** in
[`BACKLOG.md`](BACKLOG.md) need a narrow Path-scope carve-out or a prior split
Task. Prefer “one steward tree + matching `tests/` + optional one docs file”.

## Integrate hygiene

- Drop `lifecycle-ready` when the Task closes.
- Do not merge unless the user explicitly asks.
- Workers leave PRs open; orchestrator integrates on request.
- Close a wave only when PRs are on `main` with `lint-and-type` and
  `fast-check` green.

## Authority

Tracker writes and merges require explicit user request. This harness never
mints write authority. The Bengal CLI/build is not the backlog driver.

## Labels

GitHub labels used by this harness:

- `task` — claimable Path-scoped work
- `investigation` — planner-only decision freeze
- `lifecycle-ready` — worker lease (add only when Path + Acceptance are filled)

These exist on `lbliii/bengal`. Recreate them only if a fork is missing them.
