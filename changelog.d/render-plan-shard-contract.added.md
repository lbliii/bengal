Added `bengal/snapshots/render_plan.py` — the `RenderPlan` map/reduce contract for the
shard-parallel cold build (issue #350, Phase 2, saga S11). It defines an immutable,
unconditionally-picklable global render world — `PageView` (a 22-field, body-free view of a
page that substitutes for `PageSnapshot` in any page collection), `ShardPageMeta`/`XRefEntry`
(the per-shard map output), and the assembled `RenderPlan` (page-view map for `get_page`,
taxonomy, frozen xref index, related index, sections/menus, config) — built from per-shard
metadata via `assemble_render_plan`. It is the serializable foundation a separate-heap render
worker will read instead of the live mutable `Site` graph (S13), so the parsed page bodies
never cross the heap boundary. It has no caller yet and `render_isolation` stays `off`, so the
build is byte-identical. Proven by `tests/unit/snapshots/test_render_plan.py` (30 tests): pickle
round-trip + body/proxy/NavTree leak guard, shard-order-independence of the reduce, and
data-parity vs the live site (page-view map, taxonomy, xref index, related index, config).
