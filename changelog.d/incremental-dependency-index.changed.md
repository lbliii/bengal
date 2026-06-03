Warm incremental builds now update the provenance dependency reverse-map *incrementally*
on cache save instead of rebuilding it from every page's record. The old writer cold-read
~every record file on a one-page edit (≈99% of provenance save), so on a 500-page blog the
provenance save dropped from ≈2.0s / 511 record reads to ≈11ms / 0 reads — a ~180x cut to
that phase, the dominant cost of the dev-loop save. The incremental result is byte-identical
to a full rebuild (gated by `tests/unit/build/provenance/test_delta_dependency_index.py`
across edit / add / delete / multi-consumer / same-hash / combined scenarios) and falls back
to the full rebuild on cold builds or any uncertainty. Set `BENGAL_PROVENANCE_DELTA_SAVE=0`
to force the full rebuild (rollback lever).

This also fixes a latent reverse-map bug: pages with identical inputs (e.g. empty taxonomy
pagination pages) share one content-addressed record, and the old builder listed only the
dedup winner — silently dropping the other pages from the reverse map (under-invalidation),
non-deterministically. The reverse map now lists every page that consumes an input.
