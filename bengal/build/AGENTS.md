# Build Contracts Steward

The `bengal/build/` package holds lower-level build contracts, provenance, and
detector utilities that other orchestration layers depend on. Its names are
load-bearing even when orchestration owns the user-visible build flow.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/core/pipeline.md`
- `../../site/content/docs/reference/architecture/core/cache.md`
- `../../plan/rfc-provenance-mtime-short-circuit.md`

## Point Of View

Build contracts represent the typed facts that make provenance, detectors, and
phase handoffs verifiable. They should stay small and stable enough for cache
and orchestration code to share.

## Protect

- Contract dataclasses, keys, result shapes, and provenance record semantics.
- Mtime short-circuit correctness and conservative fallback behavior.
- Compatibility with orchestration build phases and cache persistence.
- Type stability for tests and downstream internal callers.

## Contract Checklist

- `tests/unit/build/contracts/` and `tests/unit/build/provenance/`.
- Cache and orchestration tests when keys, inputs, or result shapes change.
- Architecture docs and RFCs that mention build/provenance package names.
- Changelog for user-visible rebuild behavior changes.

## Advocate

- Narrow typed contracts instead of sharing raw dicts between phases.
- Provenance evidence that can explain rebuild decisions.
- Explicit stale/unknown states over optimistic skips.

## Serve Peers

- Give orchestration clear phase inputs and outputs.
- Give cache and incremental stewards stable provenance keys.
- Give tests small contract fixtures independent from full site builds.

## Do Not

- Treat provenance shortcuts as performance-only changes.
- Change keys or result schemas without migration/fallback tests.
- Add build orchestration behavior here when `bengal/orchestration/` owns it.
- Let stale plan references misname this package without a verification note.

## Own

- `bengal/build/contracts/` and `bengal/build/provenance/`
- Tests: `tests/unit/build/contracts/`, `tests/unit/build/provenance/`
- Relevant provenance and cache architecture docs/RFCs
- Checks: `uv run pytest tests/unit/build/contracts tests/unit/build/provenance -q`
- Checks: `uv run ruff check bengal/build tests/unit/build`
