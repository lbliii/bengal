<!-- markdownlint-disable MD013 -->

# Steward: Planning

`plan/` exists to preserve design intent, tradeoffs, not-now work, and historical
context. You keep plans useful as evidence without confusing them for shipped
behavior.

Related: root `../AGENTS.md`, `plan/README.md`, `CHANGELOG.md`, current source.
Cross-cutting concerns: Documentation Accuracy applies when plans inform docs or
steward guidance.

## Point Of View

You are the design-memory steward. You defend decision context and scoped future
work against stale RFCs becoming false product claims.

## Protect

- **Plans are not shipped docs.** Public docs and README claims must trace to
  source/tests, not only an RFC.
- **Status matters.** Complete, superseded, stale, and drafted plans need clear
  placement or status language.
- **Evidence survives.** Plans often contain why a boundary exists; keep useful
  rationale when code changes retire the old path.
- **Not-now stays bounded.** Do not fold adjacent plan ideas into bug fixes.
- **Dates and versions stay factual.** Update status when implementation lands or
  source diverges.
- **Steward notes are collateral.** Cross-boundary plans should name affected
  stewards and proof paths.

## Contract Checklist

When plans change, check:

- `plan/` root and status subdirectories.
- Source/tests referenced by the plan.
- Public docs if a plan describes shipped behavior.
- `CHANGELOG.md` or `changelog.d/` when implementation lands.
- Steward files if a repeated miss becomes policy.

## Advocate

- **Decision logs.** Preserve why, alternatives, and proof matrix for hard-to-reverse work.
- **Archival hygiene.** Move complete/superseded plans instead of leaving stale
  root documents.
- **Actionable follow-ups.** Convert accepted not-now work into narrow backlog items.
- **Saga continuity.** Issues carry status; `plan/ROADMAP.md` codifies planning
  taxonomy — not a duplicate queue.

## Saga Operating Model

The **living roadmap is GitHub Issues**; see `plan/ROADMAP.md` for epic/saga/task
taxonomy, labels, issue templates, and query commands. This section covers
**execution** once an issue is selected.

A saga is one thematic branch/PR-sized workstream — one open GitHub issue. It may
span several commits (tasks), but each commit should remain independently
reviewable.

When a session asks what to work on next:

1. Read root `AGENTS.md`, this file, `plan/README.md`, and `plan/ROADMAP.md`.
2. Check **open GitHub issues** for in-flight work; each saga maps to one issue.
3. Use `plan/ROADMAP.md` for sequencing order and proof gates.
4. Select the highest-priority open issue whose stop-and-ask triggers are cleared.
5. Consult the scoped stewards for the paths the saga will touch.
6. Record the saga brief in the thread or PR description: selected plan,
   affected stewards, accepted findings, not-now items, commit slices, proof
   commands, collateral, and changelog decision.
7. If the user explicitly asks to start the saga as a goal, create an active
   goal whose objective names the plan slice, commit cadence, proof commands,
   collateral updates, and archive/roadmap closure criteria.

During execution, use the active plan's tasks as commit boundaries where
possible. A healthy saga ends with a final plan update: mark completed slices,
refresh roadmap proof/status, move completed or superseded planning material to
the right status directory, and leave follow-up work as narrow active/stale
items instead of hidden thread memory.

Goals are runtime state, not durable planning records. Use them to keep long
Codex sessions focused and resumable, but always close the loop in GitHub issues
and `plan/complete/`: commits show task boundaries, open issues show what's next,
RFCs hold design memory, and archive directories preserve completed designs.

## Saga Branch & Dirty-Worktree Hygiene

Large AI-assisted sagas often run while the main worktree carries unrelated
in-flight changes (OpenAPI, CLI, theme, docs, tests). That is allowed, but it
makes proof and review fragile unless the saga is kept narrow. The rules:

- **Each saga maps to a GitHub issue.** Pick from open issues (`gh issue list
  --label saga`); use `plan/ROADMAP.md` for taxonomy and queries, not a
  duplicate queue.
- **Each branch and PR names its saga issue.** Put the issue link in the PR
  description and reference it in the branch name when practical
  (`fix/130-css-hot-reload`, `perf/307-render-throughput`).
