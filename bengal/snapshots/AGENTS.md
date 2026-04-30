# Snapshots Steward

Snapshots protect a stable, render-ready view of a site for scheduling and
parallel rendering. They should make shared state explicit and immutable where
possible.

Related architecture docs:

- `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/core/pipeline.md`

## Protect

- Immutable or effectively immutable snapshot data.
- Safe handoff between mutable compatibility pages and render scheduling.
- Deterministic navigation/template/cache snapshots.
- Thread-safe progress and error handling.

## Do Not

- Store live mutable objects when a snapshot value should be captured.
- Add shared mutable scheduler state without synchronization.
- Mutate page pipeline records.
- Hide worker exceptions without page/source context.

## Documentation Ownership

- Own snapshot-related explanations in `site/content/docs/reference/architecture/core/pipeline.md`.
- Keep cache and warm-build docs aligned when snapshot reuse behavior changes.
- Update architecture docs when mutable Page compatibility and immutable snapshot handoffs move.

## Local Checks

- `uv run pytest tests/unit/snapshots -q`
- `uv run pytest tests/integration/warm_build -q`
- `uv run ruff check bengal/snapshots tests/unit/snapshots`
