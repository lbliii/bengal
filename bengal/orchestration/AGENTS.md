# Orchestration Steward

Orchestration coordinates discovery, build phases, rendering batches,
provenance, cache policy, and output writing. It should make sequencing clear
without absorbing domain or rendering behavior.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/core/orchestration.md`
- `../../site/content/docs/reference/architecture/core/data-flow.md`
- `../../site/content/docs/reference/architecture/core/pipeline.md`

## Point Of View

Orchestration represents the build lifecycle. It should connect services and
phase outputs without becoming the owner of content semantics, presentation, or
extension contracts.

## Protect

- Build phase clarity, ordering, and user-visible lifecycle behavior.
- Plugin hook timing and compatibility.
- Atomic output writes through approved helpers.
- Boundaries between discovery, rendering, postprocess, and cache/provenance.
- Incremental/full build parity.

## Contract Checklist

- Unit tests under `tests/unit/orchestration/` and integration build workflows.
- Build docs, data-flow docs, and extension-point docs when phase handoffs or
  hook timing change.
- CLI output/docs when build command behavior, warnings, or artifacts change.
- Cache/provenance and incremental collateral for rebuild decisions.
- Changelog for user-visible build behavior.

## Advocate

- Observable phase inputs, outputs, timing, and diagnostics.
- Plugin hook usage over custom phase additions when extension behavior is
  needed mid-build.
- Integration tests for phase changes that affect caches, generated artifacts,
  command output, or incremental rebuilds.

## Serve Peers

- Give rendering clear batch inputs and do not mix presentation work into phase
  coordinators.
- Give cache/incremental precise invalidation and provenance events.
- Give CLI and site docs stable build output behavior to explain.

## Do Not

- Add a new build phase without a design conversation.
- Bypass plugin hook surfaces for behavior extensions.
- Write files non-atomically.
- Move domain convenience behavior into orchestration just to share it.

## Own

- `site/content/docs/reference/architecture/core/orchestration.md`
- `site/content/docs/reference/architecture/core/data-flow.md`
- Extension-point docs for orchestration hook timing
- Checks: `uv run pytest tests/unit/orchestration tests/integration -q`
- Checks: `uv run ruff check bengal/orchestration tests/unit/orchestration`
- Checks: `make changelog-check` for behavior-visible changes
