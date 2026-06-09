<!-- markdownlint-disable MD013 -->

# Epic: Shard-parallel end-to-end build (issue #350, Phase 2 — the holistic redesign)

> **Status: design DECIDED (2026-06-05), branch-contained.** Phase 1 (sagas
> S1–S7 on `lbliii/render-heap-isolation`) built and *de-risked* a separate-heap
> render backend — and then **measured it honestly**: it does **not** make a real
> build faster. This Phase 2 redesign is what turns the branch into a *holistic,
> superior end-to-end build*. Nothing merges to `main` until that is proven
> (S17). `render_isolation` stays `off` by default throughout.

## Why Phase 1 didn't materialize a win (the measured truth)

On a 4,288-page build (M3 Pro, 3.14t), the Phase-1 fork backend **regressed**:

| | thread | fork (Phase 1) |
|---|--:|--:|
| render *phase* | 49.4s | **68.7s (+39%)** |
| full build wall | ~115–126s | ~144s (+~20%) |

- The clean "2× render" calibration was a **small-heap artifact** — it cycled 135
  warm pages, so the forked parent's heap was tiny and copy-on-write was free.
- A real build forks a parent holding **all parsed pages**; render then reads and
  **mutates that shared graph**, so the fork pays a cost proportional to the
  corpus (COW on the shared mutable page graph + fork of a large RSS + pickling
  thousands of result records) that **exceeds** the parallelism gain.
- The fixed costs I first suspected are negligible (immortalize 0.2s, block-cache
  ×8 ≈ 0.5s), confirming the problem is the **fork boundary placement**, not setup.

### Phase attribution (the real cost map)

The first attribution mis-read two phases; the authoritative `phase_timings_ms`
breakdown (S10) on the 4,288-page fixture, **after S9 landed**, is:

| phase | time | share | note |
|---|--:|--:|---|
| **rendering** | 76.8s | **66%** | the prize; Phase-1 fork regressed it (COW) |
| cache save | 10.2s | 9% | scales with pages; partly optimizable |
| post-process | 9.3s | 8% | global artifacts, mostly serial |
| initialization | 8.0s | 7% | |
| content (taxonomy/menu/related) | 6.4s | 5.5% | related_posts now ~3s after S9 |
| **parsing** | **0.9s** | **0.8%** | NEGLIGIBLE — corrects the earlier "~28%" |

Corrections from S10 (both earlier guesses were wrong):
- **Parsing is ~1%, not ~28%.** patitas parsing is genuinely ~0% of the prize;
  the earlier figure was a residual-arithmetic artifact on a noisy box.
- **`related_posts` was ~17% and is now banked** by S9 (~8×, 24s → 3s),
  byte-identical — so the branch is *already* net-faster before the redesign.

Conclusions that drive (and re-scope) the redesign:
1. **The build is ~66% render-bound.** The entire remaining prize is recovering
   the free-threading render plateau, COW-free: ~77s → ~38s ≈ **a third off the
   whole build**. This vindicates #350's original render thesis.
2. **Parse-parallelization and the parse cache are dead** (parse is ~1%). The
   fork boundary still moves *before* parse, but only so workers **own their
   parsed pages** (avoiding the COW tax that sank Phase 1) — not for any
   parse-speedup. Render isolation done right is the whole game.

## The design: a 3-phase shard-parallel build

```
 parent: discover content files  ─┐
                                   │  (small parent heap — cheap fork)
        ┌──────────────────────────┴───────────────────────────┐
        │            fork N persistent shard workers            │
        └──────────────────────────┬───────────────────────────┘
 phase 1 (parallel, worker heaps): each worker parses ITS shard,
          returns LIGHTWEIGHT metadata (title/tags/date/url/section/excerpt/
          xref-entries) — parsed content stays in the worker's heap
                                   │
 barrier (parent): assemble the immutable, serializable RenderPlan
          (nav trees, menus, taxonomy term→pages, related index, page-view
          map for get_page(), frozen xref index, config/params, generated-page
          assignments) from the union of per-shard metadata
                                   │
 phase 2 (parallel, worker heaps): each worker renders ITS shard from its OWN
          parsed content + the received RenderPlan, writes HTML to disk,
          returns accumulations (page data, asset deps, errors)
                                   │
 reduce (parent): merge accumulations; run global postprocess (sitemap, RSS,
          search index, social cards) from site.pages metadata + merged data
```

