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
- **Saga continuity.** Keep the roadmap able to answer "what should we work on
  next?" without a second tracking system.

## Saga Operating Model

A saga is one thematic branch/PR-sized workstream selected from an active root
plan, usually a sprint, phase, or proof slice. It may span several commits, but
each commit should remain independently reviewable and match one task or proof
step.

When a session asks what to work on next:

1. Read root `AGENTS.md`, this file, `plan/README.md`, and `plan/ROADMAP.md`.
2. Treat `plan/ROADMAP.md` as the authoritative ordering and proof gate.
3. Select the highest-priority item whose stop-and-ask triggers are cleared.
4. Consult the scoped stewards for the paths the saga will touch.
5. Record the saga brief in the thread or PR description: selected plan,
   affected stewards, accepted findings, not-now items, commit slices, proof
   commands, collateral, and changelog decision.
6. If the user explicitly asks to start the saga as a goal, create an active
   goal whose objective names the plan slice, commit cadence, proof commands,
   collateral updates, and archive/roadmap closure criteria.

During execution, use the active plan's tasks as commit boundaries where
possible. A healthy saga ends with a final plan update: mark completed slices,
refresh roadmap proof/status, move completed or superseded planning material to
the right status directory, and leave follow-up work as narrow active/stale
items instead of hidden thread memory.

Goals are runtime state, not durable planning records. Use them to keep long
Codex sessions focused and resumable, but always close the loop in files:
commits show task boundaries, `plan/ROADMAP.md` shows the next queue, active
plans show status/proof, and archive directories preserve completed or replaced
design memory.

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
