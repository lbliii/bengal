<!-- markdownlint-disable MD013 MD060 -->

# Bengal Planning Handbook

**Updated**: 2026-06-17

The **living roadmap is GitHub Issues** on [lbliii/bengal](https://github.com/lbliii/bengal/issues).
This file does not duplicate that queue. It codifies how we plan, label, and close
work so agents and humans know where to look and what shape issues should take.

`plan/` RFCs are **design memory** (why, tradeoffs, proof matrices). They are not
the agenda. When an RFC and an open issue disagree on status, **the issue wins**.

---

## Where to look

| Question | Go here |
|----------|---------|
| What should we work on next? | Open issues — see [queries](#issue-queries) below |
| Why does this boundary exist? | `plan/<rfc>.md` or `plan/complete/` |
| How do I close a saga? | `plan/AGENTS.md` — proof workflow + pruning checklist |
| What shipped? | `CHANGELOG.md`, closed issues, `plan/complete/` |

---

## Work hierarchy

```text
Epic (GitHub issue, label: epic)
 └── Saga (GitHub issue, label: saga) — one thematic PR / branch
      └── Task (commit) — one proof step; not usually its own issue
```

| Level | GitHub? | Scope | Typical proof |
|-------|---------|-------|---------------|
| **Epic** | Yes — `epic` label | Multi-saga umbrella; tracks child checklist | All child sagas closed; epic acceptance criteria met |
| **Saga** | Yes — `saga` label | One branch, one PR, days–weeks | Focused gates → domain gates → acceptance criteria in issue body |
| **Task** | No (commits) | One reviewable commit inside a saga | Single test/lint/proof step; referenced in commit message |
| **Bug** | Yes — `bug` label | User-visible defect or regression | Repro + fix + regression test; no saga ceremony unless large |

**Rule of thumb:** if you cannot describe the proof in one PR description, it is an
epic. If it fits one PR with scoped commits, it is a saga. If it fits one commit,
it is a task inside that saga.

### Effort (in issue bodies)

Optional suffix on saga/epic issues: `s` (hours), `m` (days), `l` (week), `xl`
(multi-week). Used for sequencing intuition, not estimation accounting.

---

## Labels

| Label | Meaning |
|-------|---------|
| `epic` | Umbrella issue; body lists child sagas as `- [ ] #NNN` |
| `saga` | Shippable workstream; body links `Part of epic #NNN` when applicable |
| `bug` | Defect — fix and regression test |
| `enhancement` | New capability or improvement |
| `performance` | Build/runtime perf (often paired with `epic` or `saga`) |
| `documentation` | Docs-only |
| `skip-changelog` | PR exempt from `changelog.d/` fragment (chore/internal) |

Domain labels (`performance`, etc.) combine with structural labels (`epic`,
`saga`). A saga can be `enhancement` + `saga`; an epic can be `performance` +
`epic`.

---

## Issue body template

### Epic

```markdown
## Problem
<why this matters; link plan/RFC if design memory exists>

## Child sagas
- [ ] #NNN <saga title> (effort: m)
- [ ] #NNN ...

## Acceptance criteria
<what "epic closed" means — not individual saga proof>

## References
- Plan: `plan/<file>.md` (design memory only)
```

### Saga

```markdown
> Part of epic #NNN.   <!-- omit if standalone -->

## Scope
<one paragraph — what this PR will and will not touch>

## Acceptance criteria
- [ ] <observable, testable outcome>
- [ ] `uv run poe proof-pr` (or narrower gate named here)

**Effort:** s|m|l|xl

## References
- Plan: `plan/<file>.md`
```

### Bug

```markdown
## Repro
<steps or failing test>

## Expected / actual

## Acceptance criteria
- [ ] Regression test (or cite existing test that now passes)
```

---

## Issue queries

Run these before picking work (or use the GitHub UI equivalent):

```bash
# Open epics
gh issue list --label epic --state open

# Open sagas (pick one whose epic is unblocked)
gh issue list --label saga --state open

# Release blockers
gh issue list --label bug --state open

# Perf track
gh issue list --label performance --state open
```

**Pick order:** bugs blocking release → unblocked saga with clearest proof gate →
epic whose child sagas are ready. Do not start a saga without a matching open
issue.

---

## Relationship: issues ↔ `plan/`

| Artifact | Role | Updates when |
|----------|------|------------|
| GitHub issue | Living scope, status, acceptance criteria | Open → PR → close |
| `plan/<rfc>.md` | Design intent, tradeoffs, proof matrix | When architecture changes; archive on epic close |
| `plan/complete/` | Pointer that work shipped | Same PR that closes the epic/saga |
| `CHANGELOG.md` / `changelog.d/` | User-facing release notes | Shipped behavior |

**On saga close** (see `plan/AGENTS.md` checklist):

1. Close the GitHub issue (or let PR auto-close via `Fixes #NNN`).
2. Move completed RFC to `plan/complete/` if the plan is fully delivered.
3. Do **not** maintain a duplicate priority table in this file.

---

## Active design memory (`plan/` root)

These RFCs back open or near-term epics. **Status lives in GitHub**, not here.

| Plan file | GH anchor |
|-----------|-----------|
| `epic-performance.md` | #343 |
| `epic-shard-parallel-build.md` | #350 |
| `rfc-snapshot-build-plan-handoff.md` | *(open issue before starting)* |
| `rfc-incremental-dependency-indexes.md` | #333 |
| `rfc-template-view-model-contracts.md` | #335 |
| `rfc-effect-traced-incremental-builds.md` | #330 |
| `rfc-persistent-resident-site.md` | #522 |
| `rfc-theme-library-assets.md` | — |
| `rfc-health-diagnostics-audit.md` | — |
| `epic-delete-forwarding-wrappers.md` | — |
| `epic-ux-sharp-edges.md` | — |

Archived plans: `plan/complete/`, `plan/superseded/`, `plan/stale/`, `plan/evaluated/`.

---

## Baseline verification (run, do not cache)

Stale counts rot. Run these when a saga needs a recorded floor:

```bash
uv run ty check bengal/          # type diagnostic count
grep '^version' pyproject.toml   # package version
uv run poe proof-pr              # bounded PR gate
```

Record results in the **closing PR** or issue comment, not in this file.
