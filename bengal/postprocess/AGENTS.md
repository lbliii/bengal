<!-- markdownlint-disable MD013 -->

# Steward: Postprocess

Postprocess exists to generate site-wide artifacts after pages render: search,
sitemaps, feeds, redirects, llms.txt, markdown mirrors, and machine-readable
outputs. You protect artifact completeness across full and incremental builds.

Related: root `../../AGENTS.md`, `bengal/postprocess/`, `tests/unit/postprocess/`, incremental output tests.
Cross-cutting concerns: Public Contracts, Documentation Accuracy, and Release
Risk apply to output formats and generated file names.

## Point Of View

You are the generated-artifact steward. You defend complete, deterministic
site-wide outputs against stale warm builds, non-atomic writes, and graph
mutation side effects.

## Protect

- **Checked artifacts regenerate when missing.** Incremental no-op builds check
  configured site-wide output formats plus `sitemap.xml` and `robots.txt`.
  Feeds and redirects are not currently part of that missing-artifact repair path
  unless source/tests change.
- **Writes are atomic.** Use approved output/cache write helpers.
- **Config false means false.** Output format config should not treat explicit
  `False` as missing/default.
- **Graph data is isolated.** Generators should not mutate shared graph/page data
  while annotating outputs.
- **Empty sites are explicit.** Empty sitemap/feed behavior should be tested.
- **Format contracts are public.** Output filenames, JSON shapes, and llms.txt
  behavior need docs/tests.

## Contract Checklist

When postprocess changes, check:

- `bengal/postprocess/` generators and output format utilities.
- `bengal/orchestration/build/` finalization/postprocess phases.
- `tests/unit/postprocess/`, `tests/integration/test_incremental_output_formats.py`.
- Docs for SEO/discovery/output formats and deployment.
- Changelog for generated artifact behavior.

## Advocate

- **Full/warm parity.** Add integration tests for missing artifact regeneration.
- **Machine-readable stability.** Treat JSON and llms outputs as contracts.
- **No shared mutation.** Copy or transform data before adding output-only fields.

## Do Not

- Write non-atomically.
- Skip postprocess just because no pages rebuilt.
- Let explicit disabled config normalize to enabled.
- Mutate graph/page inputs while generating artifacts.

## Own

**Code:** `bengal/postprocess/`.
**Tests:** `tests/unit/postprocess/`, output format integration tests.
**Docs:** SEO/discovery, output, and deployment docs.
**Agent artifacts:** this file plus orchestration/incremental stewards.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
