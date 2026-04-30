# Orchestration Steward

Orchestration coordinates discovery, build phases, rendering batches,
provenance, cache policy, and output writing. It should make sequencing clear
without absorbing domain or rendering behavior.

Related architecture docs:

- `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/core/orchestration.md`
- `../../site/content/docs/reference/architecture/core/data-flow.md`

## Protect

- Build phase clarity and ordering.
- Plugin hook timing and compatibility.
- Atomic output writes through approved helpers.
- Boundaries between discovery, rendering, postprocess, and cache/provenance.

## Do Not

- Add a new build phase without a design conversation.
- Bypass plugin hook surfaces for behavior extensions.
- Write files non-atomically.
- Move domain convenience behavior into orchestration just to share it.

## Documentation Ownership

- Own `site/content/docs/reference/architecture/core/orchestration.md`.
- Keep `site/content/docs/reference/architecture/core/data-flow.md` accurate for phase handoffs.
- Update extension-point docs when orchestration changes plugin hook timing.

## Local Checks

- `uv run pytest tests/unit/orchestration tests/integration -q`
- `uv run ruff check bengal/orchestration tests/unit/orchestration`
- `make changelog-check` for behavior-visible changes.