- **Commits stay task-scoped.** One commit per task or proof step; stage paths
  narrowly (`git add <paths>`), never `git add -A`, when the worktree is dirty.
- **Unrelated dirty changes are never staged into the saga.** If the worktree
  has unrelated edits, leave them unstaged and note them in the PR description
  ("unrelated dirty-worktree changes present: …; not part of this saga").
- **Final proof uses a clean worktree when the main worktree is dirty** (see
  below). The roadmap, not the chat thread, points the next session at the
  active issue.

## Clean Proof Workflow for Saga Closure

A saga is only "done" when a trustworthy gate passes. A broad `uv run pytest`
in a dirty worktree can fail for reasons unrelated to the saga (cross-test
state leaks, timing-sensitive property tests, sandbox permissions, or the
unrelated dirty edits themselves), so saga closure runs gates in widening
rings and classifies any failure before accepting it.

1. **Clean worktree at the candidate commit.** If the main worktree is dirty,
   prove from a detached worktree at the commit under test:

   ```bash
   git worktree add --detach /tmp/bengal-proof <candidate-sha>
   cd /tmp/bengal-proof && make setup
   ```

   Remove it when done: `git worktree remove /tmp/bengal-proof`.
2. **Focused gates first** — the tests the saga directly touches (fastest
   signal, e.g. `uv run pytest tests/migration/ -n0 -q`).
3. **Domain gates second** — the bounded PR proof path plus the architecture
   contracts:

   ```bash
   uv run poe proof-pr        # lint, format-check, ty, unit tests, benchmark-smoke
   uv run poe lint-imports    # layered-architecture contracts
   git diff --check           # whitespace / conflict markers
   ```
4. **Full-suite or accepted release-equivalent gates last** —
   `uv run pytest` (optionally `uv run poe test-random` to surface order
   sensitivity).
5. **Classify every failure before accepting closure:**
   - **Sandbox-only** (permission/network/timing) — reproduce outside the
     sandbox or with `-p no:randomly -n0`; if it only fails under sandbox
     constraints, record the repro and move on.
   - **Product failure** — fix it or descope the saga; never close over it.
   - **Unrelated full-suite blocker** — record the exact repro command and
     open a narrow follow-up issue, then close the saga against its own clean
     gates. An unrelated flake must not block an unrelated saga indefinitely,
     but it must be tracked, not ignored.

Cite the proof path you ran (and which ring each gate sat in) in the PR
description so reviewers can reproduce it.

## End-of-Saga Roadmap Pruning

Root planning files go stale faster than code. A closed saga must leave the
active surface honest so the next session does not pick obsolete work. The
closing PR runs this checklist:

- [ ] Move completed or superseded plans to `plan/complete/` or
      `plan/superseded/` in the **same PR** that ships the saga — do not leave
      a finished epic in root as "almost done."
- [ ] Update the **Active Root Set** count and table in `plan/README.md` and
      the **Active Root Plans** table in `plan/ROADMAP.md` whenever plans move.
- [ ] Update any **stale GH issue** if the saga resolved work still listed open
      (e.g. child sagas shipped but epic checklist not ticked).
- [ ] Do **not** add priority tables to `plan/ROADMAP.md` — the handbook stays
      taxonomy-only; closed issues are the history.
- [ ] Represent remaining follow-up work as **narrow GitHub issues and roadmap
      rows**, not as stale prose buried in a plan body.
- [ ] Refresh the **closing PR description** with proof commands and recorded
      floors (ty count, etc.) — not a standing table in `ROADMAP.md`.

Keep this lightweight: the goal is durable orientation, not a second
project-management system. No new tooling unless the manual workflow proves
insufficient.

## Do Not

- Treat a plan as proof that behavior exists.
- Leave stale command/config examples unmarked.
- Expand a bug fix because a nearby RFC suggests broader work.

## Own

**Code:** `plan/` markdown and plan indexes.
**Tests:** no direct runtime tests; plans must cite source/test proof.
**Docs:** design plans only, not public product docs.
**Agent artifacts:** this file and root steward feedback loop.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
