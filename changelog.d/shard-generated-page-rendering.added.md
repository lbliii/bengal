Sharded the generated pages in the COW-free shard render backend (issue #350, Phase 2, saga
S13.4e). Tag / tag-index / auto-archive pages used to render serially in the parent process
(~15–23% of render un-parallelized), so a shard build *lost* end-to-end on generated-heavy
sites. The parent now LPT-balances them across the same content-shard workers — populating the
reserved `RenderPlan.generated_page_assignments` field (previously empty scaffolding) — and each
worker renders its assigned slice in its own heap, against its `WorkerSite`. Because the tag-page
render context already re-resolves its post list from the immortalized snapshot +
`site.get_page_path_map()` and rebuilds a fresh `Paginator` from `per_page`, rendering against
the WorkerSite resolves listings to the worker's own `PageView`s — the same COW-free path content
pages use — so the bulk parallelizes without the Phase-1 shared-graph copy-on-write tax. Generated
pages inject live `Page`/`Section` refs + a `MappingProxyType` into their metadata (`_tags`/
`_posts`/`_paginator`), which land in `AccumulatedPageData.raw_metadata` and are unpicklable across
the worker→parent boundary; `transport.picklable_metadata` flattens them exactly as
`PageArtifact._freeze_json` would, so the result pickles while the rendered output (which never
reads `raw_metadata`) and the page-artifact cache stay byte-identical. `render_isolation` stays
`off` by default. Proven byte-identical across the *whole* output tree (not just `*.html`) on
test-taxonomy by `test_shard_full_output_byte_identical_excluding_nondeterminism` (self-calibrating
non-determinism exclusion, non-vacuous) plus 7 unit tests; measured on a 1431-page, 15%-generated
idle-box A/B as 0.88× (pre-S13.4e, S17) → 1.23× shard-vs-thread (render phase 8.5s → 5.2s).
