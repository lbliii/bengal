Added an opt-in `reduce_taxonomy_from_metas` path to `assemble_render_plan` (epic #350
S13.4a, "barrier-owns-globals"): the barrier can now recompute the taxonomy structure and
the related-posts index *purely from the global PageView union* instead of from a
fully-built `site.taxonomies` / `page.related_posts`. `_reduce_taxonomies` reproduces
`TaxonomyOrchestrator.collect_taxonomies` byte-for-byte (first-writer display name,
`normalize_taxonomy_slug`, singular `category` frontmatter key, stable date-DESC ordering)
and `_reduce_related_index` reproduces `RelatedPostsOrchestrator.build_index` (limit=5),
closing the long-standing gap where the real worker map step (`shard_meta_from_live_pages`)
emits `related_pairs=()` and the assembled plan's `related_index` was therefore empty.

This is the first step toward a *small* shard-parallel build parent that never builds the
whole-site snapshot. It is off by default — `from_site` and every existing caller keep the
snapshot-sourced path, byte-unchanged. Proven in `tests/unit/snapshots/test_render_plan.py`
against the `from_site` oracle across N∈{1,2,3,5,7} shards and against the live site
(`site.taxonomies` / `page.related_posts`) as independent ground truth, plus discriminating
synthetic unit tests for the date-DESC sort, first-writer name, slug normalization, and the
generated/autodoc eligibility filter.
