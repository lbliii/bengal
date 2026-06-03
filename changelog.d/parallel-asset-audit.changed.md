The post-render asset audit (`find_missing_local_asset_references`) now scans output
HTML in parallel across a `WorkScope` for larger builds, with byte-identical findings
(per-file results are re-indexed to preserve document order; small sites stay serial).
On content-heavy sites — docs/autodoc with large pages — this audit was re-reading and
regex-scanning big rendered HTML serially and dominated the build (~47% of an autodoc
build); parallelizing it cut that phase ~5x (1.80s → 0.35s) and the overall autodoc build
~1.7x (3.8s → 2.2s, ~26 → ~45 pages/s) on a 5P+6E machine. Unlike the render phase, this
work is per-file independent (read + regex on a thread-local string), so it scales with
free-threading rather than being bound by shared-object coherency cost.