**Why this is COW-free and scales:** the parent never holds all parsed pages
(the big heap is *distributed* across workers, each holding ~1/N). Workers render
from their own heap + a freshly-unpickled RenderPlan (their own objects). No
shared mutable graph is read or written across the boundary, so the COW tax that
sank Phase 1 disappears. Render (~66% of the build) runs in separate heaps,
recovering the free-threading allocator/GC plateau that the in-thread path
cannot — the realisation of #350's original render thesis. (Parse moves into the
workers too, but only to keep the parsed pages worker-local; parse is ~1% of the
build, so there is no parse-speedup to chase.)

### The one real blocker, and its fallback

`get_page(other_page).content` (a template embedding *another* page's full
rendered body, not just its metadata/excerpt) is the only genuine cross-shard
*content* dependency. Mitigation, in order: (a) the RenderPlan ships a
**page-view** for every page (title/url/excerpt/date/metadata) — enough for the
overwhelmingly common linking/listing use; (b) detect a cross-shard full-body
access and **fall back to the thread path** for that build (never wrong output).
`related_posts` and `xref` are resolved at the barrier (metadata only), so they
are *not* blockers under this design.

## What Phase 1 we keep, and what we replace

- **Keep / extend:** `snapshots/transport.py` (immortalize, `proxy_to_plain`),
  the partitioner (`isolated/partition.py`), the gate (`isolated/gate.py`), the
  parity harness (`test_isolated_render_parity.py`), the probe + case study.
- **Replace:** `isolated/worker.py` + `isolated/backend.py` (fork-after-parse)
  with persistent two-phase shard workers and a small-parent driver.

## Containment contract

- All Phase-2 work stays on `lbliii/render-heap-isolation`.
- `render_isolation` default stays **`off`**; the shard path is never the default
  until S17's end-to-end A/B is green.
- **Fallback value:** even if the redesign (S13/S14) proves too hard, S8–S10
  already make the branch net-faster end-to-end — so the branch materializes a
  *superior build* regardless of the redesign's fate.

## Sagas

### Group A — Trustworthy measurement + certain wins (bank gains, fix methodology)

- [x] **S8 — Trustworthy end-to-end benchmark (DONE).** A deterministic large-fixture
  generator (no `random-posts` widget), phase-attributed E2E timing, thread-vs-
  experimental A/B, idle-box protocol with variance reporting. Fixes the
  cycled-heap / random-widget / saturated-box flaws that made Phase-1 numbers
  unreliable. The yardstick for "superior end to end." *(m)*
- [x] **S9 — `related_posts` candidate index (DONE: ~8x, 24s→3s, byte-identical).** Replace the O(P·T·N) per-page
  rescan with a co-occurrence inverted index built once from the taxonomy
  (`{page: {candidate: shared_tag_count}}`), score in O(K) per page, keep the
  `_stable_key` tie-break. Est. 3–5× (~24s → ~6s). Fork-independent,
  deterministic. *(m)*
