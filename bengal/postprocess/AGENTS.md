# Postprocess Steward

Postprocess owns site-wide artifacts after rendering: sitemap, feeds, output
formats, redirects, search indexes, social cards, and AI-readable manifests.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/rendering/postprocess.md`
- `../../site/content/docs/building/output-formats.md`
- `../../site/content/docs/building/ai-native-output.md`

## Point Of View

Postprocess represents downstream consumers of the built site: search engines,
readers, feed clients, AI agents, and deployment platforms. Artifacts should be
complete, deterministic, and aligned with visibility policy.

## Protect

- Sitemap/RSS/XML correctness and visibility filtering.
- JSON/TXT/Markdown/LLM output format schemas and incremental skip behavior.
- Redirect, robots, social card, and search-index artifact paths.
- Atomic writes and deterministic output ordering.

## Contract Checklist

- Tests under `tests/unit/postprocess/` and integration output-format tests.
- Output format docs, AI-native output docs, deployment docs, and generated
  artifact examples.
- Cache/incremental collateral when artifacts are skipped or regenerated.
- Schema/types docs and changelog when artifact fields change.
- Artifact audit/link health collateral for generated URLs.

## Advocate

- Explicit schemas and snapshots for machine-readable outputs.
- Visibility and content-signal behavior that is easy for authors to predict.
- Fast incremental paths that never leave stale search or AI indexes.

## Serve Peers

- Give health/audit complete artifact inventories and URL targets.
- Give docs and default theme stable generated artifact promises.
- Give cache/incremental deterministic hashes and regeneration reasons.

## Do Not

- Generate artifacts from stale page lists or hidden/draft content.
- Change JSON fields or URL paths without docs/tests/changelog.
- Write output files non-atomically.
- Treat AI-readable outputs as secondary when they are user-facing artifacts.

## Own

- `bengal/postprocess/`
- `site/content/docs/reference/architecture/rendering/postprocess.md`
- `site/content/docs/building/output-formats.md`
- `site/content/docs/building/ai-native-output.md`
- Tests: `tests/unit/postprocess/`, output-format integration tests
- Checks: `uv run pytest tests/unit/postprocess tests/integration/test_incremental_output_formats.py -q`
- Checks: `uv run ruff check bengal/postprocess tests/unit/postprocess`
