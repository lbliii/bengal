# Snapshots Steward

Snapshots protect a stable, render-ready view of a site for scheduling and
parallel rendering. They should make shared state explicit and immutable where
possible.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/core/pipeline.md`
- `../../plan/rfc-bengal-snapshot-engine.md`

## Point Of View

Snapshots represent the point where mutable compatibility state is captured for
parallel work. They should give workers a deterministic view of the site.

## Protect

- Immutable or effectively immutable snapshot data.
- Safe handoff between mutable compatibility pages and render scheduling.
- Deterministic navigation/template/cache snapshots.
- Thread-safe progress and error handling.

## Contract Checklist

- Snapshot unit tests and warm-build integration tests.
- Pipeline and cache docs when snapshot reuse or scheduling changes.
- Free-threading notes for shared state, worker queues, and mutable handoff.
- Changelog for user-visible build/rebuild behavior.

## Advocate

- Captured values over live object references.
- Small scheduling APIs with explicit error propagation.
- Tests that compare sequential and parallel snapshot behavior.

## Serve Peers

- Give rendering workers stable inputs.
- Give cache/incremental deterministic snapshot hashes or reuse signals.
- Give tests a clear seam for parallel scheduling proof.

## Do Not

- Store live mutable objects when a snapshot value should be captured.
- Add shared mutable scheduler state without synchronization.
- Mutate page pipeline records.
- Hide worker exceptions without page/source context.

## Own

- Snapshot explanations in `site/content/docs/reference/architecture/core/pipeline.md`
- Cache and warm-build docs when snapshot reuse behavior changes
- Tests: `tests/unit/snapshots/`, warm-build integrations
- Checks: `uv run pytest tests/unit/snapshots -q`
- Checks: `uv run pytest tests/integration/warm_build -q`
- Checks: `uv run ruff check bengal/snapshots tests/unit/snapshots`
