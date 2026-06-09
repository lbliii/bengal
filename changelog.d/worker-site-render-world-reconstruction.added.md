Extended `build_worker_site` (issue #350, Phase 2, sagas S13.3c+d) so a separate-heap shard
worker reconstructs the *full* render world from a `RenderPlan` and renders byte-identically to
the in-process build, not just the single-page surface S13.3b proved. It now assigns
`site.menu`/`menu_localized` from the plan (with `MenuItemSnapshot` gaining an `icon` field and
a `to_dict()` that byte-mirrors `MenuItem.to_dict`), ships the parent-built navigation trees
*view-ified* in a new `RenderPlanNavigation.nav_trees` and installs them via
`NavTreeCache.set_precomputed` (so the lock-free path never calls `NavTree.build`, which needs
live Sections), registers sections in the worker `ContentRegistry` (so `get_page_section`
resolves and section-index pages stop misrouting to the root-home tile branch), adds
`SectionSnapshot._path` (fixing breadcrumb ancestor detection), and orders `plan.pages` to the
live discovery walk (so `page.next`/`prev` are byte-stable). `render_isolation` stays `off` and
the path has no production caller yet, so the default build is unchanged. Proven by
`test_shard_build_is_byte_identical_to_in_process`, which renders every page of `test-product`
and `test-navigation` across N∈{2,3} disjoint shards (clean subprocess, pickle-round-tripped
plan) byte-identical to the in-process build; the unseeded `random_posts` widget page is
byte-excluded but overlay-checked.
