Added `bengal/orchestration/render/isolated/worker_site.py` — `build_worker_site`, which
reconstructs a real `bengal.core.site.Site` from a serializable `RenderPlan` (issue #350,
Phase 2, saga S13.3b) so a separate-heap shard worker can render its own freshly-parsed pages
without the live mutable `Site` graph. It builds an empty `Site` from the plan's config/root
(theme/config_service/page_cache rebuilt by `__post_init__` with no content discovery), then
assigns the plan's reduced state; `merge_shard_pages` forms the heterogeneous `site.pages`
(this worker's live pages ∪ body-free `PageView` stand-ins for the rest, in canonical order).
`RenderPlan` now also carries `build_time` (the default-theme footer reads `site.build_time`
directly, and it is not config-derivable). It has no caller yet and `render_isolation` stays
`off`, so the default build is byte-identical. Proven by a subprocess byte-parity test
(`test_worker_site_renders_page_byte_identical`) that renders the `test-basic` fixture through a
pickle-round-tripped plan and matches the in-process build exactly.