- [x] **S10 — Attribute the residual (DONE).** Dumped the authoritative
  `phase_timings_ms`: build is ~66% render, parsing ~1% (corrects the earlier
  ~28% guess). **Parse cache de-scoped** (parse isn't a cost). Next-tier targets
  if render is exhausted: cache-save (9%), post-process (8%), init (7%). *(s)*

### Group B — The shard redesign (holistic core, gated off)

- [x] **S11 — RenderPlan: the serializable global plan (DONE).** `bengal/snapshots/
  render_plan.py`: immutable, **unconditionally picklable** `RenderPlan` +
  `PageView` (22-field body-free page view, mirrors PageSnapshot's read surface) +
  `ShardPageMeta`/`XRefEntry` (map output) + `assemble_render_plan` (the barrier
  reduce; `RenderPlan.from_site` = the single-shard case). Reuses
  `SectionSnapshot`/`MenuItemSnapshot`; page-view-ifies the three body-holding
  places; **excludes `nav_trees`** (NavTree holds live refs → S13 rebuilds them
  worker-side). Proven by `tests/unit/snapshots/test_render_plan.py` (28 tests):
  pickle round-trip + no-proxy/no-PageSnapshot/no-NavTree leak guard
  (`assert_picklable`), shard-order-independence of the reduce (N∈{2,3,5,7}), and
  data-parity vs the live site (page-view map, taxonomy, xref index, related index,
  config). Decisions that diverged from the audit spec, with cause:
  - **Always-picklable, no fork/spawn branch.** Every mapping is flattened to a
    plain dict via `to_plain_data`, which *also drops injected runtime objects*
    (live Page refs under metadata keys like `_tags`, plugin callables) — the
    metadata-picklability hazard the audit flagged turned out to be load-bearing,
    not theoretical.
  - **Taxonomy is page-view-ified from the live `site.taxonomies`, not reduced from
    edges.** Discovered `SiteSnapshot.taxonomy` is silently empty (a pre-existing
    latent bug: `_snapshot_taxonomies` mis-iterates the `{name,slug,pages}` term
    dict as a page list). The live render path reads `site.taxonomies` directly so
    it is unaffected — and so is RenderPlan, which now sources taxonomy there.
  - **`config_snapshot` not shipped** (it holds a MappingProxyType; the render
    context already rebuilds it from raw config — the worker does the same).
  - xref edges skip generated pages to match the live index (built pre-taxonomy).
  Map/reduce edges (`taxonomy_terms`, `menu_entries`) are carried in `ShardPageMeta`
  as the S13 contract for when the parent no longer pre-builds the snapshot. *(l)*
- [x] **S12 — Content sharder (pre-parse) (DONE).** `isolated/partition.py` now
  shards *discovered content files* before parse: `discover_content_files` reuses
  `DirectoryWalker` to enumerate the source files (no parsing) — proven to be the
  **exact same set** `ContentDiscovery` parses (`test_discover_matches_content_discovery`
  asserts set-equality vs the real discovery walk = the cover guarantee);
  `ContentFile` + `estimate_file_cost` (on-disk byte size, the only pre-parse cost
  signal) + `partition_content_files` LPT-balance the files. The `"balanced"`/
  `"section"` packing was factored into one shared deterministic core
  (`_partition_indices`), leaving `partition_pages` (S3) byte-identical. Ordering
  sorts by **`Path.parts`** (component tuple), not `str(path)`, so the index→shard
  mapping is independent of filesystem listing order *and* the OS separator (a
  `str(path)` key interleaves a sibling file into a directory subtree differently
  on POSIX `/` vs Windows `\`). Adversarial review (2 confirmed findings) +
  mutation-verified that the ordering tests fail when the sort key regresses.
  *(m)* — NB the analogous `str(source_path)` tie-break in `render_plan.py`'s
  reduce (S11, line ~599) has the same latent cross-OS quirk; reconcile in S13/S16.
- [ ] **S13 — Persistent two-phase shard workers (IN PROGRESS).** `mp.Process`
  actors forked from a *small* parent: parse-shard → return metadata → barrier →
  receive RenderPlan → render-shard from own heap → return accumulations. The
  COW-free core; replaces Phase-1's fork-after-parse worker. *(xl)*

  **Reframing (2026-06-05):** the perf bet is already de-risked. The ceiling probe
  (`render-scaling-attribution-findings.md`) measured separate processes recovering
  render from the 2.26× thread plateau to **3.8×–4.6×**, while every *in-thread*
  lever (intern, full-world immortalize, owned frames) recovered ≤7%. Phase-1
  regressed only because it forked a *big* parent (all parsed pages) and paid COW;
  the probe won because its parent heap was tiny (COW-free). S13's small-parent
  design is engineered to land in that COW-free regime, so the dominant risk is
  **engineering correctness + new overhead** (barrier serialization, per-worker
  reconstruction, result merge), not the raw perf hypothesis. ⇒ Build S13 in
  testable vertical increments gated by **byte-parity** (S11's `from_site` oracle +
  the subprocess parity-test pattern); take the render-phase A/B at the first
  representative point (after the render leg works), not as a throwaway pre-probe.

  Increments (dependency order):
  - [x] **S13.1 — from-live-page map step (DONE).** `page_view_from_live_page` +
    `shard_meta_from_live_pages` in `snapshots/render_plan.py`: derive
    PageView/taxonomy/xref edges from a worker's OWN freshly-parsed pages with **no
    SiteSnapshot** (reuses `_snapshot_page_initial`'s per-page derivations;
    `section_path` sourced from `page._section_path` since the transient per-page
    snapshot has no resolved section; `related_pairs` deferred to the barrier —
    related is global). Proven byte-identical to the snapshot path
    (`shard_meta_from_pages`) across all 4 fixtures + reduces to the same plan as
    `from_site` (`tests/unit/snapshots/test_render_plan.py`, 9 new tests).
  - [x] **S13.2 — parse_shard (DONE).** `isolated/shard_worker.py::parse_shard`
    parses a `ContentFile` shard (S12) into fully body-filled live pages in the
    caller's own heap, with no full-site discovery: reconstructs each file's owning
    Section from its path (immediate parent dir; top-level files → no section),
    reuses `ContentDiscovery._create_page` UNCHANGED for construction, then
    `RenderingPipeline._parse_content` (the exact `phase_parse_content` call) for the
    body-fill, and computes `output_path` worker-side. Proven byte-identical to the
    in-process parse through the S13.1 PageView lens across all 4 fixtures, bodies
    confirmed filled, cover holds when partitioned into N shards
    (`tests/unit/orchestration/render/test_shard_worker.py`, 9 tests).
    **Deferred to S13.4 (genuine cross-shard hazard):** `_parse_content` resolves
    `[[xref]]` links via `site.xref_index`, but at parse time the *global* index
    doesn't exist yet (it's reduced from all shards). The tests pass the fully-built
    site (complete index) as the parity oracle, validating parse *mechanics*; the
    real worker needs an xref pre-pass or deferred resolution — S13.4's job.
  - [x] **S13.3a — render leg (render_shard) (DONE).** `shard_worker.py::render_shard`
    — the reusable phase-2 render core: renders a shard's own parsed pages →
    HTML on disk + a picklable `RenderChunkResult`, decoupled from the fork-state
    global (the persistent actor doesn't fork per chunk). Mirrors the proven
    `fork_render_chunk` body. Validated: re-rendering the build's own pages against
    the same site reproduces the in-process HTML byte-for-byte on test-basic +
    test-product. **Finding:** byte-parity requires `build_context.snapshot` to carry
    section data ("In This Section" tiles render from it) — a load-bearing input for
    the WorkerSite. (Nav-heavy parity is deferred to S13.3c's single-render subprocess
    harness; re-rendering an already-built site double-perturbs per-page nav state.)
  - [ ] **S13.3b–f — WorkerSite (design DECIDED via Plan agent).** **Verdict: build a
    real `bengal.core.site.Site` populated from the RenderPlan, NOT a facade** —
    because `SiteContext.__getattr__` silently returns `""` for a missing attribute
    (a facade gap → blank HTML that passes the build but fails the diff with no stack
    trace), and `Site.__post_init__` already rebuilds theme/version_config/
    config_service/`PageCacheManager`/registries from `config` alone **with no content
    discovery** — so a worker constructs an empty Site then assigns plan state.
    Gap fixes: (1) **NavTree** — the parent builds the real nav_trees at the barrier and
    ships a **page-view-ified NavNode tree** in the RenderPlan; the worker
    `NavTreeCache.set_precomputed`s it (the lock-free fast path never calls the
    SectionSnapshot-incompatible `NavTree.build`); relax `assert_picklable` for
    view-ified NavNodes. (2) **heterogeneous `site.pages`** = live pages (own shard) ∪
    PageViews (rest) in `plan.pages` order → `PageCacheManager` serves `regular_pages`/
    `get_page_path_map`/`indexes` uniformly (readers use source_path/metadata only).
    (3) **theme** — free via `__post_init__`. (4) **`site.indexes`** — `build_all` over
    the merged list with a **per-worker cache_dir** (the default theme reads
    `site.indexes.*`; avoid N-worker file races). (5) reset process-globals per worker
    (`_global_context_cache`, `NavTreeCache`, directive cache, external-ref resolvers).
    **`get_page().content` cross-shard** is the one true blocker → render-time raise for
    now; ship-or-fallback is S14. Ladder (fail-fast, byte-parity vs in-process each
    rung): **b** empty WorkerSite + 1-page render (test-basic); **c** heterogeneous
    pages at N≥2 shards + NavTree precompute (test-product/test-navigation); **d**
    indexes + menus; **e** taxonomy/related/xref/generated (test-taxonomy); **f**
    global-reset hardening + worker-count-invariance sweep.
    - [x] **S13.3b — empty WorkerSite + 1-page render (test-basic) (DONE).**
      `isolated/worker_site.py::build_worker_site(plan, shard_pages=())` builds a real
      `Site(root_path, config)` (theme/config_service/page_cache/version_config free via
      `__post_init__`, no discovery) then assigns plan state; `merge_shard_pages` produces
      the heterogeneous `site.pages` (live shard ∪ PageViews, in plan order). Proven
      byte-identical to the in-process build on test-basic in a **clean subprocess**
      (`test_worker_site_renders_page_byte_identical`) that also pickle-round-trips the
      plan (real heap transport). Findings that diverged from the b-rung spec, each fixed:
      - **`RenderPlan.build_time` added** — `base.html` renders `site.build_time |
        dateformat('%Y')` directly (footer copyright); it is NOT config-derivable nor in
        `bengal_metadata`, so a worker that left it `None` emitted a blank year. Sourced
        in `assemble_render_plan` / `from_site`.
      - **`site.sections` = top-level *real* sections, not `plan.sections`.** The snapshot
        carries a synthetic `root` container (path == content dir) that live `site.sections`
        never holds; assigning it makes `get_auto_nav` emit a bogus `/root/` item and
        `base.html:477` crash on its absent `_path`. Reconstructed as
        `[s for s in plan.navigation.top_level_sections if s.path != content_dir]` —
        verified to reproduce live `site.sections` across all 4 fixtures.
      - **URL parity needs `page._site` consistent with `output_path`.** `get_path`
        relativises `output_path` against `page._site.output_dir`; the worker must parse
        its shard AGAINST the worker site (two-phase: build → parse → `merge_shard_pages`),
        not a foreign site, or the home page resolves to `/index/` not `/`.
      - **Asset fingerprinting** needs the parent's `asset-manifest.json` passed as
        `render_shard(asset_ctx=...)` (loaded from the shared `output_dir`).
      - **In-process byte-parity is contaminated** by `id(site)`-keyed global caches +
        the directive-cache singleton across fixtures → the test runs per-build in a clean
        subprocess (mirrors `test_isolated_render_parity.py`); a real worker IS a separate
        process, so this is also the faithful proof.
      Triaged c–e scope: test-product/navigation/taxonomy still render an error overlay —
      all hit the same `item._path` / empty-`site.menu` path (`_auto_nav` fires with dicts
      lacking `_path` because the worker has no menu yet). Unblocking them is rung d (menu
      reconstruction) + rung c (NavTree precompute / transported section data for tiles).
    - [x] **S13.3c/d — menus + NavTree precompute + section/index reconstruction at N≥2
      (DONE, shipped as one PR).** c and d were entangled (both gating fixtures crash on the
      same empty-`site.menu` path and `test-navigation` needs both the menu *and* the docs
      sidebar to render), so they shipped together. Proven by
      `test_shard_build_is_byte_identical_to_in_process` — every page of **test-product** and
      **test-navigation** rendered across **N∈{2,3} disjoint shards** is byte-identical to the
      in-process build, in a clean subprocess with a pickle-round-tripped plan. Six findings,
      each a real reconstruction gap the render-level gate caught that the S13.2 PageView-lens
      parity could not:
      - **Menus carried, not re-derived.** `plan.navigation.menus` is snapshotted *after* the
        in-process menu phase, so it is the final assembled hierarchy, page-view-ified.
        `build_worker_site` assigns it straight onto `site.menu`; the engine builds the
        template menu via `[item.to_dict() …]`, so `MenuItemSnapshot` gained an `icon` field +
        a `to_dict()` byte-mirroring `MenuItem.to_dict` (carried through `_snapshot_menu_item`).
        Re-running `MenuOrchestrator` would re-derive auto-nav against `_site`/`_path`-less
        SectionSnapshots and diverge.
      - **NavTrees shipped view-ified, installed via `set_precomputed`.** `NavTree.build` calls
        live-Section-only APIs, so the parent's already-built trees are carried in a new
        `RenderPlanNavigation.nav_trees` field with every `NavNode.page`→`PageView`,
        `.section`→`SectionSnapshot` (`_view_ify_nav_trees`, fresh graph — never mutates the
        parent's live tree). `assert_picklable` relaxed: allow view-ified NavTrees, still reject
        live page/section refs by inspecting `NavNode.page`/`.section` types. The worker (test
        caller / future S13.4 driver) calls `NavTreeCache.invalidate()` +
        `set_precomputed(plan.navigation.nav_trees)` per shard — the lock-free fast path never
        reaches `build`.
      - **Section registry rebuilt.** `__post_init__` builds an empty `ContentRegistry`; a live
        page's `_section` resolves lazily via `registry.get_section`, so without registration
        `get_page_section()` returns None and the renderer misroutes every section-index page
        into its *root-home* tile branch. `build_worker_site` registers `plan.sections` (flat,
        completeness) then `register_sections_recursive(top_level)` (the tree carries the
        `.parent` links the flat tuple lacks — needed for `page.ancestors`/breadcrumb depth).
      - **`SectionSnapshot._path` added** (= `href`, which `snapshots/content.py` already builds
        baseurl-free). Breadcrumbs read `ancestor._path`; without it `get_breadcrumbs` fell back
        to a `/{slug}/` guess and emitted a duplicate ancestor crumb (`//`).
      - **`plan.pages` ordered to the live discovery walk.** `page.next`/`prev` index into
        `site.pages`; the old `(weight, str(source_path))` sort diverged from the walk, breaking
        leaf-page prev/next. `assemble_render_plan` now orders by the live `site.pages` when the
        parent holds the full list (from_site / single-process driver), falling back to the
        deterministic key only for the future multi-shard reduce — pulling part of S16's
        ordering reconcile forward; the cross-OS `str(source_path)` reconcile remains S16.
      - **Indexes deferred, justified.** `site.indexes` lazy-builds correctly over the merged
        heterogeneous page list at N≥2; the SectionIndex/PageView-`section` gap and the
        per-worker index `cache_dir` (parallel-worker file race) did **not** surface in the
        gating fixtures, so they move to S13.4 (where parallel workers actually race).
      The **random-posts widget** (`site.regular_pages | sample(3)`, unseeded) is provably
      non-reproducible once the pool exceeds the sample size (test-navigation/api.md); those
      pages are byte-excluded but overlay-checked (same reason `test_isolated_render_parity.py`
      uses only deterministic test-product). Gate is non-vacuous (#130): asserts ≥2 shards
      fired, exact cover, ≥2 real pages byte-compared, no overlay on skipped pages — and a
      mutation (breaking `SectionSnapshot._path`) was confirmed to fail it. `ty` floor
      unchanged (539); `render_isolation` stays **off**.
  - **S13.4 — barrier-owns-globals ladder (IN PROGRESS).** Make the parent SMALL: every
    global is reduced from the per-shard meta union + the small parent, NOT from a fully-built
    `SiteSnapshot`. Each rung is OFF-by-default (a kwarg on `assemble_render_plan`) and
    byte-parity-gated vs the `from_site` oracle (N∈{1,2,3,5,7}) + live-site ground truth.
    - [x] **S13.4a — taxonomy + related + tag_pages** reduced from the PageView union
      (`reduce_taxonomy_from_metas`). `_reduce_taxonomies` reproduces
      `TaxonomyOrchestrator.collect_taxonomies`; `_reduce_related_index` reproduces
      `RelatedPostsOrchestrator.build_index`. Closed the `related_index=={}` gap from the real
      (related-free) live map step.
    - [x] **S13.4b — config/params/data + schedule_template_groups + snapshot_time** from the
      small parent (`reduce_globals_from_parent`), 2026-06-09. Byte-identical BY CONSTRUCTION:
      config = `to_plain_data(dict(site.config.raw))` (the exact expr `builder.py:178-179` uses
      to seed `snapshot.config` — landmine: `snapshot.config` is `site.config.raw`, NOT
      `site.config`, which flattens to `{}`); params = `config_dict["params"]`; data =
      `dict(site.data)`; `schedule_template_groups` = the PageView union grouped by
      `template_name` (reproduces `scheduling._compute_template_groups`); `snapshot_time → 0.0`
      (proven unread on the render path — the build stat is the separate `stats.snapshot_time_ms`).
      Scalars + `bengal_metadata` were ALREADY `getattr(site, …)`. Gated by
      `test_globals_from_parent_*` incl. a non-vacuous params test (injected `[params]`) — note
      `plan.data` is `{}` on every fixture because `to_plain_data` drops `DotDict`-typed data
      leaves (a PRE-EXISTING snapshot-path behaviour, flagged for a separate issue, NOT S13.4b's
      regression). Design adversarially critiqued (workflow, 7/7 claims held).
    - [ ] **S13.4c — SectionSnapshot tree from `ShardPageMeta.section_metas` + content walk
      (DESIGNED, refutation-corrected; NEXT RUNG).** Gate `_relink_all_sections` (section 5)
      behind `reduce_sections_from_metas`; rebuild the flattened section tree at the barrier from
      a new `SectionMeta` (carried from each `_index.md` the worker parses) + the parent's
      `discover_content_files` walk (directory skeleton incl. virtual sections) + `pv_by_path`.
      **Ordering change DROPPED + frozen:** the plan's "adopt `discover_content_files` Path.parts
      order, delete the `(weight, str(source_path))` fallback" is **empirically REFUTED** —
      live `site.pages` is the discovery-walk append order (a section's weight-ordered subsections
      BEFORE its own `_index`; top-level sections NOT weight-sorted), which equals NEITHER
      Path.parts NOR the `(weight, str)` fallback on nested-section sites (measured on
      test-navigation; frozen as `test_walk_order_diverges_from_path_parts`). So the fallback
      STAYS; the multi-shard walk-order reproduction is coupled to this section-tree rebuild and
      is its own follow-on. **Refutation-corrected design points (from the critic):** (1) the
      worker CANNOT pre-resolve section `href` (no parent chain) — recompute `href`/`_path` at the
      BARRIER top-down after the skeleton tree is built, via parent-name join +
      `apply_version_path_transform(site)`; (2) `SectionMeta` ownership is DIRECTORY-keyed and
      index-page-agnostic (stem ∈ {index,_index}), not "`_index.md`-keyed"; (3) seed virtual
      sections (dir with content files but no index) from the content walk. New dataclass
      `SectionMeta(path, metadata, weight, …)`; `_rebuild_sections_from_metas` (union by dir path
      → seed skeleton → group pages by `pv.section_path` → parent/child by path-prefix → post-pass
      `root`/`hierarchy`); 8 new gate tests. Navigation (menus/nav_trees/top_level_*) stays
      snapshot-sourced — separate **S13.4d**.
    - [~] **S13.4d — menus + nav_trees rebuilt at the barrier — OPTIONAL (small-parent only).**
      NOT required by the shipped backend: it uses `RenderPlan.from_site`, which already carries
      `menus` + view-ified `nav_trees` (installed via `NavTreeCache.set_precomputed`), byte-identical
      on test-navigation. Only the small-parent path (avoiding the snapshot build) needs this. xl.
    - [ ] **S13.4e — shard generated pages — THE MAIN REMAINING PERF ITEM.** tag/archive/pagination
      currently render SERIALLY in the parent (byte-correct, but ~23% of render un-parallelized) —
      so the shard build LOSES end-to-end on generated-heavy sites (S17). Sharding them (synthesis +
      `generated_page_assignments` + worker Paginator rehydration; COW-prone — the generated graph is
      shared) is what broadens the win beyond render-heavy-low-generated sites. *(l)*
    - [~] **S13.4f/g — small-parent driver — OPTIONAL OPTIMIZATION.** The shipped `ShardRenderBackend`
      forks from a `from_site` parent (parent builds the snapshot — cheap, ~10%). The pure
      snapshot-free small-parent reduce (all barrier flags on, S13.4a/b done; sections=S13.4c-pt2,
      nav=S13.4d) only shrinks that serial tail; not required for the win.
  - [x] **S13.5 — render-phase A/B (DONE).** Clean idle-box measurement (`.context/spike_clean.py`):
    1.75× content render on render-heavy docs (ceiling-consistent), 0.90× cheap content.
- [x] **S14 — Cross-shard rendered-content (the one true blocker) — DONE (fork).** `PageView.content`
  property resolves a sibling's rendered body from a fork-COW `{source_path: content}` registry the
  parent installs pre-fork — body-free + picklable preserved. Handles the related-posts card's
  `post.content` fallback AND full embeds; byte-identical on test-taxonomy. Spawn (no COW) deferred.
  Commit `9d3d48846`. (xref reconciliation across shards: not exercised by fixtures; revisit if a
  cross-shard xref case appears.)

### Group C — Prove & gate

- [~] **S15 — Integrate + the gate (PARTIAL).** Shard wired as a cold-build path behind
  `render_isolation=shard` (gate + dispatch, commit `76e6395c3`). The crossover gate is still
  page-count-based; S17 shows it must become **content-aware** (render-cost + generated-page ratio):
  shard wins on render-heavy-low-generated, loses on generated-heavy. *(m)*
- [x] **S16 — Byte-parity guard (DONE, small).** `tests/integration/test_shard_render_parity.py`:
  full build `shard` == `thread` BYTE-IDENTICAL on test-product/basic/taxonomy/navigation (excluding
  the unseeded random-posts widget page), backend fires, non-vacuous. Large-fixture + worker-count
  sweep (S16 v2) still pending. *(m)*
- [~] **S17 — Materialization gate (MEASURED, conditional).** Idle-box median-of-3 E2E A/B
  (`bench_build_ab --modes thread,shard`): render-heavy docs (1001 pg, no generated) **1.12× — shard
  WINS (+12%)**; bench site (1779 pg, 273 generated) **0.88× — shard LOSES** (generated render serial
  in parent). ⇒ net-positive ONLY for render-heavy-low-generated cold builds; **S13.4e broadens it**.
  Stays non-default until S13.4e + the content-aware gate. *(s)*

### Group D — Close

- [ ] **S18 — Write-up + roadmap.** Update the case study, attribution findings,
  and the #350 issue with the redesign, the honest Phase-1 negative result, and
  the Phase-2 numbers. *(s)*

## Gates & invariants

- **Byte-parity is non-negotiable** (S16) — thread == shard, run-to-run and
  across worker counts, on a deterministic fixture.
- **The merge bar is end-to-end speed** (S17), measured on an idle box,
  median-of-N — not render-phase-only and not a cycled-heap microbench.
- **Cold-build / CLI / CI only**; dev server + incremental keep the thread path.
- **Default `off`** until S17; the build always falls back to the thread path on
  any shard-backend failure or unsupported cross-shard content access.

## Risks

- **S13 actor protocol complexity** (persistent workers, barrier, RenderPlan
  serialization) — the XL. Prototype the protocol on a small fixture before
  wiring the full pipeline.
- **RenderPlan completeness** — missing a Type-A dependency ⇒ a subtle output
  diff. S16's parity guard is the backstop; build the RenderPlan field list from
  the Phase-2 dependency audit (cross-chunk-render-deps).
- **`get_page().content` cross-shard** — the one true blocker; the page-view +
  fallback must be airtight (never silently wrong).
- **Per-platform crossover** — fork-only today; spawn (Windows) remains deferred.

## References

- Phase-1 work + honest negative result: this branch (S1–S7),
  `benchmarks/render-isolation-case-study.md`,
  `benchmarks/render-scaling-attribution-findings.md`.
- Backend to replace: `bengal/orchestration/render/isolated/`.
- Reusable foundation: `bengal/snapshots/transport.py`, `isolated/partition.py`,
  `isolated/gate.py`, `tests/integration/test_isolated_render_parity.py`.
