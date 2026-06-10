Warm (incremental) builds now keep `rss.xml` and the prebuilt Lunr
`search-index.json` correct. Previously a warm no-op build only repaired
`sitemap.xml`, `robots.txt`, and the output-format artifacts when they went
missing; a deleted `rss.xml` or `search-index.json` was never regenerated, and
the no-op fast path could skip the build entirely without noticing they were
gone. Worse, RSS/Atom were gated behind `if not incremental`, so a normal
incremental content change (e.g. adding a dated post) left the feed stale until
a full rebuild.

`_missing_postprocess_artifacts` now lists `rss.xml` (when `generate_rss` is
enabled, honoring the i18n prefix path) and `search-index.json` (only when the
search backend is enabled + prebuilt, `index_json` is a configured site-wide
format, and the optional `lunr` package is importable — otherwise the build
would loop reporting a file it can never create). RSS/Atom feeds are now
regenerated on incremental builds alongside the sitemap (both are cheap and
correctness-critical); dev-server / serve-ready builds still restrict
post-processing via the task allow-list, so reload latency is unaffected.

Adds discriminating regression coverage: unit tests for the artifact list (with
config/availability guards and i18n path placement) and integration tests for
no-op feed/search-index repair plus warm-build content parity (RSS, sitemap,
baseurl change, and autodoc-source-edit page content matching a from-scratch
full build). Replaces the previously vacuous RSS incremental tests that asserted
against a `public/blog/index.xml` path the generator never writes and guarded
every assertion behind `if rss_path.exists():`.
