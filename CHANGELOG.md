## [0.5.0] - 2026-06-15

### Added

- `bengal serve --drafts` and `bengal build --drafts` (or `drafts = true` under `[build]`) render pages marked `draft: true` so you can preview unpublished content locally; drafts stay hidden by default. (`#488`)
- `bengal fix` now suggests and applies fixes for broken internal links — correcting typos in a page path, re-pointing a link to a page that moved, and fixing a stale `#anchor` — instead of only fixing directive fences. Link rewrites are offered as confirm-before-apply fixes so you can review each one. (`#491`)
- `define_collection(..., transform=callable)` runs your callable on each record's frontmatter before schema validation, so you can normalize legacy field names during a migration without rewriting source files. (`#492`)
- Autodoc CLI extraction now supports argparse: point it at an `argparse.ArgumentParser` with `framework="argparse"` and it documents subcommands, positional arguments, and options just like the Click and Typer paths. (`#493`)

### Changed

- Dev-server assets now serve through the fast static path; the hidden-buffer 404 workaround is removed (requires bengal-pounce 0.8.0+). (`#400`)
- `bengal build --memory-optimized` is now labeled experimental, and its help text and docs no longer promise a fixed memory saving — measure peak memory with and without the flag on your own site before relying on it. (`#487`)

### Fixed

- Autodoc no longer turns illustrative cross-reference and directive examples in docstrings into live (often broken) links, so generated API pages and the broken-link health check stay clean. (`#485`)
- The internal link checker now resolves relative links (such as `../other/`) against the page that references them and reports broken ones, instead of silently passing them. (`#489`)


## [0.4.3] - 2026-06-15

### Fixed

- Build error summaries and investigation hints no longer crash or report wrong counts during parallel builds on free-threaded Python. (`#439`)


## [0.4.2] - 2026-06-15

### Removed

- Removed the dead `phase_cache_save` build-finalization helper, which was never called and diverged from the live cache-save path by omitting `build_context`; the live build already persists the cache with `build_context` for incremental safety. (`#451`)

### Fixed

- Fixed the `make gh-release` / `poe gh-release` mechanism: the GitHub release title was built from a greedy `grep '^name ='` that captured every `[[tool.towncrier.type]]` category name (`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`), so the v0.4.1 title rendered as `bengal Added Changed Deprecated Removed Fixed Security 0.4.1`. A new `scripts/publish_github_release.py` now reads `[project].version` via `tomllib` and renders the title as `vX.Y.Z — <theme>`, deriving the theme from the release page's frontmatter `description:`. (`#480`)
- Corrected docs-vs-reality drift across the documentation: the snippet/config and migration tutorials now use the real `baseurl` site-config key (not `base_url`), the install/verify/pin examples report the current `0.4.1` version instead of the stale `0.1.10`, the R002/H1702 error-code docs name Kida (the default engine) instead of Jinja2, and the object-model reference lists the real `bengal/core/page` modules (`navigation.py`, `bundle.py`) instead of the phantom `content.py`/`relationships.py`. The CLI-contract doc-lint allowlist was also burned down: the renamed `bengal validate` (now `bengal check`), `bengal collections ...` (now `bengal content collections`/`content schemas`) and `bengal sources ...` (now `bengal content sources`/`content fetch`) families were corrected in the docs and removed from the allowlist, and the lint now scans only code context so prose phrases like "Running bengal from wrong directory" no longer need allow-listing. (`#474`, `#470`)
- Removed the fabricated `bengal project ...` command group from the documentation (it was never registered in the CLI): skeleton-manifest passages now explain that skeletons are applied automatically during `bengal new site` rather than via a non-existent `bengal project skeleton apply`, profile docs point at `bengal build --profile`, and "add sections to an existing site" guidance was reworded since no such command exists. Also corrected `bengal init` references to `bengal config init` in the site-templates reference. A new CLI-contract doc-lint now greps every `bengal <subcommand>` invocation in `site/content/docs/**/*.md` and fails if it does not resolve to a command registered in the Milo CLI. (`#435`)
- Corrected the content-types reference and design-principles docs to use the real public API: `from bengal.content_types import register_strategy` with `register_strategy("news", NewsStrategy())` (an instance, not the nonexistent `ContentTypeRegistry` class), and fixed the documented "Available types" list to match the actual registry keys (`autodoc-python`/`autodoc-cli` instead of phantom `api-reference`/`cli-reference`, plus the previously undocumented `archive`, `notebook`, and `list`). (`#436`)
- `BaseMarkdownParser.parse_with_toc` now documents and returns the 4-tuple `(html, toc, excerpt, meta_description)` that the parsers actually produce. `PythonMarkdownParser` now returns this 4-tuple (with empty excerpt/meta) instead of a 2-tuple, so custom parser implementations and callers can unpack four values uniformly. (`#443`)
- `Site.from_config(config_path=...)` now loads the explicitly named config file instead of silently ignoring the argument. The factory declared and documented a `config_path` parameter but never forwarded it to the loader, so an explicit path was dropped and Bengal always auto-discovered `bengal.toml` in the site root; the path is now honored, falling back to auto-discovery only when it is omitted. (`#444`)
- Unified the two diverged `RebuildReasonCode`/`RebuildReason` definitions into a single canonical vocabulary in `bengal.build.contracts.results` (string-valued codes, `RebuildReason.details` plus a backward-compatible `trigger`); the build-orchestration copy now re-exports them so both import paths resolve to the same objects, and `ChangeDetectionResult.full_rebuild(reason=...)` now records its reason instead of silently discarding it. (`#445`)
- When per-page JSON / search-index data accumulation fails for a page, the failure is now surfaced as a visible build warning (recorded in the build summary) with the full, untruncated error and an actionable suggestion, instead of being silently dropped at debug level. The page is still omitted gracefully and the build completes as before. (`#449`)
- Removed a production `from unittest.mock import Mock` import from the site index generator. The JSON-serialization path no longer references the test library to skip values; non-serializable metadata (custom objects, lists, and dicts) is now dropped via a real `json.dumps`-based serializability check. (`#450`)
- Routed three remaining non-atomic file writes through the crash-safe atomic helpers in `bengal.utils.io.atomic_write` (write-temp-then-rename), so a SIGINT/crash/OOM mid-write can no longer leave a truncated file: the external-reference index cache (`ExternalRefResolver` index fetch), the performance `latest.json` metrics snapshot, and the `bengal.yaml` rewrite performed when registering a new docs version. (`#471`)
- Two silent `except` swallows in perf-gated paths now emit diagnostics instead of dropping facts. When restoring cached parsed links fails, the rendering pipeline's cache checker logs a `cached_links_restore_failed` warning with the full (untruncated) error and `reason="fallback_to_empty"` before falling back to an empty link set (mirroring the link-extraction handling in `core.py`). When the dev server's `BuildTrigger` cannot load the build cache while deciding whether a template change forces a full rebuild, it now logs a `template_cache_load_failed` debug breadcrumb (with the error and the action taken) instead of silently setting `cache = None`. (`#472`)
- De-vacuumed the tracks-rendering test's `hasattr(site.data, "tracks")` assertion (always True on a DotDict) into a real membership/value check, and added `AssetURLValidator` and `PerformanceValidator` to the health-validator contract suite (both are `BaseValidator` subclasses that the suite previously skipped; only `TemplateValidator` genuinely differs). The contract suite now exercises both classes and pins the mock site's `_last_build_stats` so `PerformanceValidator`'s real no-stats path is checked. (`#473`)


## [0.4.1] - 2026-06-15

### Fixed

- Re-armed the core composition-over-inheritance guard tests so they actually protect the live page object. The four mixin/rendering guards previously scanned `bengal/core/page/__init__.py` (which defines no page class) and trivially passed; they now scan the live `RuntimePage` in `runtime.py` and go red if it re-acquires a `*Mixin` base or hoists a `bengal.rendering` import to module scope. (`#433`)
- Wire the `data_table` template function into `register_all()` so templates calling `{{ data_table(...) }}` no longer raise an `UndefinedError` at render time. The function existed and was tested in isolation, but was never registered through the production rendering path. (`#434`)
- The `build_complete` plugin lifecycle hook now fires exactly once even when a mid-build phase raises, so plugin teardown callbacks (closing connections, writing summaries) always run. The original build error still propagates to the caller after the hook has executed. (`#437`)
- The health `--auto-fix` remediator now writes user content files atomically (write-temp-then-rename) instead of overwriting in place, so a crash or interrupt mid-write can no longer leave a source file truncated or partially written. (`#440`)
- Autodoc "View source" links now resolve to a real GitHub blob URL when `github_repo` is configured (under `[autodoc]` or at the top level), instead of always falling back to `#`. The default-theme autodoc header partial builds the URL from the repository and branch directly, expanding `owner/repo` shorthand and honoring `github_branch`. (`#441`)
- The default theme's article JSON-LD partial now emits valid structured data on doc pages. The `@type` field previously rendered an unquoted `TechArticle` token because `| tojson` bound only to the conditional's `else` branch, producing invalid JSON-LD that search engines and AI crawlers reject; the conditional is now parenthesized so the value is always quoted. (`#442`)
- The `build.render_isolation`, `build.render_isolation_threshold`, and `build.render_isolation_workers` options are now read from config instead of being silently swallowed, so opting into the experimental isolated render backend takes effect. The config validator also recognizes the `output_formats`, `link_previews`, `document_application`, `external_refs`, `content_signals`, `connect_to_ide`, and `structured_data` sections, eliminating spurious "unknown config section" warnings on valid configs. (`#446`)
- Restored the documented public import `from bengal.assets import AssetManifest` (the package previously re-exported nothing) and made the asset orchestrator honor the nested `[assets]` settings (`minify`, `optimize`, `fingerprint`) instead of the deprecated flat `*_assets` keys, so setting `minify = false` under `[assets]` now actually disables minification. (`#447`)


## [0.4.0] - 2026-06-12

### Added

- Autodoc now surfaces inherited members in the rendered output (#329). When
  `include_inherited` is enabled, members synthesized from base classes already
  carried `inherited_from`/`synthetic` metadata but it was never shown. `MemberView`
  now exposes `is_inherited` and `inherited_from`, and the default theme renders an
  "inherited from X" attribution badge that is visually distinct from native
  members. The `include_inherited` default is unchanged (stays opt-in/off). (`#autodoc-inherited-member-badges`)
- Autodoc now groups `@overload` definitions (#328). Multiple `typing.overload`
  stubs plus the concrete implementation of a callable are collapsed into a single
  documented member that lists every signature variant in source order, instead of
  N+1 duplicate peers that all collide on one `#name` anchor. The implementation's
  docstring is kept as the canonical description; an `overload` badge marks the
  member and each signature variant is rendered. Grouping runs before member-order
  sorting (so ordering stays stable and byte-reproducible) and applies to both class
  methods and module-level functions. The grouped metadata round-trips through
  `DocElement.to_dict`/`from_dict` and the content-hash stays stable. (`#autodoc-overload-grouping`)
- Autodoc now cross-links symbol names to their documented pages (#327). A new
  deterministic `SymbolResolver` service (`bengal/autodoc/symbol_resolver.py`) maps
  qualified and simple symbol names to a real, page-aware URL: modules resolve to
  their own page, while inline elements (classes, functions, methods rendered as
  cards on a module page) resolve to that module page plus a stable `#Card` anchor,
  so links never 404. Return types, parameter types, base classes, `See Also`
  targets, and bare `Name` code spans in docstrings are linked when they resolve to
  a documented symbol and degrade to plain text otherwise. Simple-name resolution is
  ambiguity-safe — a name shared by two documented symbols resolves to neither (a
  wrong link is worse than no link). The `See Also` section, previously dropped, now
  renders on Python module and class output. xref runs at render time (via the
  `xref_type` / `xref_docstring` template filters) so extraction and cache hashing
  stay unchanged, and xref output is byte-identical across rebuilds. (`#autodoc-symbol-xref`)
- Added a theming guide, `site/content/docs/theming/capabilities-vs-theme.md`
  ("What Bengal Provides vs What Your Theme Provides"), documenting the
  capability-vs-presentation boundary for theme authors. It diagrams the template
  resolution / fallback chain (site `templates/` -> theme chain via `extends`,
  child to parent -> the bundled `default` theme, always appended as the final
  filesystem fallback -> library provider loaders; first match wins, else
  `TemplateNotFoundError`) and explains the directive-vs-shortcode asymmetry:
  directives are a fixed, core-registered set that always render through a Python
  `render()` fallback even with zero theme templates (extensible only via plugins,
  not themes), whereas shortcodes are an open set with no engine fallback — a
  missing `shortcodes/{name}.html` passes the raw shortcode through (or errors in
  strict mode), making the default theme's shortcode templates the de-facto
  standard library. The page cross-links issues #335/#337/#338 as the path to
  portable capability templates. Also corrected `theme-creation.md`, which claimed
  the engine "automatically includes base CSS for all directives": that base CSS
  actually lives in the default theme at
  `bengal/themes/default/assets/css/components/`, so it is inherited only when a
  theme extends `default` (or is layered over it) — a non-extending theme must
  supply its own directive CSS. (`#capability-theme-boundary-docs`)
- Added a CI architecture-contract gate: the `Lint & Type Check` workflow now runs
  `lint-imports --config .importlinter` (new step in the `lint-and-type` job, feeding the
  `lint-ok` branch-protection gate), so any violation of the Site/Page/Section import
  contracts fails the build instead of only being catchable by running the linter locally.
  Also cleaned up the `.importlinter` baseline so the gate exits green: removed three stale
  `ignore_imports` entries that no longer matched any edge (the `bengal.core.site ->
  bengal.orchestration.feature_detector` import was removed in `#245`, and neither
  `bengal.core.page` nor `bengal.core.section.navigation` imports `bengal.core.site.context`),
  and added the live deferred `bengal.core.site -> bengal.orchestration.content` edge that the
  contract had been silently broken by. Tightened `RuntimePage._site` from `Any | None` to
  `SiteContext | None` to match `Section`, keeping the read-only Site coupling surface explicit. (`#lint-imports-ci-gate`)
- Added `tests/integration/test_nav_chrome_not_hoisted.py` — a discriminating guard that the
  default theme's navigation active-state is rendered per page and never hoisted as page-invariant
  chrome. It builds a multi-section site and asserts each section's page marks its own nav entry
  active (`/docs/` → "Documentation", `/blog/` → "Blog") and not the other's, so any future
  "render the chrome once" optimization (#348) that cached the page-scoped nav block as if it were
  site-scoped would fail here instead of silently shipping stale navigation. Backed by the
  investigation note `benchmarks/348-chrome-memoization-findings.md`. (`#nav-chrome-not-hoisted-guard`)
- REST autodoc schema pages now render advanced OpenAPI constructs as structured
  model documentation instead of dropping or flattening them (#285). `oneOf`,
  `anyOf`, and `allOf` render as labeled composition blocks; polymorphic schemas
  show their `discriminator` property and `value → schema` mapping; per-property
  validation constraints (`format`, `pattern`, numeric `min`/`max`/`multipleOf`,
  string `minLength`/`maxLength`, and array `minItems`/`maxItems`/`uniqueItems`)
  render as chips; and `nullable`, `readOnly`, `writeOnly`, and `deprecated`
  render as badges. Open and typed maps (`additionalProperties`) get their own
  section, primitive schemas surface their constraints and example, and a
  self-referential schema renders a bounded, readable "circular reference"
  indicator rather than an empty box or runaway recursion. Schema catalog tiles
  gained composition/discriminator/deprecated summary chips. Examples normalize a
  singular `example`, a 3.1 `examples` list, and a named `examples` map into a
  uniform rendering. The work is driven by additive normalization filters in
  `bengal/rendering/template_functions/openapi.py`
  (`schema_composition`/`schema_constraints`/`schema_flags`/
  `schema_additional_properties`/`schema_examples`/`schema_ref`), so simple schemas
  render byte-identically. The demo commerce spec marks server-assigned fields
  `readOnly` and credentials `writeOnly` to exercise the new rendering. Covered by
  unit tests for the normalization helpers (including circular-ref bounding and
  malformed-input robustness), template/CSS contract tests, and an end-to-end
  build of a fixture exercising every construct. (`#openapi-advanced-schema-rendering`)
- REST autodoc catalog pages gained first-class navigation interactions (#287),
  shipped as one lazy-loaded vanilla-JS enhancement (`api-catalog`, no npm). The
  API landing catalog and the schema index now have client-side filtering: typing
  in the filter box narrows endpoint cards and schema tiles by method/path/name,
  collapses empty tag groups, and announces a no-results state via `aria-live`.
  The left rail on the landing catalog and on the resource/schema/endpoint shells
  is now a scroll-spy: it marks the active section (`aria-current` +
  `.api-rail__link--active`) as you scroll and on direct hash navigation, honoring
  `prefers-reduced-motion` (the smooth-scroll gap `toc.js` leaves open).
  Operation paths gained copy buttons that ride the existing global `[data-copy]`
  handler, so base URLs, operation paths, and code samples now copy consistently,
  with a screen-reader announcement on copy. Filtering only toggles the `hidden`
  attribute and never reorders or removes anchored nodes, so deep links and the
  back button keep working; a hash navigation to a filtered-out section clears the
  filter to reveal it. Everything degrades gracefully with JavaScript disabled —
  rail links are real anchors and the filter input is simply inert. Covered by
  template/CSS contract tests, an end-to-end build that asserts the hooks render
  in output across the landing, tag, endpoint, and schema-index pages, and a
  fingerprinted-asset check. (`#openapi-catalog-navigation`)
- Added `benchmarks/probe_render_ceiling.py` — a process-isolation render *ceiling* probe that
  answers the prerequisite question of the render-scaling epic (#343/#345) on any box, macOS
  included: is the ~1.7x in-process free-threading plateau a fixable cross-thread coherency tax
  or a hardware ceiling? It runs K single-threaded render builds concurrently as separate
  processes (each with its own heap → zero cross-process refcount coherency) and compares
  aggregate throughput to the in-process thread pool. If processes scale ~K toward the P-core
  count while threads stay ~1.7x, the gap is pure coherency tax and software un-sharing can
  recover it; if processes also plateau, the ceiling is hardware-bound. Must be run on an idle,
  free-threaded (3.14t) box, median-of-N. No production code change. (`#render-ceiling-probe`)
- Added `benchmarks/run_clean_box.sh` — a turnkey "measure clean" driver for the render-scaling
  epic (#343/#344). On an idle Linux box with free-threaded 3.14t it bootstraps the toolchain,
  refuses to run under load (the epic's prime invariant — one load-inflated number was already
  retracted), reproduces the GIL=0/GIL=1 plateau, runs the process-isolation ceiling probe, and —
  only if the probe says the plateau is a fixable coherency tax — stages the `py-spy --native`
  attribution that names the dominant contended object. All results land as committable JSON under
  `benchmarks/clean_box_results/` alongside the box's CPU topology and loadavg. No production code change. (`#render-clean-box-runbook`)
- Added an **experimental, opt-in** isolated render backend that renders large
  cold builds across separate-heap worker processes (`fork`). It is **off by
  default** and gated behind `[build] render_isolation` (`off` | `auto` | `fork`),
  with `render_isolation_threshold` (default 400) and `render_isolation_workers`
  knobs. Cold CLI/CI builds only — the dev server and incremental builds keep the
  in-process thread path, and the backend falls back to threads on any failure, so
  it can never break a build. Rendered output is byte-identical to the thread path.
  This lands the foundation (transport, partitioning, serial merge, crossover gate,
  parity guard, benchmarking) for the heap-isolation epic; note the current
  fork-after-parse backend is not yet a guaranteed end-to-end speedup (it can
  regress very large builds via copy-on-write), which is why it stays opt-in. See
  issue #350. (`#render-heap-isolation`)
- Added `benchmarks/profile_render_native.py` and `benchmarks/PROFILE_RENDER_NATIVE.md` — a
  deterministic single-build driver and runbook for native profiling of the free-threaded render
  plateau (Step 0 gate of `plan/rfc-frozen-render-world.md`). The driver pins worker count, prints
  the cpu/wall signature + render-phase time so the plateau is confirmable on any box, and is meant
  to be wrapped by `py-spy --native` / `perf` on Linux to name the objects whose refcount/coherency
  traffic dominates the 8-worker build. No production code change. (`#render-native-profiling-harness`)
- Added an opt-in `reduce_taxonomy_from_metas` path to `assemble_render_plan` (epic #350
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
  generated/autodoc eligibility filter. (`#render-plan-barrier-taxonomy-reduce`)
- Added `bengal/snapshots/render_plan.py` — the `RenderPlan` map/reduce contract for the
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
  data-parity vs the live site (page-view map, taxonomy, xref index, related index, config). (`#render-plan-shard-contract`)
- Sharded the generated pages in the COW-free shard render backend (issue #350, Phase 2, saga
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
  idle-box A/B as 0.88× (pre-S13.4e, S17) → 1.23× shard-vs-thread (render phase 8.5s → 5.2s). (`#shard-generated-page-rendering`)
- Lay the foundation for an experimental shard-parallel cold build (issue #350,
  Phase 2; gated off by default, no change to the default build path): a
  deterministic pre-parse content-file sharder, a from-live-page map step, and
  shard-worker parse + render legs, so each worker can parse and render its own
  ~1/N of the corpus in its own heap (avoiding the copy-on-write tax that
  regressed the Phase-1 fork-after-parse backend). (`#shard-parallel-build-foundation`)
- Experimental COW-free shard-parallel render backend (`render_isolation=shard`, off by default): renders a cold build across separate-heap fork workers that each re-parse and render their own content shard, recovering the free-threading render plateau (~1.75x render-phase, ~+12% end-to-end on render-heavy content). Off by default — cold-build/CLI/CI only, render-heavy large sites; generated-page sharding (broad win) is still pending. (`#shard-render-backend`)
- Added `bengal/orchestration/render/isolated/worker_site.py` — `build_worker_site`, which
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
  pickle-round-tripped plan and matches the in-process build exactly. (`#worker-site-from-render-plan`)
- Extended `build_worker_site` (issue #350, Phase 2, sagas S13.3c+d) so a separate-heap shard
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
  byte-excluded but overlay-checked. (`#worker-site-render-world-reconstruction`)
- Added a repeatable manual visual-QA smoke checklist for the REST/OpenAPI autodoc
  pages (`docs/rest-autodoc-visual-qa-checklist.md`), covering the landing catalog,
  tag/resource, endpoint, schema-index, and schema-detail shells across light/dark
  mode and mobile/tablet/laptop/wide viewports, with explicit pass criteria for
  non-blank styled shells, rail reflow, scroll-spy plus hash/anchor routing,
  light/dark readability, keyboard focus states, and filter-preserves-deep-links.
  The checklist references the existing template-contract and end-to-end build
  tests as the automated half; an in-tree headless-browser screenshot harness is
  intentionally deferred to 0.5.x. (`#284`)
- Theme libraries can now declare version governance in their
  `get_library_contract()` -- a `contract_version` integer and a `requires`
  mapping of distribution name to PEP 440 specifier (e.g. `{"kida": ">=0.9.0"}`).
  Bengal enforces both during theme-library provider resolution at build start,
  raising a clear `BengalConfigError` (code `C003`) with the installed version and
  a fix command when a wheel was built against a newer contract or its required
  distributions are skewed, instead of surfacing a `BengalRenderingError` on the
  first rendered page. A `bengal[chirp]` extra pins `chirp-ui` alongside a
  matching `kida-templates` range. The default-theme path, which declares no
  governance fields, is unaffected (`#363`). (`#363`)
- Added `.github/CODEOWNERS` to record review routing and approval ownership across public API, CLI/config, rendering/themes, orchestration, docs, and release/dependency surfaces. (`#394`)
- The dev server now runs an HTTP serve-ability smoke check at startup (#398): once the server is listening it requests a known asset against the real serving setup and fails loudly with the buffer path, serving directory, and reason if it does not return 200, catching the #392-class serve-path failures before the first user request. (`#398`)
- Added a live `bengal serve` HTTP integration test (#399) that boots a real dev-server subprocess on a temp site, drives concurrent content/CSS edits while continuously fetching referenced CSS/JS/favicon assets, asserts they stay reachable across rebuilds and buffer swaps, and verifies a broken save preserves the last-good output. (`#399`)
- The dev server's double-buffer manager now warns loudly at construction when a served buffer path contains a hidden (dot-prefixed) component (#400), pinning the Pounce static-handler constraint (lbliii/pounce#74) at the integration boundary so a future hidden serving path fails visibly instead of as mysterious runtime 404s. (`#400`)

### Changed

- Theme-library provider resolution is now cached per `(site_root, theme_chain)`.
  `resolve_theme_providers()` was previously called on two independent build paths
  with no shared state — asset discovery and Kida engine loader/filter setup — and,
  under the #350 shard-parallel render backend, once per worker-thread pipeline.
  Each call did `importlib.import_module` plus convention-hook probing
  (`get_library_contract` / `get_loader` / `static_path` / `register_filters`) for
  every declared library, rebuilding the contract strictly more than twice per
  build. A module-level `LRUCache` (RLock-backed, free-threading-safe under CPython
  3.14t) now collapses all of these to a single resolution that every caller and
  shard thread shares; the resolved tuple of frozen+slots providers is read-only
  and safe to share. The cache is registered with the central cache registry
  (invalidated on full rebuild / config change / build start) so theme.toml
  `libraries` edits in long-lived dev-server/incremental processes re-resolve.
  The default-theme happy path is unchanged: a theme that declares no libraries
  caches the empty tuple `()` and short-circuits identically, keeping output
  byte-identical (verified against baseline on the default-theme path). See #365. (`#cache-theme-provider-resolution`)
- The bundled `default` theme no longer ships dead or demo-only assets: the
  39-file `icons_backup/` directory, two orphaned holographic-card demo pages,
  and several stale architecture/process docs are removed. The experimental
  holographic-card CSS is no longer force-loaded on every site — it is now
  included only when a page actually uses holo classes, via the existing CSS
  feature detection. Pagination and table-of-contents active-state glow
  animations now honor `prefers-reduced-motion`. (`#default-theme-stabilization`)
- Render-time asset-dependency extraction now uses a fast single-pass scanner instead
  of the stdlib `HTMLParser`, cutting per-page extraction ~4x (4.84 → 1.19 ms/page)
  with a byte-identical dependency set (verified by an adversarial parity suite). The
  post-render asset audit also memoizes existence checks. Benchmark docs were corrected
  to committed baselines (the previous "256/373 pages/sec" figures were unbacked), and
  the `gil_speedup` harness now reports a full per-phase ledger. (`#fast-asset-extraction`)
- Warm incremental builds now update the provenance dependency reverse-map *incrementally*
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
  non-deterministically. The reverse map now lists every page that consumes an input. (`#incremental-dependency-index`)
- OpenAPI autodoc consolidated tag pages now render full endpoint reference
  sections with parameters, request bodies, responses, and request/response code
  examples, and the default theme REST API layout has a denser modern explorer
  presentation with scoped tabs, copy controls, and sidebar filtering. (`#openapi-autodoc-reference`)
- Removed the dead pre-shell REST/OpenAPI layout CSS from the default theme's
  `autodoc.css` (~1450 lines): the Mintlify explorer grid, the three-column
  `.api-explorer` layout, the single-column `.api-reference` layout, the standalone
  `.api-home` landing page, and the `.api-playground` bar. These layers were
  superseded by the bespoke `.api-catalog-app` / `.openapi-app` shell, which now
  owns every rendered REST page — verified by a zero-occurrence grep of all
  issue-named legacy classes across the generated `bengal-demo-commerce` site and a
  byte-stable live-class histogram before/after the change. Each deletion was
  cross-checked against the emitted-class set so live shell selectors (and shared
  typography/card groups) are preserved; structural rules (`#main-content` reset,
  global `.breadcrumb__item`) are untouched. Two orphaned templates
  (`partials/playground-bar.html`, the superseded `partials/endpoint-header.html`)
  were also deleted, and a discriminating contract test now fails if any legacy
  selector reappears. (`#openapi-css-legacy-residue-removed`)
- OpenAPI autodoc now generates an individual three-column explorer page for
  every endpoint by default (the `consolidate` option defaults to `false`), so
  endpoint cards link to real pages instead of dead `#anchors` and schema pages
  render their properties, enums, and examples. Untagged endpoints nest under a
  synthetic `default` tag section so their page URL agrees with their section
  placement. Set `consolidate: true` to keep the previous consolidated
  reference-view behavior. (`#openapi-endpoint-pages`)
- Retire the public `bengal.Page` and `bengal.core.Page` compatibility re-exports
  plus the `Page.create_virtual()` compatibility constructor, and reduce internal
  concrete `Page` coupling by routing page construction through page-like records
  and the remaining SourcePage adapter boundary. Discovery now resolves i18n
  metadata before creating `SourcePage` records instead of mutating adapted pages
  afterward. Non-compatibility tests no longer use local `Page`-named doubles that
  obscure the remaining production adapter/class boundary. The remaining adapter
  now lazy-loads the legacy class so importing content discovery helpers does not
  load `bengal.core.page`. Tests now import Page submodules directly and guard
  against new package-root imports from `bengal.core.page`. Raw source access now
  flows through a content-owned helper instead of requiring `_source` on the
  `PageLike` protocol. Section access now flows through core section helpers
  instead of requiring `_section` on `PageLike`, and directive link collection now
  flows through rendering helpers instead of requiring `_directive_links`.
  Parsed content caches now stay out of `PageLike`; AST, TOC, excerpt, and meta
  description state are handled by compatibility/cache helpers while the legacy
  mutable page adapter remains.
  Section archive context now stays out of `PageLike`; existing section indexes
  receive `_posts`, `_subsections`, `_paginator`, and `_page_num` through metadata
  instead of mutable page slots.
  Autodoc fallback tagging now stays out of `PageLike`; fallback template markers
  are recorded through metadata instead of mutable page slots.
  Pre-rendered virtual page HTML now stays out of `PageLike`; rendering helpers
  own access to `prerendered_html` while the legacy mutable page adapter remains.
  Legacy mutable page site context now stays out of `PageLike`; content discovery
  and orchestration use page-site helpers while the compatibility adapter remains.
  Analysis graph tests now use hashable page-like mocks instead of constructing
  legacy mutable pages for graph-only behavior.
  Cache query-index tests now use page-like fixtures instead of constructing
  legacy mutable pages for index-only behavior.
  Content-type, related-posts, and taxonomy-incremental orchestration tests now
  use hashable page-like mocks instead of constructing legacy mutable pages.
  Redirect postprocess tests now use local page-like fixtures instead of
  constructing legacy mutable pages for alias behavior.
  Render, taxonomy, section, and incremental orchestration tests now use the
  shared page-like mock instead of constructing legacy mutable pages for
  orchestrator inputs.
  Nav-tree tests now use the shared page-like mock instead of constructing legacy
  mutable pages for navigation behavior.
  Section sorting, hashability, index-collision, page-like input, and versioning
  tests now use shared page-like mocks instead of constructing legacy mutable
  pages for hierarchy behavior.
  Cascade and cascade-snapshot tests now use shared page-like mocks instead of
  constructing legacy mutable pages for section cascade behavior.
  Section ergonomic helper tests now use shared page-like mocks instead of
  constructing legacy mutable pages for recent-page, content-page, and
  tag-listing behavior.
  Page visibility logic now has Page-package-independent helpers used by core
  page caches and visibility tests, reducing dependence on legacy Page visibility
  properties.
  Page visibility tests now use shared page-like mocks and the visibility helper
  API instead of constructing the legacy mutable Page adapter.
  Href and section page URL tests now use shared page-like URL mocks backed by
  rendering URL helpers instead of constructing the legacy mutable Page adapter.
  Page URL cache-regression tests now assert the rendering URL helper cache names
  through the shared page-like URL mock instead of constructing the legacy mutable
  Page adapter.
  The standalone section-navigation edge case now exercises navigation helpers
  with a shared page-like mock instead of constructing the legacy mutable Page
  adapter.
  Navigation tests now build breadcrumb and parent assertions through section and
  page navigation helpers with shared page-like mocks instead of constructing the
  legacy mutable Page adapter.
  Component model metadata-normalization tests now exercise `build_page_core()`
  directly instead of constructing the legacy mutable Page adapter.
  Computed page metadata tests no longer duplicate age, author, and series helper
  coverage through the legacy mutable Page adapter.
  Page metadata helper tests now cover generated, assigned-template,
  content-type, and variant behavior through metadata helpers instead of the
  legacy mutable Page adapter.
  Page record migration tests now use the canonical SourcePage-backed test-page
  adapter for bridge-retirement coverage instead of constructing the legacy
  mutable Page adapter directly.
  Hashability and deduplication tests now use source-path-hashable page-like
  mocks instead of constructing the legacy mutable Page adapter for set and dict
  identity behavior.
  Obsolete legacy Page cached-property tests were removed; raw source,
  word-count, reading-time, meta-description, and excerpt behavior is covered by
  the content, computed-function, and rendering helper tests.
  Obsolete legacy Page section-reference tests were removed; section helper,
  registry, and virtual-section behavior is covered outside the mutable Page
  descriptor surface.
  PageInitializer tests now build pages through the canonical SourcePage-backed
  test-page adapter instead of legacy mutable Page constructor keyword names.
  Frontmatter integration tests now build pages through the canonical
  SourcePage-backed test-page adapter, leaving the legacy mutable test-page
  factory isolated to the shared compatibility helper.
  The unused legacy mutable test-page factory was removed; tests now use
  SourcePage-backed helpers or page-like mocks.
  Production `page_from_source_page()` now returns a SourcePage-backed
  `RuntimePage` from the core page compatibility boundary instead of constructing
  the legacy mutable `Page` class.
  The legacy mutable `Page` class module, `bengal.core.page.legacy`, has been
  deleted; `bengal.core.page` remains a helper package and does not export
  `Page`. (`#page-import-coupling`)
- Strengthened page-record migration guardrails by adding parsed-state test helpers, routing more test setup through parsed-record adapters, and documenting the SourcePage-to-Page compatibility boundary for generated-page examples. (`#page-record-test-boundaries`)
- The post-render asset audit (`find_missing_local_asset_references`) now scans output
  HTML in parallel across a `WorkScope` for larger builds, with byte-identical findings
  (per-file results are re-indexed to preserve document order; small sites stay serial).
  On content-heavy sites — docs/autodoc with large pages — this audit was re-reading and
  regex-scanning big rendered HTML serially and dominated the build (~47% of an autodoc
  build); parallelizing it cut that phase ~5x (1.80s → 0.35s) and the overall autodoc build
  ~1.7x (3.8s → 2.2s, ~26 → ~45 pages/s) on a 5P+6E machine. Unlike the render phase, this
  work is per-file independent (read + regex on a thread-local string), so it scales with
  free-threading rather than being bound by shared-object coherency cost. (`#parallel-asset-audit`)
- Related-posts computation is dramatically faster on large sites. The candidate
  filters (skip generated/home/section-index pages) and the deterministic
  tie-break key are now computed once per build instead of for every
  (page × tag × candidate) in the scoring loop. On a 4,288-page site this cut the
  related-posts phase from ~24s to ~3s (~8×) with byte-identical output. See #350. (`#related-posts-cooccurrence-index`)
- Per-page rendering is faster: `RuntimePage.metadata` is read hundreds of times per
  page, and each read previously recomputed the section path relative to `content/`
  via `Path.relative_to` before consulting its cache. The relative section path now is
  memoized per site (invalidated when the section changes), eliminating ~265k
  `Path.relative_to`/`pathlib` calls on a 300-page docs build and cutting single-thread
  render time ~27% (13.4 → 9.7 ms/page, median of 5 sequential builds). Output is
  byte-identical (verified by a timestamp-normalized full-tree comparison: HTML trees
  hash-equal before/after). (`#render-metadata-section-path-memo`)
- The experimental shard-render backend's byte-parity tests now run as nightly `known_gap` signal instead of gating every pull request. The backend remains opt-in and off by default (`render_isolation="off"`), and its byte-output is order-dependent-flaky under randomized test ordering, so a divergence in those tests was intermittently failing unrelated PRs. The functional shard tests (page bodies filled, all pages covered/rendered, cross-shard related content resolved) stay as merge gates; only the byte-equivalence/determinism checks were moved to the non-gating lane. The remaining shard output-determinism work is tracked and must close before the backend is ever enabled by default. (`#376`) (`#shard-parity-degate`)
- Completed OpenAPI autodoc Phase 2. Endpoint pages now render a cross-endpoint
  sidebar that marks the current endpoint with both an `--active` class and
  `aria-current="page"`. The endpoint/schema templates were migrated from
  Jinja-era `{% include %}` partials to Kida `{% def %}`/`{% slot %}` components
  (`_components.html`, recursive `_schema.html`) with no change to rendered
  output. Multi-tag endpoints are now cross-listed under every one of their tag
  sections (previously a secondary tag that also owned its own endpoint silently
  dropped the cross-listed ones), still backed by a single canonical page, and
  their header tag chips link to the correct per-tag section URL. (`#openapi-autodoc-phase2`)
- Default theme: corrected the experimental-CSS documentation (`EXPERIMENTAL.md`) to describe holo styles as feature-detected/opt-in via the CSS manifest rather than "loaded by default" — matching the opt-in behavior shipped in #367 (documentation only; no behavior change). (`#360`)
- Decomposed the cross-reference index builder into focused per-page helpers and consolidated the two divergent anchor-collision branches into one warning site, preserving identical heading (keep-existing) and target-directive (precedence) resolution behavior. (`#380`)
- Consolidated the four drifting free-threading/GIL-detection helpers into the
  single canonical `bengal.utils.concurrency.is_gil_disabled()` (#381). The local
  copies in the render orchestrator, dev-server build executor, and social-card
  generator (two of which lacked the `sysconfig` fallback) now delegate to the
  canonical check, so executor selection and build behavior stay consistent across
  the build, dev-server, and render paths. (`#381`)
- Tightened import-linter Contract 1 to track the `bengal.core.site -> bengal.rendering.template_functions.version_url` edge so the core/rendering boundary can no longer erode without CI signal. (`#383`)
- Standardized the CLI render-format vocabulary (Finding 25): `json` is now the machine-readable token on every command, each command's `output_format` Description follows one phrasing template, and the injected envelope `--format` row is suppressed in `--help` on commands that already carry their own format flag — so `bengal inspect page --help` (and its siblings) show exactly one format option instead of two colliding ones. The `-o FILE` serialization path is unchanged. Genuinely-distinct human renders (config `yaml`, version/perf `table`, directive `html`, graph `mermaid`/`dot`) stay available and are allow-listed in `bengal/cli/format_options.py`. `bengal version diff` renames its `--output` format flag to `--output-format` for consistency with the other twelve render-format commands. (`#387`)
- Refactored the dev-server rebuild pipeline: `BuildTrigger._execute_build` is now a thin strategy-dispatch shell delegating to named `_run_reactive_build`/`_run_warm_build` helpers, the double-buffer prepare/swap/resync invariant (including the #315 `asset-manifest.json` always-sync) is centralized in a `_DoubleBuffer` context manager, and the warm-build path now constructs the shared `BuildResult` instead of an inline per-build DTO (#390). Behavior is unchanged. (`#390`)

### Removed

- Removed the experimental in-repo `chirpui` bridge theme so Bengal bundles a
  single stable `default` theme. The bridge shell (24 templates, a small Bengal
  bridge stylesheet, a bridge JavaScript file, and a `libraries = ["chirp_ui"]`
  `theme.toml`) only re-exposed the generic theme library asset contract through a
  bundled slug. Component-library integration such as Chirp UI is now delivered
  through external theme packages (for example the chirp_theme package) using the
  same library-provider contract, which remains covered by the provider and
  metadata contract-shape tests. (`#remove-chirpui-bridge`)
- Removed six permanently-skipped "classic fallback" theme tests that encoded an abandoned design and relied on config keys the schema does not accept. (`#382`)
- Removed dead code and stale metadata (empty `bengal.experimental` package, false `bengal.build.__all__` entries, the unused `AutodocTracker.get_affected_autodoc_pages` method) and fixed a stale import that aborted collection of the build-initialization test module. (`#386`)

### Fixed

- CLI help, bare command groups, `--version`, and ordinary single-command
  execution now avoid full Milo parser construction. Bengal resolves only the
  selected command schema unless a full-tree built-in mode such as `--llms-txt`,
  completions, or MCP needs the entire command registry. (`#cli-help-startup`)
- The dev server no longer lets `asset-manifest.json` drift between its two output
  buffers. The double buffer seeds the next staging buffer from the active one
  using only the previous build's changed outputs, but the asset manifest describes
  the *currently served* buffer and is never rewritten on a content-only rebuild —
  so it never appeared in the changed-output delta and could fall a generation
  behind. A buffer that became active carrying a stale manifest could omit entries
  for assets it actually held (`asset_url` failing to resolve them) and make
  `inspect_asset_outputs` mis-report completeness — the residual dev-server
  mechanism behind #130's intermittent "unstyled, fixed by restart" symptom that
  the build-API fix (#313) did not cover. `prepare_delta_staging` now takes an
  `always_sync` set and the dev server passes `asset-manifest.json`, so the manifest
  is re-seeded from the active buffer on every rebuild and both buffers stay
  consistent. Adds the first dev-server-realistic buffer/swap/delta integration
  harness. (#315) (`#dev-server-manifest-buffer-sync`)
- Fixed a dev-server (`bengal serve`) crash where serving a static asset (CSS/JS/font) could
  abort the worker with `BlockingIOError: [Errno 35] Resource temporarily unavailable`. The dev
  server disables compression so live-reload streams immediately, which makes Pounce advertise
  its zero-copy `pounce.sendfile` extension; Pounce 0.7.1's sendfile path runs `os.sendfile` in
  a thread executor without handling `EAGAIN` on the non-blocking socket, so a full send buffer
  crashed the transfer (seen on macOS + free-threaded CPython 3.14t). Bengal now opts out of the
  `pounce.sendfile` extension for dev static serving, falling back to chunked ASGI body writes
  that respect async backpressure. The production-like preview server keeps compression (and so
  never advertised sendfile) and is unaffected. Tracked upstream as
  [lbliii/pounce#72](https://github.com/lbliii/pounce/issues/72). (`#dev-server-sendfile-eagain`)
- Fixed a directive render-cache key collision in the Patitas backend. The
  structural fingerprint only recursed through `block.children` and probed a
  hand-picked attribute list, so directives whose bodies were lists, tables, or
  fenced code (which patitas stores in `.items`/`.head`/`.body` and source
  offsets) collapsed onto one cache key — the first render's HTML was then served
  for all later ones. On versioned sites (where the directive cache is enabled)
  this could render stale, duplicated directive output. The key now walks every
  declared slot across each node's MRO, so distinct directives can no longer
  collide. (`#directive-cache-key-collision`)
- Cleared the dogfood-site health blockers that were obscuring REST autodoc QA
  (#288). The `important` admonition (a standard docutils/MyST type) is now
  registered, fixing the H201 "Unknown directive" error and the cascading
  "PosixPath is not JSON serializable" error it triggered. Six icon names
  referenced by docs content (`external`, `languages`, `python`, `robot`,
  `stethoscope`, `arrows`) now resolve: `external` was aliased to a non-existent
  `arrow-square-out` (in both `ICON_MAP` and `theme.yaml`) despite `external.svg`
  existing, and the other five gained aliases to existing theme SVGs. The
  `/docs/content/i18n/` URL collision is resolved by renaming the standalone
  `i18n.md` to `multilingual.md` so it no longer collides with the canonical
  `i18n/` section index. Thirty-one real broken navigation links across the docs
  were corrected (the dominant bug was relative `./sibling` / `.md`-suffixed links
  that don't resolve under pretty URLs — corrected to the `../sibling/` form), and
  the stale `/assets/css/style.css` reference in two self-contained demo HTML files
  was removed. Build health quality rose from 60% (Fair) to 80% (Good); broken
  internal links dropped from 43 to 9 — the remaining nine are illustrative example
  paths inside autodoc'd Python docstrings (e.g. the link-validator module's own
  docstring demonstrates `./sibling.md`) and one shortcode-syntax example, not real
  navigation, and are left as documented false positives. Added guard tests for the
  admonition registry and icon aliases. (`#dogfood-health-blockers`)
- Incremental builds no longer shrink the asset manifest when only some assets are
  reprocessed. `_write_asset_manifest` rebuilt `asset-manifest.json` from just the
  assets processed that run, so editing a single asset (a *partial* asset
  incremental) dropped every unchanged entry — leaving a manifest with one entry.
  That re-introduced the #130 failure class: a small-but-complete manifest makes
  `inspect_asset_outputs` report a vacuously "complete" tree, blinding the
  incremental reprocess safety net so a later missing CSS/JS output goes
  unrecovered until a full rebuild. Incremental builds now *merge* — prior entries
  whose output file still exists are carried forward, then the run's freshly
  processed assets are overlaid (current entries win). Full builds still rebuild
  from scratch, so they stay orphan-free. (#314) (`#incremental-asset-manifest-partial-merge`)
- Incremental builds no longer corrupt the asset manifest. When a build had no
  assets to process (e.g. a content-only edit during `bengal serve`), the asset
  phase overwrote `asset-manifest.json` with an empty manifest. A present-but-empty
  manifest makes the output-integrity check (`inspect_asset_outputs`) report a
  vacuously "complete" asset tree (manifest present, zero entries, zero missing),
  which blinded the incremental reprocess safety net on later builds — so if a CSS
  or JS output went missing it was never regenerated until a full rebuild
  (restart). The asset phase now preserves the existing manifest when there is
  nothing to reprocess (the output tree is unchanged, so the manifest is still
  accurate); the empty baseline is only written when no prior manifest exists.
  Adds theme-provided-CSS hot-reload regression coverage. (#130) (`#incremental-asset-manifest-preserved`)
- Warm parsed-cache hits now reuse cached text metrics, AST persistence reuses the Patitas document parsed during TOC rendering instead of parsing the page a second time, excerpt generation avoids scanning full HTML bodies after it has enough plain-text words, generated-page caches miss conservatively when member content hashes are unavailable while reusing page-level content hashes when present, provenance caches persist a read-only dependency index for conservative data/template detector lookups, page provenance records capture render-observed template/data inputs for that index, provenance/build-cache recovery is more observable, output cache keys are normalized, and Patitas exposes a tested parser-level batch TOC primitive for future render batching. (`#parsed-cache-warm-optimizations`)
- Builds are now byte-reproducible: identical content produces identical output
  across repeated builds and across worker counts. Three sources of
  thread/hash-dependent output were eliminated — related-posts now break score ties
  by a stable key, tag listings sort ties deterministically, and tag accent colors
  use a stable digest instead of Python's per-process-randomized `hash()`. This makes
  parallel (free-threaded) output trustworthy for caching, CDNs, and version control. (`#reproducible-builds`)
- Fixed a latent bug where the internal taxonomy snapshot (`SiteSnapshot.taxonomy`)
  was always empty because `_snapshot_taxonomies` mis-iterated the `{name, slug,
  pages}` term dict, leaving the renderer's lock-free tag-page fast path dead. Tag
  pages now resolve through the corrected snapshot with byte-identical output, and
  per-language tag pages under i18n `share_taxonomies = false` correctly list only
  their own language's posts. (`#taxonomy-snapshot-populated`)
- The shared test suite no longer leaks the active plugin registry between tests.
  A build sets the `_active_registry` contextvar (`set_active_registry()`) but
  never resets it, so any test that ran a build leaked its `FrozenPluginRegistry`
  into the contextvar for every later test sharing the same `pytest-xdist` worker.
  Under random test ordering this caused intermittent failures in
  `test_active_plugin_registry_is_context_scoped`, which expects the ambient
  registry to be `None`. The autouse `reset_bengal_state` fixture now clears the
  contextvar before and after each test. (`#test-isolation-active-plugin-registry`)
- Warm (incremental) builds now keep `rss.xml` and the prebuilt Lunr
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
  every assertion behind `if rss_path.exists():`. (`#warm-artifact-repair-rss-searchindex`)
- Fixed a dev-server (`bengal serve`) bug where the theme would repeatedly "drop" to unstyled
  HTML for long stretches while editing — every CSS/JS/font/icon request returning `404` even
  though the files were present on disk. The double-buffer stages builds in `<root>/.bengal/staging`
  and serves from whichever buffer is active after a swap; Pounce's static handler rejects any path
  whose resolved absolute path contains a hidden (dot-prefixed) component, so whenever the
  `.bengal/staging` buffer was the active one (≈half the time under rapid edits) it 404'd *every*
  asset — while HTML kept loading (it is served by Bengal's own `_serve_static`, which has no such
  restriction), producing the characteristic fully-rendered-but-unstyled page. Bengal now detects a
  hidden serving directory and routes asset requests around Pounce to `_serve_static` (correct
  content types, no HTML injection for non-HTML), so assets serve regardless of which buffer is
  active. A live reproduction went from 53% of CSS requests 404ing to 0%. Also covers the rarer
  case of a project rooted under a dot-directory. Tracked upstream as
  [lbliii/pounce#74](https://github.com/lbliii/pounce/issues/74). (`#dev-server-hidden-buffer-asset-404`)
- Use a notebook's first H1 heading as the page title when no explicit notebook
  title is present, preserving the visible title after duplicate H1 stripping. (`#notebook-title-from-h1`)
- The snapshot parse cache now keys on the parser version and resolved config hash, so a parser upgrade or a markdown/directive config change forces a full re-parse instead of silently replaying byte-stale parsed HTML on the next build. (`#377`)
- Warm autodoc cache-hit builds no longer crash on a present-but-unreadable source file; both the warm and cold dependency-registration paths now share one OSError-guarded helper and degrade gracefully with an `autodoc_source_stat_failed` warning. (`#378`)
- The rendered-output cache now resolves template/partial dependency keys against the site root (mirroring the parsed-content cache) instead of the process working directory, so a changed or deleted template dependency correctly invalidates the cached HTML. (`#379`)
- Hardened the remaining vacuous test-quality guards from the assertion-hardening saga: the three sibling meta-guards that called `pytest.skip()` on threshold breach (going green exactly when the suite was at its worst) are now committed-ceiling ratchets that fail on regression, the four href-rendering integration tests now render `page.href`/`section.href`/nav-item `href`/the `href` filter and assert on the resolved output instead of `assert True`, the incremental asset-manifest test on the #130 hot path now asserts the manifest is written, its entry set preserved, and the `style.css` fingerprint changes after a CSS edit, and the two `TrackValidator._get_page` tests now assert the returned `Page` identity instead of discarding it (`#384`). (`#384`)
- Silent exception swallows (`noqa: S110`/`S112`) across Bengal now carry a reason and, at meaningful subsystem boundaries, emit a `logger.debug` diagnostic; the asset-URL and autodoc health validators surface a nonzero skipped-file count instead of reporting a false all-clear, and a pre-commit guard now requires a justification on every such swallow. (`#385`)
- The root `bengal --help` now lists `preview` under "Core workflow" and no longer advertises the hidden `health` legacy alias as a separate command, eliminating the stray "Other" section. A guard test keeps the curated help sections in sync with the live command registry. (`#387`)
- Rewrote the custom-directives extension guide and quick-start to use the real public `bengal.parsing.backends.patitas.directives` API (the `DirectiveHandler` protocol, frozen `DirectiveOptions`, and `DirectiveRegistryBuilder`), replacing the nonexistent `bengal.directives` / `BengalDirective` / `DirectiveToken` symbols; a new docs-snippet import test guards the guide imports in CI. (`#388`)
- Corrected docs accuracy: the README parser table now reflects real runtime availability (only Patitas is built-in, Python-Markdown needs `pip install markdown`, Mistune is a deprecated alias), the Philosophy section honestly describes the tracked-debt model instead of claiming zero compatibility shims, and the benchmarks page labels its render-light/warm-cache pages-per-second figures against the committed ~18–20 pages/s baseline. (`#389`)
- Kida template render errors are now classified through the canonical `ErrorClassifier`: a `None` filter/function (`'NoneType' object is not callable`) reports `R015` instead of the mislabeled `R008`, keeping the live render path and the error-classifier in sync. (`#391`)
- Fixed `PatitasParser.render_ast()` so round-tripping `parse_to_ast()` output (including headings, links, lists, and code blocks) renders HTML instead of raising `TypeError: Document.__init__() missing ... 'location'`, honoring the parser's `supports_ast=True` contract. (`#393`)
- Shared documentation pages (under `_shared/`) now appear in every version-specific navigation tree (#395). Previously they were discovered and documented as shared but were silently absent from each version's NavTree, since they carry `version=None` and are not attached to any versioned section. (`#395`)
- Autodoc members that do not get their own page (Python classes, functions, and
  methods; CLI options) now receive an on-page anchor `href`
  (`<parent-page>#<card>`) instead of a dangling `/api/<module>/<member>/` page
  URL, so templates using `{{ child.href }}` no longer emit broken internal links. (`#401`)
- The experimental shard render backend (`BENGAL_RENDER_ISOLATION=shard`) now emits per-page JSON output-format files for content pages that live inside a section, matching the default thread build. Previously a sectioned page's navigation lookup raised a `TypeError` against its frozen section snapshot inside the per-page JSON accumulator; the broad `except` swallowed it and silently dropped the whole page from accumulation, so its `index.json` was never written. The section page-index is now keyed by stable `source_path` (resolving live pages against snapshot sections) and a section index page correctly reports no in-section prev/next. (`#418`)
- The experimental shard render backend now renders an authored `type: blog` section index (`content/<section>/_index.md`) byte-identically to the thread build — its post-listing `<time>` date elements no longer diverge. A worker's section listing is now canonicalised to the same build snapshot the thread path resolves through, instead of the RenderPlan's body-free `PageView`s (which exposed a `date` the thread path's `PageSnapshot` does not). (`#419`)


## [0.3.3] - 2026-05-23

### Added

- Added `bengal audit` to scan generated artifacts for missing internal file
  references with Kida-rendered and JSON output. (`#artifact-audit-command`)
- Add a pre-discovery build change census for no-op and single-edit rebuilds. (`#build-change-census`)
- Added a separate bundled `chirpui` theme that renders Bengal pages with Chirp UI macros and assets without modifying the existing `default` theme. (`#chirpui-theme`)
- Added Git versioning configuration for building the latest branch plus the newest matching release tags. (`#git-previous-tags`)
- Added `bengal preview`, which runs a complete build and then serves the completed
  output directory through Pounce static handling for production-like local checks. (`#preview-static-serving`)
- Added a version-aware `url_for` template helper for pages, sections, snapshots, and literal paths. (`#render-url-for`)
- Add theme library asset contracts with provider-managed CSS/JS emission, tag attributes, runtime metadata, strict missing-asset diagnostics, manifest provenance, and vendor-facing documentation. (`#theme-library-assets`)

### Changed

- Route health link target discovery through an explicit generated artifact inventory when available. (`#artifact-inventory-link-registry`)
- Sites can now opt into Atom feed generation with `generate_atom` or `features.atom`, producing `atom.xml` alongside existing RSS support with language-specific self links. (`#atom-feed`)
- Made additional rendered output, special page, optimized CSS, and output-format sidecar writes atomic so interrupted builds do not leave partial files behind. (`#atomic-output-writes`)
- Build requests now carry an explicit completion policy so `bengal serve` can distinguish browse-ready work from complete deployable builds. (`#build-completion-policy`)
- Post-render build work now has explicit finalization task contracts, separating serve-ready, artifact, quality, and persistence responsibilities. (`#build-finalization-task-policy`)
- Build summaries now use recorded phase timings for colder builds, including previously hidden parsing, snapshot, filtering, artifact inventory, cache-save, and stats work. (`#build-phase-accounting`)
- Scoped active plugin and effect-tracing state to the current build context so concurrent builds do not share dependency or extension state. (`#build-scoped-state`)
- Page artifact persistence now rewrites only shards affected by changed or deleted page artifacts during warm builds. (`#cache-dirty-page-artifact-shards`)
- Build cache saves now split parsed content, rendered output, validation results, and synthetic pages into separate hot-store files to reduce the main cache payload rewritten after builds. (`#cache-split-hot-stores`)
- Render debug and inspect report summaries through shared Kida templates instead
  of forwarding preformatted summary strings to the CLI. (`#cli-debug-report-output`)
- Bengal's Milo CLI bridge now renders root, group, and every registered command help path through Bengal-owned Kida templates backed by Milo's command registry, routes semantic CLI messages, structured logger console events, phase summaries, and runtime output call sites through `bengal.output.get_cli_output()`, aggregates repeated missing-icon, unknown-config, valid-track, navigation, taxonomy, menu, cache, performance, and rendering health messages into compact notices, renders URL collisions from structured records instead of raw multi-line strings, gives `bengal clean` branded Kida output, adds reusable command empty/list/error templates for plugin, content, cache, theme, config, codemod, content schema, i18n, and version output states, gives `bengal build`, `bengal serve`, `bengal check`, and `bengal audit` ASCII-safe `--style` output through scoped output modes that do not leak between embedded command invocations, gives check/audit verdict-first reports with `--focus` and bounded `--limit` output where findings can be long, annotates command read/write intent for MCP clients, documents the built-in `--llms-txt`, `--completions`, and MCP modes, keeps CLI output/scaffold writes atomic, and guards Bengal package code against direct terminal writes outside the live progress cursor-control sink. (`#cli-milo-builtins`)
- Route performance reporting and fallback live-progress output through the
  shared CLI output bridge instead of direct terminal writes. (`#cli-observability-output`)
- Add a unit-test guard that blocks direct terminal writes in CLI-facing Bengal
  packages so output continues to route through the shared CLI renderer. (`#cli-output-boundary-guard`)
- Route CLI progress, prompts, interrupt messages, and Milo compatibility output
  through the shared `CLIOutput` bridge so CLI utility imports and output package
  imports use the same renderer singleton. (`#cli-output-bridge`)
- During dev-server background completion, requests for missing generated artifacts now return a short retryable response instead of looking like ordinary missing pages. (`#deferred-artifact-response`)
- Git versioned builds now prune previously managed stale version outputs, preserve latest assets when merging older staged outputs, accept `releases/tags` and `git-tags` as aliases for tag-based previous-version discovery, make `git.latest` override duplicate branch-pattern discoveries, show the version selector on generic versioned pages, cover repository-root builds where the Bengal site lives in a subdirectory, and dogfood automatic release-tag versioning on Bengal's own docs site. (`#git-version-hardening`)
- Kept `bengal health` as a compatibility alias for `bengal check` while the new
  artifact-focused `bengal audit` command is introduced. (`#health-command-alias`)
- Invalidate cached Links health results when rendered URLs, anchors, source paths, or auxiliary outputs change. (`#health-link-cache-registry-fingerprint`)
- Cache repeated health link-validation results during each run and report cache hit stats in validator output. (`#health-link-result-cache`)
- Teach the Links health validator to validate only scoped changed pages on incremental runs while preserving cached unchanged-page findings. (`#health-links-incremental-scope`)
- Health check reports now expose a versioned result envelope used by Milo/Kida
  validation output; artifact audit uses its own versioned envelope. (`#health-report-envelope`)
- Incremental health checks can now reuse a cached whole-report result when source, configuration, and link-registry inputs are unchanged. (`#health-report-reuse`)
- Add internal scoped validation plumbing so incremental health checks can pass changed-file context and cached validation results to file-specific validators. (`#health-validation-scope`)
- Effect tracing now replaces stale records for regenerated outputs and uses dependency indexes for template/data invalidation lookups. (`#incremental-effect-trace-replacement`)
- Documented the Milo CLI as Bengal's settled command entry point and removed stale migration alias references. (`#milo-cli-closure`)
- OpenAPI autodoc now resolves local file-relative `$ref` entries and tracks the resolved files as incremental build dependencies. (`#openapi-local-ref-dependencies`)
- Skip rewriting unchanged per-page JSON, text, and Markdown output-format files during post-processing. (`#output-formats-skip-unchanged`)
- Deep-froze nested payloads on pipeline records so cached page metadata, parsed AST data, TOC items, and render dependencies cannot be mutated after construction. (`#pipeline-record-freeze`)
- Wire plugin-provided Patitas directives and roles into parser setup and mark those plugin capabilities ready in plugin inspection. (`#plugin-directive-role-wiring`)
- Hardened plugin registry validation so malformed extension names, non-callable hooks, invalid template phases, and mutable frozen snapshots fail early with explicit errors. (`#plugin-registry-contract`)
- Improve post-render build diagnostics and reduce incremental per-page output work. (`#post-render-build-tail`)
- Incremental site-wide output fingerprints now reuse cached per-page artifact hashes, reducing no-op aggregate skip work on large sites. (`#postprocess-delta-aggregate-fingerprints`)
- Output-format graph data is now built lazily, avoiding graph construction when incremental JSON outputs are already up to date. (`#postprocess-lazy-graph`)
- Reuse cached post-render page artifacts for incremental output formats and link-registry health setup. (`#postrender-artifact-cache`)
- Internal link target registries are now owned by rendering, with health keeping
  compatibility imports while validation migrates to the shared resolver. (`#rendering-reference-registry`)
- Rendering health checks now warn about missing share-card metadata and malformed JSON-LD blocks in generated HTML. (`#rendering-social-jsonld-validation`)
- Search configuration now has an explicit `search.backend` contract, defaulting to the existing Lunr backend without changing generated artifact paths. (`#search-backend-contract`)
- `bengal serve` now starts a background completion build after the browse-ready cold start so deferred artifacts, health checks, and caches finish without blocking first paint. (`#serve-background-completion`)
- Background completion for `bengal serve` now runs in quiet mode, reports one concise completion line, and coalesces deferred generated-artifact polling in the request log. (`#serve-background-console`)
- `bengal serve` now exposes `--complete` for users who want dev-server startup and watched rebuilds to wait for the full artifact, health, and cache tail instead of the default browse-ready fast path. (`#serve-complete-policy`)
- `bengal serve` builds now honor the serve-ready policy by deferring non-browse-critical post-render work such as artifact inventories, cache persistence, provenance saves, health checks, and asset audits. (`#serve-ready-defers-tail`)
- Serve-ready build summaries now say `HTML ready` instead of `Built` so local dev output distinguishes first paint from full background artifact completion. (`#serve-ready-summary`)
- Dev server static/CSS edits can now use a direct atomic output copy and reload without running the full warm build when Bengal can prove the output is an existing verbatim asset. (`#server-asset-fast-path`)
- Dev server double buffering now delta-seeds the inactive output buffer after successful incremental builds, avoiding full-tree staging copies on the next rebuild when typed output records identify the changed files. (`#server-delta-buffer-staging`)
- Improve dev-server reload and health-check feedback by suppressing aggregate-only reloads and showing health-check progress before validators finish. (`#server-reload-health-ux`)
- Dev-server watcher rebuilds now skip the pre-build output content-hash scan when typed build outputs can drive the reload decision. (`#server-skip-reload-baseline`)
- Explain dev-server template rebuild decisions at info level, including template dependency cache misses and incremental template rebuilds. (`#server-template-rebuild-diagnostics`)
- Social cards now persist rendered-input fingerprints in the build cache so full builds can reuse unchanged generated card files without sharing the output-format fingerprint map during card generation. (`#social-card-persistent-fingerprints`)
- Tightened stale-output prevention for incremental builds by using build-start provenance timestamps, nanosecond file mtimes, section derived-cache invalidation, and conservative dev-server reactive fallbacks. (`#stale-output-prevention`)
- List and inspect bundled themes consistently, add `theme swizzle-list`, `theme swizzle-update`, and `theme preview`, and make `theme new --mode package` produce an installable package skeleton. (`#theme-cli-parity`)
- Added an internal theme metadata model so theme validation reports malformed metadata fields before checking template and asset structure. (`#theme-metadata-contract`)
- Improved `bengal theme preview` so it reports the active theme, watched paths, and validation issues before starting the live preview server. (`#theme-preview-preflight`)
- Versioned documentation configs can now set `status` to `current`, `legacy`, `deprecated`, `preview`, or `eol`; existing `deprecated: true` configs remain supported. (`#version-status-config`)
- Upgrade Bengal's `milo-cli` requirement to the Kida 0.9-compatible 0.3.1 release, and make Bengal resolve as its own uv workspace root for local development. (`#milo-cli-0-3`)

### Fixed

- Made notebook sidecar and generated font CSS writes atomic and output-collector visible, and routed downloaded font files through the shared atomic write helper. (`#atomic-sidecar-font-writes`)
- Restore `bengal cache inputs` and `bengal cache hash` runtime execution by moving CI cache input discovery into the cache package, fix cache hashing for cwd-relative `--config` paths, keep site-local themes visible in `bengal theme list/info`, and add published CLI runtime smoke coverage for advertised commands. (`#cache-hash-runtime`)
- Fix menu hierarchy rebuild idempotence and mixed-type section weight sorting. (`#core-menu-section-sorting`)
- Preserve descendant selector whitespace before pseudo, attribute, and universal selectors during CSS minification. (`#css-minifier-selector-whitespace`)
- Fix Git-mode versioned builds so release-branch outputs merge into canonical versioned documentation paths and cached worktrees are reused when refs have not moved. (`#git-version-builds`)
- Fix git-versioned documentation sidebar links so older versions point at their versioned section paths. (`#git-version-sidebar-links`)
- Directive health validation now uses the shared validation scope and seeds per-file cached results, preventing stale directive findings from disappearing during incremental checks. (`#health-directive-scope-cache`)
- Restored incremental theme-template directory detection used by warm-build template invalidation. (`#incremental-theme-template-helper`)
- Internal link validation now uses the rendering reference resolver and correctly
  handles `./` links from directory-style page URLs. (`#link-validator-rendering-resolver`)
- Sanitize cached page artifact metadata before output-format fingerprinting and cache persistence. (`#page-artifact-json-safety`)
- Add a manifest for page artifact shards and support targeted artifact loads. (`#page-artifact-manifest`)
- Fix stale page lookup caches after same-length page-list replacements. (`#page-cache-epoch`)
- Harden post-render correctness around aggregate LLM text hashing, incremental validation caching, cache-save failures, and provenance session caches. (`#post-render-correctness`)
- Batch page provenance persistence after render instead of storing each record individually. (`#provenance-batch-persistence`)
- Scoped icon resolver caches, rendered icon caches, template icon aliases, and page context wrappers to the active site/build so concurrent or repeated builds cannot reuse stale rendering state from another site. (`#render-cache-scoping`)
- Fixed Kida fragment cache entries that include `asset_url()` so asset fingerprint changes cannot replay stale CSS or JavaScript URLs. (`#rendering-asset-fragment-cache`)
- `bengal serve --complete` now blocks through the full initial build even when cached output exists instead of taking the cached serve-first shortcut. (`#serve-complete-cached-blocking`)
- Dev server reload suppression no longer emits a follow-up `"none"` reload event after deciding no browser reload should be sent. (`#server-none-reload-suppressed`)
- Update Poe build, serve, and deploy-test helpers to use the current `--source site` CLI shape. (`#release-0.3.3-prep`)
- Upgrade Bengal's Pounce dependency to the release with protocol-owned sendfile handling, allowing dev and preview static assets to use sendfile without HTTP/1 Content-Length errors. (`#server-static-sendfile`)
- Replaced shortcode pairing with a single-pass stack scanner so nested paired shortcodes, including nested shortcodes with the same name, expand correctly without repeated full-content searches. (`#shortcode-stack-scanner`)
- Treat generated site-wide output-format files like `/llms.txt` as valid internal link targets. (`#site-wide-output-link-targets`)
- Fix incremental template invalidation for active theme inheritance chains. (`#template-invalidation`)
- Hardened dev-server watcher shutdown with explicit lifecycle states, including the race where the background event loop closes before `stop()` posts its final stop callback. (`#watcher-stop-closed-loop`)


## [0.3.2] - 2026-05-02

### Added

- Epic agent DX polish (`plan/epic-agent-dx-polish.md`): close the five discoverability gaps that trip AI agents cold-reading Bengal. Core-type docstrings on `Site`/`Page`/`Section` gained "When to use" intent lines (coverage 1.2% → 71.6%). `AGENTS.md` grew an "Extending Bengal" section with 4 extension points (template function, content type, CLI command, build phase) and a 3-bullet Milo-vs-Click primer. New `bengal new content-type <name>` scaffold generates a working `ContentTypeStrategy` subclass with `When to use:` docstring, `default_template`, `sort_pages()`, and `register_strategy()` call. Every `cli.error(...)` in `bengal/cli/` now pairs with a guidance follow-up (`cli.tip`/`info`/`render_write`) within 3 lines (coverage 27.1% → 100%, 70/70); new AST gate test enforces the rule for future additions. Archived 4 done-signal RFCs from `plan/` root into `plan/complete/` and `plan/evaluated/` (root count 69 → 65). (`#epic-agent-dx-polish`)
- Error UX overhaul (`#236`): stable `ErrorCode` (R002–R040) emitted at every template-error site; browser overlay in dev server (HTML renderer + SSE transport); "Did you mean?" suggestions surfaced in terminal, HTML overlay, and JS live-reload overlay; `--continue-on-error` and `--error-format=json` build flags; build-end summary table grouped by `ErrorCode`. `TemplateRenderError` (635 LOC god class) split into `ErrorClassifier` + `SourceContextExtractor` with the suggestion path collapsed into `bengal/errors/suggestions.py`. (`#error-ux-overhaul`)
- Added `bengal plugin list`, `bengal plugin info`, and `bengal plugin validate` to report installed plugin readiness and distinguish wired capabilities from pending registry surfaces. (`#plugin-cli-introspection`)

### Changed

- Add scoped AGENTS.md steward guidance for Bengal's highest-risk packages and test layers. (`#contributor-stewards`)
- Move Page content access, excerpt fallback rendering, and meta-description derivation behind rendering-side helpers while preserving template-facing Page properties. (`#page-content-service`)
- Internal Page metadata normalization now lives in pure helper functions behind inline Page compatibility properties, removing the legacy Page metadata and relationship mixins. (`#page-metadata-helpers`)
- Move Page link extraction and shortcode checks behind rendering-side operation helpers while preserving Page compatibility shims. (`#page-operations-service`)
- Move page bundle resource filesystem access, type categorization, and image conversion behind rendering-side helpers while preserving PageResource compatibility methods. (`#page-resources-service`)
- Move Page href/path URL construction behind rendering-side helpers while preserving template-facing Page URL properties. (`#page-url-service`)
- Moved Section hierarchy, query, and navigation helpers out of core mixin inheritance, and moved Section URL presentation and theme/navigation ergonomic behavior, including section icons and nav-child visibility, behind rendering-side helpers while preserving the existing template-facing Section API. (`#section-ergonomics-helpers`)
- Moved direct Site content and asset discovery work behind the content orchestrator while preserving Site compatibility shims. (`#site-content-orchestrator`)
- Site decomposition + mixin elimination (`#236`): extract `SiteRunner` (build/serve/clean lifecycle) to `bengal.orchestration.site_runner`; `Page`/`Section` now depend on a read-only `SiteContext` Protocol enforced by `import-linter` Contract 2; all 5 Site mixins dissolved into a plain `@dataclass` with zero inheritance (1,649 → ~467 LOC), guarded by `tests/unit/core/test_no_core_mixins.py` and the architectural tenet in `CLAUDE.md`. (`#site-decomposition-mixin-removal`)
- Upgrade bengal-pounce to 0.7.0 and kida-templates to 0.9.0. Bengal now carries a temporary uv override for milo-cli's stale `kida-templates<0.8.0` dependency ceiling while keeping the pinned Milo source revision unchanged. (`#bump-pounce-kida`)
- Add `bengal check --templates-security` for Kida 0.9 static escape/privacy analysis, surfacing trust-boundary warnings such as unexplained `| safe` use and sensitive-looking context paths without making normal template syntax validation noisy. (`#kida-static-template-analysis`)
- Upgrade `bengal check --templates-context` to use Kida 0.9 dotted-path context contract checks while filtering dynamic Bengal roots such as `params.*` and `site.data.*` to avoid false positives for author-provided data. (`#kida-context-contracts`)
- Refresh Kida static context guidance for 0.9.0: Bengal keeps `kida.static_context` opt-in while documenting the compile-time `config.*` folding path and covering the engine wiring with a regression test. (`#kida-static-context-guidance`)
- Support Kida template aliases through `kida.template_aliases`, enabling `@alias/` includes such as `{% include "@components/card.html" %}` alongside Kida's relative `./` and `../` template paths. (`#kida-template-aliases`)
- Route dev-server static assets through Pounce's optimized static file handler while keeping Bengal-owned HTML, markdown negotiation, live reload, rebuild badges, and generated-artifact behavior intact. Assets now get ETags, `304` revalidation, range responses, and precompressed `.gz`/`.zst` variants when available. (`#pounce-static-assets`)
- Bump milo-cli to v0.2.2; remove redundant `no_include_version` param that now conflicts with milo's auto-generated `--no-` flags for boolean defaults. (`#bump-milo-cli-0.2.2`)
- Bump bengal-pounce to v0.6.0 (subinterpreter workers, RFC 9842 compression dictionaries, zero-copy sendfile, TOML config, security hardening); fix CoercionWarning in tags template where empty-string `max_tags_display` was silently coerced by `| int`. (`#bump-pounce-0.6.0`)
- Foundation leaf hygiene (Sprint 1 of `plan/foundation-leaf-hygiene.md`): hoist `default_formats` in `dates.parse_date` to module-level constant; dedupe `text.truncate_words` double-join; delete unreachable post-loop blocks in sync + async `retry_with_backoff`; hoist local `unicodedata` import in `text.slugify_id`. Net −15 LOC across 4 leaf utility modules; no behavioral changes. (`#foundation-leaf-hygiene-s1`)
- Foundation leaf hygiene (Sprint 2 of `plan/foundation-leaf-hygiene.md`): consolidate DotDict `__getattribute__`/`__getitem__` via shared `_wrap_dict_value` helper and document the `""`-on-miss + `hasattr` quirk + the eager `from_dict` rationale; migrate `menu.py` and `validators/tracks.py` from `hasattr(site.data, "tracks")` to `"tracks" in site.data` so DotDict misses (which always return `""`) stop silently bypassing the data-driven code paths; expand `isinstance(data, dict)` in `menu.py` to `dict | DotDict` (fixes a latent bug where data-driven dropdowns silently no-op'd in production because `site.data[key]` is eager-wrapped to `DotDict`); collapse `lru_cache.get_or_set` into a single locked block; add a "Function groups" section to `text.py`'s module docstring per the Sprint 0 monolith decision. Test fixtures updated to use real `DotDict` instead of `MagicMock` (whose `__contains__` defaulted to False and masked the menu bug). No public API changes; ty diagnostic count drops 2207 → 2204. (`#foundation-leaf-hygiene-s2`)
- Foundation leaf hygiene (Sprint 4 of `plan/foundation-leaf-hygiene.md`): swap `async_compat._get_uvloop`'s manual `_uvloop_checked`/`_uvloop_module` globals for `@functools.cache` (eliminates the check-then-act race that would surface under Python 3.14t free-threading and removes redundant ~200ms uvloop import attempts); extract a `ThreadLocalCache._cache_key` helper so the `_cache_{name}_{key or 'default'}` f-string lives in one place instead of three (`get`, `clear`, `clear_all`); switch `truncate_words` from `text.split()` to `text.split(maxsplit=word_count)` so callers like `generate_excerpt` only parse the prefix of long markdown bodies instead of the whole thing twice. Behavior-preserving; ty diagnostic floor stable at 2204. (`#foundation-leaf-hygiene-s4`)
- Upgrade kida-templates to 0.7.0. The new default `strict_undefined=True` now raises `UndefinedError` on missing attrs/keys instead of rendering empty — default-theme templates were updated to use `?.` optional chaining with `?? default` fallbacks, and `tiles.html` was updated for the new `groupby` iteration shape (`{grouper, list}` dicts instead of `(key, items)` tuples). (`#kida-0.7.0-upgrade`)
- Adopt Python 3.14+ patterns: freeze 38 dataclasses with `frozen=True, slots=True`, convert 10 type aliases to PEP 695 `type` syntax, replace 3 if/elif dispatch chains with `match/case`, and add 5 TypedDict definitions for `to_dict()` return types. (`#py314-pattern-modernization`)

### Removed

- Removed the Textual dashboard runtime, CLI flags, package, and dashboard-specific tests so Bengal's CLI stays focused on fast pure-Python site generation. (`#axe-textual-dashboard`)

### Fixed

- Move default documentation page content before bulky navigation sidebars in the HTML stream so agents can reach meaningful content earlier without changing the visual docs layout. (`#agent-score-content-start`)
- Add explicit `llms.txt` directives to generated HTML and Markdown mirrors so AI documentation checkers can discover the site-wide agent index from sampled pages. (`#agent-score-directives`)
- Generate Markdown mirrors from rendered primary content when templates add substantial page content, improving parity for section and other generated pages. (`#agent-score-markdown-parity`)
- Avoided wasted cold-build provenance verification, made Markdown mirror generation lazy, added output-format timings, and skipped unchanged-output byte comparisons outside incremental hot-reload builds. (`#build-performance-diagnosis`)
- Fix dev-server startup on `localhost` when an existing Bengal server is listening on IPv6. Bengal now recognizes the `bengal s` serve alias in stale-process detection and checks all address families before handing the port to Pounce, allowing auto-port fallback to run before the server bind fails. (`#dev-server-port-probe`)
- Fix Kida 0.7.0 `strict_undefined=True` render errors in default-theme templates that caused ~800 pages to render as "Build Error" overlays. `render_menu_item` in `base.html` now extracts `item.name`/`item.href`/`item.children` to safe locals via `?.` and `??`, and `authors/single.html`, `doc/list.html`, `partials/page-hero/_macros.html`, and `autodoc/openapi/partials/schema-viewer.html` now use optional chaining with `?? none` fallbacks for nullable accesses. Also removes the `parse_discover_config` `{% def %}` macro (which returned `Markup`, not the intended dict) in favor of inline `{% let %}` bindings. (`#fix-kida-strict-undefined-theme-templates`)
- Suppress local preview reload notifications for rendered HTML pages whose output bytes did not actually change. (`#preview-byte-stable-reload`)
- Make local preview `reload-page` events route-aware so edits to one HTML page do not reload unrelated pages that are open in the browser. (`#preview-route-aware-reload`)
- Load default-theme view transition CSS only when view transitions are enabled so local preview navigation does not opt into browser page transitions by accident. (`#preview-view-transitions`)
- Fix release-readiness gaps found by local broad test runs: theme library configuration failures now include Bengal error codes with actionable suggestions, warm no-op incremental builds report measured cache-hit stats before early return, timing-sensitive local tests now validate behavior instead of scheduler luck, and Makefile build/serve helpers use the current `--source site` CLI shape. (`#release-readiness-local-gates`)
- Improve warm-build performance by preserving lazy Kida template context, caching Kida template dependency discovery, passing incremental context to health checks, reusing fingerprint fast paths for data/templates, memoizing section version membership, removing transient nav proxy locks, and regenerating missing site-wide postprocess artifacts without rebuilding pages. (`#steward-performance-followups`)
- Template changes in the dev server now use existing template dependency data instead of importing the removed legacy template detector, keeping selective rebuilds available when dependencies are known and falling back conservatively when they are not. (`#template-hmr-steward-slice`)
- Ship the milo-cli argparse fix as v0.3.2 and add regression guards against CLI dependency drift. v0.3.1 installed cleanly but crashed at parser construction on every invocation (`bengal --version`, `--help`, everything) because `uv.lock` pinned milo-cli 0.2.1 while the wheel's `>=0.2.1` constraint resolved end users to the newer 0.2.2, whose auto-generated `--no-<flag>` behavior collided with an explicit `no_include_version` param in `cache_hash`. Adds three layers of defense: a fast unit test that builds the full milo parser (catches the exact argparse conflict in ~0.1s), a slow integration test that installs the built wheel into a fresh venv against latest PyPI-resolved deps, and a pre-publish CI step in `python-publish.yml` that smoke-tests the wheel before it reaches PyPI. (`#release-0.3.2-and-cli-drift-guards`)


## [0.3.1] - 2026-04-13

### Added

- Add milo as a first-class CLI autodoc framework, enabling automatic CLI reference documentation generation from milo-based CLIs with JSON Schema parameter extraction and lazy command support. (`#milo-cli-autodoc`)
- Adopt [Towncrier](https://towncrier.readthedocs.io/) for release notes: add `changelog.d/` fragments, `poe changelog` / `poe changelog-draft`, and rename the package changelog to `CHANGELOG.md` (aligned with the b-stack strategy).

### Fixed

- Harden CLI user-facing edges: route site-loading errors through existing error infrastructure, make required args enforced by argparse, remove double-negative boolean flags in serve, add traceback fallback when renderer fails, and fix misleading help text. (`#cli-sharp-edges`)
- Update stale `bengal site {build,serve,clean}` references to flattened top-level commands across CI, tooling, source code, and documentation. (`#fix-stale-cli-refs`)
- Fix live progress bar not updating in place by adding throttled ANSI rendering with deferred logger output, and eliminate false-positive cascade and directive warnings for virtual autodoc pages. (`#progress-bar-and-warnings`)
- Fix 12 sharp edges across effects, CLI, and error handling: Effect.from_dict now uses tagged serialization to preserve Path vs string types, BuildCache.load sets site_root eagerly to prevent cache key races, EffectTracer.load handles JSON corruption gracefully, provenance recovery scans all pages instead of sampling 10, serve/dashboard commands wrap exceptions through handle_exception, 22 CLI return-None sites return structured dicts, output-mode flag conflicts are validated upfront, and 5 silent except-OSError-pass handlers now log debug messages. (`#sharp-edges-remediation`)
- Harden 17 UX sharp edges: codemod now confirms before writing, version create rolls back on failure, stale remote cache warns visibly, unknown config keys and features get "did you mean?" suggestions, template context validation wired into builds, CLI flags categorized in help, and exit codes standardized. (`#ux-edge-finder`)
- Surface silent failures across directives, incremental builds, and CLI: unknown directives now warn with fuzzy-match suggestions, contradictory CLI flags fail fast, silent full-rebuild triggers log reasons, and all CLI commands return structured dicts. (`#ux-sharp-edges`)
- Bump kida-templates to v0.6.0 for optional chaining display fix, structured errors, and expanded error codes. Fix silent `| int` coercion of empty string in tag list component. (`#bump-kida-v0.6.0`)


## [Unreleased]

## 0.3.0 - 2026-04-09

### Immutable Page Pipeline
- **core**: add SourcePage frozen record for immutable discovery pipeline (#199)
- **rendering**: add ParsedPage frozen record for immutable rendering pipeline (#196)
- **rendering**: add RenderedPage frozen record for immutable rendering pipeline (#197)
- **orchestration**: decompose SiteSnapshot into NavigationPlan, TaxonomyPlan, RenderSchedule (#198)
- **core**: delete PageProxy (906 lines), reconstruct pages from cache with zero disk I/O (#200)

### Plugin System
- **plugins**: add unified plugin framework with `Plugin` protocol, `PluginRegistry`, and `FrozenPluginRegistry`
- **plugins**: entry-point discovery via `bengal.plugins` group — third-party plugins auto-discovered
- **plugins**: 9 extension points: directives, roles, template functions/filters/tests, content sources, health validators, shortcodes, phase hooks
- **plugins**: builder→immutable pattern — mutable registry during registration, frozen snapshot for thread-safe rendering

### Architecture
- **concurrency**: add WorkScope structured concurrency, migrate all executor sites (#189)
- **core**: eliminate Site mixin hierarchy, migrate to protocol types (#194)
- **cli**: CLI feature maturity audit — fix bugs, add missing commands, wire sources (#187)

### Template Dependency Tracking
- **cache**: per-page template dependency recording — tracks which templates (and their include/extends chain) each page uses
- **incremental**: selective rebuild when templates change — only affected pages rebuild instead of full site rebuild
- **provenance**: `_expand_forced_changed()` uses per-page dependencies for targeted invalidation; falls back to full rebuild on cache miss

### Free-Threading Hardening
- **effects**: serialize all EffectTracer mutations and reads under lock for PEP 703 free-threading
- **utils**: replace `@lru_cache` on `get_bengal_dir()` with thread-safe `LRUCache` (RLock-backed)
- **deps**: kida-templates 0.2.8→0.2.9 for free-threading support

### Performance
- **perf**: eliminate O(n²) hotspots, consolidate taxonomy slug normalization (#192)
- **orchestration**: coalesce 8 redundant `site.pages` traversals into single passes across menu, finalization, provenance, and rendering phases
- **menu**: `_analyze_menu_state()` replaces 3 separate page scans with one pass returning `(needs_rebuild, menu_pages, root_level_pages)`
- **finalization**: merge page count + autodoc detection into single loop
- **manifest**: fix `summary()` multi-scan (4 scans → 1 efficient pass)
- **refactor**: stale code refresh — ~50 files audited, 205 lines dead code removed, ty diagnostics 837 → 715 (#203)

### Features
- **directives**: add excerpt-break directive for author-controlled excerpts (#202)

### Code Simplification
- **errors**: replace 11 manual `__init__` methods in exception subclasses with `_default_build_phase_name` class variable pattern
- **rendering**: remove 3 deprecated transforms (`escape_jinja_blocks`, `transform_internal_links`, `normalize_markdown_links`) — consolidated into `HybridHTMLTransformer`
- **rendering**: extract `_default_pagination()` and `_coerce_pagination_ints()` helpers in renderer

### Fixes
- **rendering**: render progress bar stuck at 0% during WaveScheduler rendering (#190)
- **metrics**: accurate render metrics, per-page timing, and regression detection (#184)
- **rendering**: xref pipe placeholder surviving Patitas escape_html (#182)
- **rendering**: add missing error codes to Kida rendering engine exception handlers
- **tests**: fix contextvar test — tuple context manager protocol error
- **orchestration**: gate WriteBehindCollector on parallel builds to prevent sequential deadlocks (#201)
- **ci**: replace SIGALRM with watchdog thread for CI test timeouts (#199)

### Tooling
- **lint**: add 8 ruff rule sets, tighten ty config, migrate to PEP 695 generics (#191)
- **ci**: flatten test pipeline and deduplicate coverage (#185, #186)
- **ci**: restructure workflow for 6 parallel integration shards with signal-based timeouts (free-threading compatible)
- **deps**: bump deps, fix ty 0.0.26 errors, add Renovate config (#183)
- **docs**: remove stale PageProxy refs, document frozen records (#201)
- **tests**: add comprehensive `tests/README.md` with test suite guide (4,065+ tests, 116 property-based)
- **fixtures**: extract `build_ephemeral_site_at()` for class/module-scoped test reuse
- **cleanup**: remove no-op `test_resource_cleanup.py`

## 0.2.6 - 2026-03-17

### Double-Buffered Dev Server
- **server**: add BufferManager for double-buffered output — eliminates FOUC during rapid rebuilds
- **server**: ASGI app accepts callable output_dir for per-request directory consistency
- **server**: zero-disk reactive path for content-only edits
- **server**: in-process builds for clean Ctrl+C shutdown (no zombie subprocesses)
- **server**: remove stopgap FOUC mitigations now redundant with double-buffer

### i18n Gettext Workflow
- **cli**: add `bengal i18n extract`, `bengal i18n compile`, `bengal i18n status` commands (Phase 1A)
- **i18n**: add PO/MO catalog management and coverage computation
- **cli**: narrow exception handling in i18n commands and catalog

### Jinja2 Engine Removed
- **rendering**: remove Jinja2 engine and adapter — Kida is now the only template engine
- **BREAKING**: `template_engine: jinja2` config no longer valid; use `kida`

### Performance
- **navigation**: O(n²)→O(1) page navigation via lazy dict index with auto-invalidation
- **validation**: precompute newline positions + bisect for O(N + M log N) cross-ref validation
- **cache**: add excerpt index for PageProxy without full page load

### Orchestration
- **orchestration**: wire block cache into WaveScheduler for per-page rendering optimization
- **orchestration**: propagate asset manifest context explicitly through pipeline
- **orchestration**: aggregated fallback diagnostics (sampled, summarized at phase end)
- **orchestration**: add parsed/rendered cache hit metrics to build summary

### New Output Generators
- **postprocess**: add agent manifest generator
- **postprocess**: add changelog generator
- **postprocess**: add llms.txt generator
- **postprocess**: add robots.txt generator

### Other
- **core**: add `visibility.ai_train` and `visibility.ai_input` page properties for Content Signals
- **core**: normalize tags in `Frontmatter.from_dict()` for malformed input
- **core**: rename menu `url` → `href`; remove `active`/`active_trail` from MenuItem.to_dict()
- **directives**: fix list-table options mapping, re-enable skipped tests
- **cli**: use CLIOutput for stale process and port-in-use messaging
- **rendering**: add `direction()` template function for RTL language support
- **rendering**: add template context validation (`--templates-context` flag)
- **rendering**: add template profiler for render performance analysis
- **cli**: scan all subdirectories for Bengal site markers (not hardcoded names)
- **code**: remove three unused methods from PageOperationsMixin
- **deps**: kida-templates ≥0.2.8, patitas ≥0.3.5, bengal-pounce ≥0.3.0

## 0.2.5 - 2026-03-03

### Kida 0.2.3

- **config**: add `max_extends_depth` and `max_include_depth` to `kida:` config for sites with deep theme/inheritance chains
- **deps**: require `kida-templates>=0.2.3`

## 0.2.4 - 2026-03-02

### Versioning for MkDocs Migration
- **versions.json**: Emit Mike-compatible `versions.json` when versioning enabled (config: `versioning.emit_versions_json`, default true)
- **Root redirect**: Configurable redirect from site root to default version (`versioning.default_redirect`, `versioning.default_redirect_target`)
- **Docs**: Versioning guide updated with format details and MkDocs migration comparison

### Math and LaTeX Rendering
- **content.math**: New theme feature for KaTeX client-side math (opt-in via `theme.features`)
- **Elements**: Renders `.math` (inline) and `.math-block` (display) elements
- **Docs**: Math and LaTeX authoring guide; theme reference updated

### Patitas Consolidation
- **Frontmatter**: Migrate from python-frontmatter to Patitas; require `patitas>=0.3.3`
- **Notebooks**: Migrate from nbformat to Patitas; `.ipynb` parsed via `patitas.parse_notebook()`
- **Result**: Fewer dependencies, unified content pipeline

### Dev Server and Live Reload
- **Live reload**: Pure async SSE for more reliable hot reload
- **DOM fragments**: Instant partial updates when editing content (no full page refresh)
- **Serve-first**: Requires build cache when starting with empty output

### Blog Theme
- **Series navigation**: New `series-nav` component for default blog theme
- **Layout**: `blog-after-content` moved inside `blog-post-layout`

### Other
- **Shortcodes**: Ref/RelRef, HasShortcode, nesting, strict mode, CLI support
- **Build**: Parallel provenance filter for large sites; skip verification on cold builds
- **Health**: Refactored link validator with configurable resolution and skip rules
- **Rendering**: Improved error display when template engine raises errors

## 0.2.3 - 2026-03-01

### Default Theme Blog Improvements
- **Post cards**: New layout with related posts, author bio, social share dropdown
- **Contact & About**: Dedicated pages for blog scaffold
- **Newsletter CTA**: Placeholder for newsletter signup
- **Comments**: Placeholder and theming recipe for comments integration
- **Scaffolds**: Updated authors.yml, skeleton, and sample posts

### Excerpt Filters for Card Previews
- **excerpt_for_card**, **card_excerpt**: New filters to avoid repeating title/description in card excerpts
- Documented in reference and cheatsheet

## 0.2.0 - 2026-02-14

### Rosettes Highlight Caching
- **Code blocks**: Block-level caching to avoid re-highlighting identical blocks across pages
- **Deps**: `rosettes>=0.2.0`

### Dev Server: Pounce ASGI Backend
- **Pounce**: Replace ThreadingTCPServer with Pounce ASGI (`bengal-pounce>=0.2.0`)
- **Live reload**: SSE-based, fragment-based partial page updates
- **Static serving**: HTML injection in ASGI app

### Kida & Patitas 0.2.0
- **Deps**: `kida-templates>=0.2.0`, `patitas>=0.2.0`

## 0.1.9 - 2026-02-08

### 🏗️ Architecture Decomposition ✅

- **core**: split `PageLike` and `SiteLike` into role-based protocols (`SiteConfig`, `SiteContent`, `Summarizable`)
  - Migrate Page → PageLike and Site → SiteLike across 40+ consumer files
  - Narrow protocols to minimal interfaces per consumer (read-only where possible)
  - Remove `SiteLike` from `Site` inheritance chain entirely
- **core**: extract mixins to free functions and composed services
  - `PageComputedMixin` → free functions with tests
  - `PageBundleMixin` → free functions
  - `PageNavigationMixin` → free functions + property wrappers
  - `SiteVersioningMixin` → composed `VersionService`
  - `SitePropertiesMixin` → inline properties on `Site`
  - Remove 8+ dead mixin files from `Site` inheritance chain (12 → 4 mixins)
- **config**: create `ConfigService` frozen dataclass, wire into `Site` with bridge properties (31 tests)
- **cache**: extract `TaxonomyIndex` and `AutodocTracker` to composed classes
- **cache**: remove `DependencyTracker`, fully replace with `EffectTracer` (persistence, file fingerprinting, threading tests)
- **core**: split `snapshots/builder.py` (1,762 lines) into 5 focused modules
- **core**: replace `Any` escape hatches with correct types across rendering and Page files
- **core**: rename `parsed_ast` to `html_content` in core and all consumers
- **core**: remove 55 stale `type: ignore` comments
- **core**: fix protocol Self-type annotations in renderers and mixins
- **config**: remove deprecated `config/loader.py`, update test imports

### ⚡ Build Performance Optimizations ✅

- **rendering(output)**: wire `fast_mode` to skip HTML formatting (Phase 1.1)
  - `build.fast_mode=True` now returns raw HTML without pretty-printing or minification
  - Provides ~10-15% speedup for builds with formatting enabled
- **rendering(assets)**: implement render-time asset tracking (Phase 2)
  - Track assets during template rendering via ContextVar-based AssetTracker
  - Eliminates post-render HTML parsing for asset dependency tracking (~20-25% speedup)
- **cache(autodoc)**: add AST caching for autodoc extraction (Phase 3)
  - Cache parsed Python module data to skip AST parsing on subsequent builds (~30-40% speedup)
  - Full DocElement reconstruction from cache on cache hit
  - Automatic cache invalidation on source file changes
- **core(pool)**: re-enable ParserPool with patitas 0.1.1 `_reinit()` support (~78% faster instantiation)
- **rendering**: pre-compute renderer caches and context wrappers at snapshot time
- **core**: pre-compute NavTrees at snapshot time for lock-free lookups

### 🐍 Python 3.14 Modernization ✅

- **core**: convert to PEP 695 type parameter syntax (`class Foo[T]:` instead of `Generic[T]`)
- **core**: add `slots=True` to all frozen dataclasses
- **core**: add exception chaining to raise-in-except blocks
- **core**: annotate mutable class defaults with `ClassVar`
- **perf**: convert manual list building to comprehensions (PERF401)
- **rendering**: narrow `except Exception` blocks in kida.py and authors.py
- **style**: auto-fix source and test lint violations across codebase

### 🔒 Thread Safety (Python 3.14t) ✅

- **core(assets)**: ContextVar pattern for thread-safe asset manifest access
  - Fixes TOCTOU race condition in `Site._asset_manifest_cache` for free-threading
  - ~8M ops/sec throughput, zero lock contention
- **core**: add lock protection to shared mutable state in rendering hot path
- **core**: add lock ordering convention and concurrency documentation
- **core**: add immutable snapshot evaluation to concurrency docs
- **rendering**: separate BuildCache from DependencyTracker in pipeline
- **tests**: add threading integration tests for EffectTracer and BuildTaxonomyIndex

### 🔧 Cache & Incremental Build Improvements ✅

- **cache**: implement unified CacheCoordinator for coordinated cache invalidation across subsystems
  - Centralized path registry, rebuild manifest, and invalidation coordination
- **core(cache)**: implement Output Cache Architecture RFC
  - Content-hash embedding in rendered output for O(1) change detection
  - Output type classification (authored, generated, static)
  - GeneratedPageCache for taxonomy/archive page deduplication
- **orchestration(incremental)**: add IncrementalFilterEngine for rebuild decision hardening
- **cache**: detect template changes and trigger incremental rebuilds
- **orchestration**: fix incremental tag term page generation
- **orchestration**: promote PageProxy to full Page in `phase_update_site_pages`
- **orchestration**: wire EffectTracer into incremental build pipeline with persistence and file fingerprinting
- **orchestration**: move `configure_for_site` before parallel rendering, fix stale tracker tests
- **incremental**: skip cascade rebuild on body-only changes to `_index.md` sections
- **server**: enable content-hash change detection; integrate into build_trigger and dev_server

### 🚀 Developer Experience ✅

- **cli(upgrade)**: add `bengal upgrade` self-update command with PyPI version checking and installer detection (uv/pip)
- **cli(build)**: add incremental build observability flags (`--explain`, `--dry-run`, `--explain-json`)
- **cli**: add Python 3.14+ version warning on startup for compatibility awareness
- **server(dev)**: implement serve-first startup for instant first paint when cache exists (~2-3s faster cold start)
- **theme(link-previews)**: add dead link indicator styling for broken internal links
- **build**: add `make release`, `make publish`, `make dist` targets with `.env` token support

### 🎨 Theme Enhancements ✅

- **theme(header)**: add configurable navigation options
  - `nav_position`: left or center alignment
  - `sticky`: fixed header on scroll
  - `autohide`: hide header when scrolling down, show on scroll up
  - CSS variants via `data-nav-position`, `data-sticky`, `data-autohide` attributes

### 📝 Changelog & Releases Filter ✅

- **core(changelog)**: smart version detection with semantic sorting (semver-aware)
- **core(changelog)**: simplify releases filter API — always sort by default
- **core(changelog)**: make releases filter domain-aware; respect content type strategy
- **templates(changelog)**: trust ChangelogStrategy sorting, fix `sort_by` None handling

### 🔴 Error System Improvements ✅

- **errors**: consolidate error handling per RFC with 5 new exception classes
  - `BengalParsingError`, `BengalAutodocError`, `BengalValidatorError`, `BengalBuildError`, `BengalTemplateFunctionError`
  - Convert 10 generic exceptions to structured Bengal errors with codes and suggestions
  - Add O/V/B error code categories for orchestration, validation, and build errors
  - 43 unit+integration tests for error handling

### 🏗️ Protocol Layer ✅

- **protocols**: add `bengal.protocols` module as central protocol layer
  - Migrate `Cacheable`, `ProgressReporter`, `HighlightService` to shared protocols
  - Documented in architecture docs with protocol layer diagrams
- **refactor**: migrate to external `patitas` package; delete embedded parser (~15k lines removed)
  - ContextVar configuration pattern for Parser and HtmlRenderer
  - ParserPool, RendererPool, RenderMetadata, RequestContext for framework integration

### 🔨 Refactoring & Code Health ✅

- **refactor(rendering)**: decompose HtmlRenderer into block/inline/directive modules (Phase 3)
- **refactor(utils)**: split into domain-aligned sub-packages; extract shared protocols
- **core**: implement RFC code health improvements (Phase 1-2)
- **directives**: add Patitas-native glossary directive

### 📚 Documentation Audit ✅

- **docs**: comprehensive staleness audit across all doc sections
  - Fix stale claims in about, building, content, extending, get-started, reference, and theming sections
  - Align page URL properties to match codebase (`page.href`, `page._path`)
  - Replace Jinja2-style block endings with `{% end %}` in Kida examples
  - Add external cross-links for Kida, Patitas, Rosettes in about section
- **autodoc**: fix section-index pages blocked by stale URL claims from cache

### 🔧 CI & Packaging ✅

- **ci**: add `python-publish.yml` GitHub Actions workflow for trusted PyPI publishing
- **ci**: add `--clean-output` to pages build to fix 404s on `/api/` and `/cli/`
- **tests**: restore imports stripped by ruff auto-fix in deprecation tests
- **tests**: prefix unused variables with underscore
- **tests**: guard bs4 import in integration tests

### 🐛 Bug Fixes

- **core(taxonomy)**: fix duplicate tag page generation in incremental builds
- **rendering(link_transformer)**: fix `.md` link normalization to preserve anchor fragments
- **server(dev)**: fix serve-first not activating when baseurl is `/`
- **cache**: fix Python 3.14 import scoping issue in cache loading
- **core**: fix undefined name references in site and sitemap
- **orchestration**: fix incremental tag term page generation
- **tests**: fix CI failures from missing module, wrong kwarg, and unimplemented gaps

### 📦 Dependencies

- Bump `patitas` to >=0.1.1 (adds `_reinit()` for parser pooling)
- Bump `kida-templates` to >=0.1.2 (RenderContext, profiling support)

## 0.1.8 - 2026-01-12

### 🌐 External Linking & Previews ✅

- **external_refs**: add cross-project linking via `[[ext:project:target]]`, template-based resolution, cached index lookups, and `ext()/ext_exists()` helpers; exports `xref.json` during production builds with built-in templates (python stdlib, requests/httpx, pydantic/fastapi/sqlalchemy, numpy/pandas) for consumers
- **link-previews**: allow cross-site previews for whitelisted hosts with per-host failure thresholds, CORS fetch support, and configurable allowed hosts/schemes

### ⚙️ Config & Packaging ✅

- **config(v2)**: migrate to nested config architecture with structured `site.`*/`build.*` accessors, backward-compatible loader alias, and explicit disabled-feature booleans (e.g., `features.rss: false`)
- **config**: rename site config `features.yaml` to `outputs.yaml` (compatibility kept) and remove unused `features.syntax_highlighting` toggle
- **rendering(kida)**: remove bundled Kida engine in favor of external dependency `kida-templates>=0.1.1` (lighter tree; templates still supported)

### 🧭 CLI & Cache ✅

- **cli(cache)**: add `bengal cache inputs` and `bengal cache hash` commands (JSON/verbose) for deterministic CI cache keys that include the Bengal version
- **cache/autodoc**: add self-validation of autodoc sources with hash+mtime tracking and stale detection integrated into taxonomy change detection; supports migration from pre-0.1.8 caches
- **ci/pages**: update GitHub Pages workflow caching logic for accurate invalidation when outputs are missing

### 📝 Markdown Parser Improvements ✅

- **patitas**: implement container-stack architecture phases 1-4 for lists/blockquote handling, lazy blockquote continuation, and entity parsing fixes; full CommonMark 0.31.2 compliance (652/652 spec examples, no xfails)

## 0.1.7 - 2026-01-03

### 🔧 Build & Cache Fixes ✅

- **orchestration**: detect output/cache mismatch and force rebuild when output is missing (fixes CI issues where cache is restored but `public/` is cleaned)
- **discovery**: fix asset discovery for themes installed in hidden directories (e.g., `.venv`) by checking relative paths for hidden status
- **core(rendering)**: improve thread safety of global context creation via streamlined locking pattern

### 🔍 Health Check Improvements ✅

- **health(assets)**: make critical asset checks theme-agnostic (detects missing CSS/JS regardless of theme file names)
- **health(assets)**: add detection for empty (0-byte) CSS and JavaScript files which cause silent style/interaction failures
- **health(asset_urls)**: add case-sensitivity validation for asset URLs to prevent "works on macOS, fails on Linux CI" bugs
- **health(config)**: add GitHub Pages `baseurl` validation (detects missing or malformed `baseurl` for project sites)

## 0.1.6 - 2026-01-01

### 🚀 Kida Template Engine ✅

- **core(kida)**: Pure-Python template engine with Jinja2 compatibility as default
- **kida**: `{% match %}` pattern matching, pipeline operators `|>`, optional chaining `??`
- **kida**: `{% while %}` loops, `{% cache %}`, `{% slot %}`, `{% embed %}` components
- **kida**: Bytecode caching with `BlockCache` for site-wide block reuse
- **kida**: Pure-Python AST optimization pass (constant folding, dead code elimination)
- **kida**: Compile-time filter/test validation with 'Did you mean?' suggestions
- **kida**: Resilient None handling and line-aware error messages
- **themes(default)**: Full migration to Kida-native syntax with advanced patterns
- **engines**: Add `EngineCapability` enum and capabilities protocol for engine-agnostic templates

### 🚀 Patitas Markdown Parser ✅

- **core(parsers)**: Add Patitas as default markdown parser with typed AST and O(n) lexer
- **patitas**: Directive and role systems for extensible markup (Phase 2)
- **patitas(directives)**: Complete Bengal directive migration — 54 handlers with full parity
- **patitas**: Zero-Copy Lexer Handoff (ZCLH) protocol for Rosettes integration
- **patitas(parser)**: Fix list termination when followed by non-indented paragraph

### 🚀 Rosettes Syntax Highlighter ✅

- **rosettes**: Pure-Python syntax highlighter for Python 3.14t (no GIL re-enablement)
- **rosettes**: Now available as standalone package: [pypi.org/project/rosettes](https://pypi.org/project/rosettes/)
- **lexers**: 55 language support including tree, myst, jinja2, configs, diagrams
- **themes**: RFC-0003 semantic token system with CSS theming architecture
- **core(highlighting)**: Skip tree-sitter on free-threaded Python automatically
- **syntax-highlighter**: Add Kida template syntax highlighting v1.1.0

### 🔧 Error System Adoption ✅

- **errors**: Comprehensive error codes across all packages (A/B/C/D/N/O/V/X series)
- **errors**: Session tracking with `record_error()` for silent failure detection
- **errors**: Actionable suggestions in all error messages
- Packages adopted: cache, config, collections, content_layer, autodoc, health, assets, orchestration, postprocess, themes, analysis

### ⚡ Algorithm Optimizations (Big O) ✅

- **cache**: Reverse dependency graph for O(1) affected pages lookup
- **cache(taxonomy)**: Reverse index for O(1) page-to-tags lookup
- **cache(query_index)**: Set-based storage for O(1) page operations
- **analysis**: PageRank O(I×E) and Link Suggestions via inverted indices
- **config**: Batch deep merge O(K×D) for directory loading
- **health**: O(L²)→O(L) DirectiveAnalyzer, O(D²)→O(D) AutoFixer
- **postprocess**: Streaming LLM write O(n×c)→O(c) memory; heapq.nlargest for RSS
- **orchestration(complexity)**: LPT scheduling for parallel page rendering
- **content_layer**: LocalSource 2.5x faster, GitHubSource 10x faster, NotionSource 3x faster

### 🔒 Thread Safety (Python 3.14t) ✅

- **core**: Thread-safe locking for free-threading support across critical paths
- **directives/cache**: Add `DirectiveCache._lock` for concurrent access
- **icons/resolver**: Add `_icon_lock` for thread-safe icon resolution
- **server/live_reload**: Protect `set_reload_action()` with locking
- **rendering/context**: Double-check locking patterns for template context

### 🔧 Type System Hardening ✅

- **types**: Replace `Any` across 4 phases (protocols, critical paths, directives, template functions)
- **types**: Add TypedDict and Protocol definitions for type refinement
- **directives(options)**: Fix cache inheritance bug in `DirectiveOptions.from_raw()`

### 📦 Autodoc Improvements ✅

- **autodoc(openapi)**: REST API layouts with three-panel scroll-sync navigation
- **autodoc**: Migration from Jinja2 to Kida template engine
- **filters(views)**: Add PostView, ReleaseView, AuthorView, TagView filters
- **rendering(autodoc)**: Add MemberView, CommandView, OptionView for theme developers
- **rendering(openapi)**: Add endpoints/schemas filters for normalized template access

### ⚡ Performance Improvements ✅

- **health**: Remove redundant validators (saves 312ms/build)
- **health(directives)**: Remove H207 rendering check (saves 1s/build)
- **themes(docs-nav)**: Convert recursive include to macro (13x faster rendering)
- **cache**: All auxiliary caches migrated to compressed `.json.zst` format
- **perf**: ~~40% reduction in `.bengal/` directory size (~~2.8M savings)

### 🔍 Health Check Improvements ✅

- **health**: Add H-prefix codes to all health check results (H0xx-H9xx schema)
- **health**: Add `--ignore` CLI option for selective validation
- **health(autofix)**: O(1) dict lookup for fence fixes

### 🛠️ Template Functions ✅

- **template_functions**: Add 13 new filters (dates, collections, sharing, archive helpers)
- **core(page)**: Implement RFC Template Object Model Phase 1 — add `_source`, `word_count` properties

### 📝 Documentation Fixes ✅

- **docs**: 15+ accuracy fixes across versioning, i18n, authoring, filtering, menus, sources, deployment, benchmarks
- **docs(kida)**: Add Template Engine Concepts crash course
- **docs(site)**: Add language designators to 62 code blocks for Rosettes highlighting

### 🔧 Core Changes ✅

- **server**: Remove component preview feature
- **core**: Remove module/package shadowing; delete unused backward-compat shims
- **autodoc**: Remove backward compatibility aliases and legacy code

## 0.1.5-rc1 - 2025-12-10

### Page Hero Template Separation ✅

- **templates(page-hero)**: refactor monolithic `page-hero-api.html` (250+ lines) into modular components
- **templates(page-hero)**: add `_share-dropdown.html` - extracted AI share dropdown component (~100 lines)
- **templates(page-hero)**: add `_wrapper.html` - shared wrapper with breadcrumbs and share dropdown (~40 lines)
- **templates(page-hero)**: add `_element-stats.html` - element children stats component (~75 lines)
- **templates(page-hero)**: add `element.html` - DocElement pages (modules, classes, commands) (~55 lines)
- **templates(page-hero)**: add `section.html` - section-index pages with explicit `is_cli` support (~70 lines)
- **templates(page-hero)**: add `hero_context.is_cli` flag for explicit CLI detection (replaces URL sniffing)
- **templates(dispatcher)**: update `page-hero.html` to route `api` style to new separated templates
- **templates(autodoc/python)**: migrate `module.html` and `section-index.html` to use new templates
- **templates(autodoc/cli)**: migrate `command.html`, `command-group.html`, and `section-index.html` to use new templates
- **templates(legacy)**: add deprecation warning to `page-hero-api.html` with migration guide
- **tests**: add 31 unit tests for page hero template rendering
- **docs**: document new template structure and `hero_context` usage in theming guide

### Centralized `.bengal/` Cache Directory ✅

- **cache(paths)**: add `BengalPaths` class as single source of truth for all `.bengal/` directory paths
- **cache(paths)**: add `STATE_DIR_NAME` constant for consistent directory naming
- **cache(paths)**: add `migrate_template_cache()` helper for backwards-compatible migration
- **core(site)**: add `site.paths` property for centralized `.bengal/` access
- **rendering(template_engine)**: relocate template bytecode cache from `output/.bengal-cache/templates` to `.bengal/templates`
- **orchestration**: migrate all `.bengal` path references to use `BengalPaths`
- **cli**: migrate all `.bengal` path references in commands to use `BengalPaths`
- **utils**: migrate `.bengal` paths in utilities to use `BengalPaths`
- **server**: use `STATE_DIR_NAME` constant in ignore patterns
- **tests**: add 29 unit tests for `BengalPaths` class
- **docs**: document `.bengal/` directory structure in QUICKSTART.md

### Proactive Template Validation ✅

- **rendering(template_engine)**: add `validate_templates()` method for proactive syntax checking
- **rendering(template_engine)**: enable Jinja2 `do` extension for template statements (`{% do list.append(x) %}`)
- **orchestration(build)**: add optional template validation phase (runs before content discovery)
- **config**: add `validate_templates` build option (default: false) for opt-in validation
- **utils(build_stats)**: add `syntax_errors` and `not_found_errors` properties for categorizing template errors
- **tests**: add 7 unit tests for `validate_templates()` and BuildStats categorization
- **tests**: re-enable 6 integration tests for template error collection
- **docs(plan)**: RFC and implementation plan moved to completed

### Media Embed Directives ✅

- **rendering(directives/video)**: add `YouTubeDirective` with privacy-enhanced mode (youtube-nocookie.com) by default
- **rendering(directives/video)**: add `VimeoDirective` with Do Not Track mode by default
- **rendering(directives/video)**: add `SelfHostedVideoDirective` for native HTML5 video playback
- **rendering(directives/embed)**: add `GistDirective` for GitHub Gist embeds with file selection
- **rendering(directives/embed)**: add `CodePenDirective` with tab/theme/height customization
- **rendering(directives/embed)**: add `CodeSandboxDirective` with module/view customization
- **rendering(directives/embed)**: add `StackBlitzDirective` with file/view customization
- **rendering(directives/terminal)**: add `AsciinemaDirective` for terminal recording playback with ARIA accessibility
- **rendering(directives/figure)**: add `FigureDirective` for semantic images with captions (`<figure>`/`<figcaption>`)
- **rendering(directives/figure)**: add `AudioDirective` for native HTML5 audio playback
- **themes(css)**: add responsive CSS for video embeds with aspect-ratio support (`_video-embed.css`)
- **themes(css)**: add CSS for code playground embeds (`_code-embed.css`)
- **themes(css)**: add CSS for terminal recording embeds (`_terminal-embed.css`)
- **themes(css)**: add CSS for semantic figures and audio (`_figure.css`)
- **tests**: add 71 unit tests for media embed directives including security validation
- **docs(hugo-migration)**: update with media embed directive equivalents and migration table
- **docs(rfc)**: RFC moved to implemented

### Directive System v2 ✅

- **rendering(directives)**: add named closer syntax `:::{/name}` for closing directives without fence-depth counting
- **rendering(directives)**: add `BengalDirective` base class for typed directives with standardized parsing and rendering
- **rendering(directives)**: add `DirectiveToken` dataclass for typed AST tokens replacing ad-hoc dictionaries
- **rendering(directives)**: add `DirectiveOptions` base class with automatic type coercion (bool, int, str)
- **rendering(directives)**: add `DirectiveContract` system for validating parent-child nesting relationships
- **rendering(directives)**: add `ContractValidator` with warning logs for nesting violations (non-blocking)
- **rendering(directives)**: add `utils.py` with shared HTML utilities (`escape_html`, `build_class_string`, `bool_attr`, etc.)
- **rendering(directives)**: migrate 19 directive classes to `BengalDirective` base class
- **rendering(directives)**: add preset options: `StyledOptions`, `TitledOptions`, `ContainerOptions`
- **rendering(directives)**: add preset contracts: `STEPS_CONTRACT`, `STEP_CONTRACT`, `TAB_SET_CONTRACT`, `TAB_ITEM_CONTRACT`, `CARDS_CONTRACT`, `CARD_CONTRACT`
- **health(validators)**: fix `ADMONITION_TYPES` and `CODE_BLOCK_DIRECTIVES` import from rendering package (single source of truth)
- **tests**: add 80+ unit tests for foundation components (`test_foundation.py`, `test_contracts.py`)
- **tests**: add 18 unit tests for named closer syntax (`test_named_closers.py`)
- **tests**: add 11 integration tests for directive nesting validation (`test_directive_nesting.py`)
- **docs**: add comprehensive `README.md` for directive system with named closers and migration guide

### Template Functions Robustness ✅

- **rendering(strings)**: fix `truncatewords_html` to preserve HTML structure and close tags properly
- **rendering(strings)**: add `filesize` filter wrapping `humanize_bytes` for human-readable file sizes
- **rendering(strings)**: add warning log for invalid regex patterns in `replace_regex`
- **rendering(collections)**: add debug log for `sort_by` failures with heterogeneous data
- **core(site)**: add `get_page_path_map()` with version-based cache invalidation for O(1) page lookups
- **rendering(collections)**: update `resolve_pages` to use cached page path map (performance improvement)
- **tests**: add 15 unit tests for `truncatewords_html` HTML preservation and `filesize` filter
- **docs**: RFC moved to completed

### Autodoc Incremental Build Support ✅

- **server(dev_server)**: watch autodoc source directories (Python `source_dirs`, OpenAPI spec files) for changes
- **server(build_handler)**: add `_should_regenerate_autodoc()` to detect when autodoc sources change and trigger rebuilds
- **cache(autodoc_tracking)**: new `AutodocTrackingMixin` for tracking source file → autodoc page dependencies
- **cache(build_cache)**: add `autodoc_dependencies` field for selective autodoc rebuilds
- **autodoc(virtual_orchestrator)**: track dependencies in `AutodocRunResult.autodoc_dependencies` during page creation
- **orchestration(content)**: register autodoc dependencies with cache during content discovery
- **orchestration(incremental)**: selective autodoc page rebuilds based on source file changes (not all autodoc pages)
- **orchestration(incremental)**: track autodoc source file hashes in `save_cache()` for change detection
- **docs**: RFC moved to implemented

### Autodoc Resilience Improvements ✅

- **autodoc(virtual_orchestrator)**: add `AutodocRunResult` summary dataclass tracking extraction/rendering successes and failures
- **autodoc(virtual_orchestrator)**: update `generate()` to return `(pages, sections, result)` tuple for observability
- **autodoc(config)**: add `autodoc.strict` config flag (default `false`) for fail-fast mode in CI/CD
- **autodoc(virtual_orchestrator)**: enforce strict mode with partial context (failures recorded before raising)
- **autodoc(rendering/pipeline)**: tag fallback-rendered pages with `_autodoc_fallback_template: true` in metadata
- **orchestration(content)**: remove blanket exception swallow; keep `ImportError` handling, allow strict mode exceptions to propagate
- **orchestration(content)**: add `_log_autodoc_summary()` for structured logging of run results
- **tests(autodoc)**: add 16 comprehensive resilience tests covering strict mode, failure handling, and summary tracking
- **docs(autodoc)**: document strict mode, run summaries, and fallback tagging in README

### Typed Metadata Access (Phase 6) ✅

- **autodoc(utils)**: add 14 typed metadata access helpers with fallback (`get_python_class_bases`, `get_openapi_tags`, etc.)
- **autodoc(virtual_orchestrator)**: migrate `.metadata.get()` calls to typed helpers for OpenAPI endpoints
- **autodoc(extractors/python)**: use typed helpers for property detection and inheritance
- **autodoc(extractors/openapi)**: use typed helpers for path/tag determination
- **autodoc(README)**: document `typed_metadata` field and helper functions
- **tests**: add 36 comprehensive tests for typed metadata access patterns
- **docs**: RFC moved to completed

### Typed Autodoc Models (Phase 1) ✅

- **autodoc(models)**: create typed metadata dataclasses replacing untyped `metadata: dict[str, Any]`
- **autodoc(models/common)**: add `SourceLocation` and `QualifiedName` with validation
- **autodoc(models/python)**: add `PythonModuleMetadata`, `PythonClassMetadata`, `PythonFunctionMetadata`, `PythonAttributeMetadata`, `PythonAliasMetadata`
- **autodoc(models/cli)**: add `CLICommandMetadata`, `CLIGroupMetadata`, `CLIOptionMetadata`
- **autodoc(models/openapi)**: add `OpenAPIEndpointMetadata`, `OpenAPIOverviewMetadata`, `OpenAPISchemaMetadata`
- **autodoc(base)**: add `typed_metadata` field to `DocElement` with serialization support
- **autodoc(extractors)**: update Python, CLI, OpenAPI extractors to dual-write typed and untyped metadata
- **tests**: add 80+ tests for models, serialization, and extractor integration
- **docs**: RFC and plan moved to implemented

### Silent Error Elimination ✅

- **config(env_overrides)**: upgrade exception logging from DEBUG to WARNING for user-impacting failures with helpful hints
- **utils(theme_registry)**: add structured logging to `assets_exists`, `manifest_exists`, `resolve_resource_path`, and `get_installed_themes` methods
- **health(rendering)**: add logging to SEO page check failures with page context
- **health(connectivity)**: add logging to 5 graph analysis handlers (hub normalization, metrics, orphans, hubs, percentage)
- **health(navigation)**: add logging to breadcrumb ancestor check failures
- **health(cache)**: add logging to cache file read and JSON decode failures
- **health(assets)**: add logging to CSS/JS minification check failures
- **cli(theme)**: add structured logging to `_theme_exists`, `_get_template_dir_source_type`, and `features` command handlers
- **debug(config_inspector)**: add logging to `explain_key` defaults/environment layer loading and YAML parsing failures
- **debug(content_migrator)**: add logger import; add logging to `split_page` and `merge_pages` frontmatter parsing failures
- **postprocess(utils)**: add logging to URL extraction failures for callable page URLs
- **postprocess(llm_generator)**: add logging to existing file read failures in `_write_if_changed`
- **analysis(graph_visualizer)**: add logging to page URL access fallback chain
- **core(page/content)**: add logging to AST-to-HTML rendering fallback
- **rendering(jinja_utils)**: add logging to `safe_getattr` property access failures
- **tests**: update `test_exception_in_env_logic_silent` to use targeted mock for env vars, supporting new warning logging
- **docs**: RFC moved to implemented

### TemplateEngine Package Decoupling ✅

- **rendering(template_engine)**: decouple 861-line monolithic `template_engine.py` into focused package structure
- **rendering(template_engine/core)**: create thin facade class composing `MenuHelpersMixin`, `ManifestHelpersMixin`, `AssetURLMixin`
- **rendering(template_engine/environment)**: extract `create_jinja_environment()`, `resolve_theme_chain()`, `read_theme_extends()`
- **rendering(template_engine/asset_url)**: consolidate asset URL generation with `file://` protocol support
- **rendering(template_engine/menu)**: extract menu caching helpers
- **rendering(template_engine/manifest)**: extract asset manifest loading/caching
- **rendering(template_engine/url_helpers)**: URL generation utilities (`url_for`, `with_baseurl`, `filter_dateformat`)
- **docs**: update docstring references in `template_profiler.py` and `template_functions.py`
- **docs**: RFC moved to implemented

### Virtual Section Page Reference Fix ✅

- **core(page)**: fix critical bug where virtual pages had flat navigation instead of hierarchical
- **core(page)**: add `_section_url` field for URL-based section lookups (virtual sections have `path=None`)
- **core(page)**: update `_section` setter/getter to use URL for virtual sections, path for regular sections
- **core(site)**: add `get_section_by_url()` and `_section_url_registry` for O(1) virtual section lookups
- **core(site)**: consolidate `_setup_page_references` into Site (removed duplicate in ContentOrchestrator)
- **core(site)**: add `_validate_page_section_references()` for post-discovery validation warnings
- **tests**: add 6 unit tests for virtual section navigation hierarchy
- **docs**: RFC moved to implemented

### Centralized Path Resolution Architecture ✅

- **utils**: add `PathResolver` utility class for consistent path resolution relative to site root
- **utils(path_resolver)**: add `resolve()`, `resolve_many()`, `resolve_if_exists()` for flexible resolution
- **utils(path_resolver)**: add security methods `is_within_base()` and `relative_to_base()` for path traversal protection
- **core(site)**: ensure `Site.root_path` is always absolute (resolved in `__post_init__`)
- **rendering(directives)**: remove `Path.cwd()` fallback from `LiteralIncludeDirective`, `IncludeDirective`, `GlossaryDirective`, `DataTableDirective`
- **tests**: add `test_path_resolver.py` with 20 tests covering PathResolver and Site path resolution
- **docs**: RFC moved to implemented

### Documentation Cleanup ✅

- **site(homepage)**: simplify to focus on features and getting started
- **README**: streamline to essential info only
- **docs(about)**: remove philosophy/positioning content, keep practical info
- **docs(comparison)**: simplify to feature comparison table
- **docs(limitations)**: condense to brief list of constraints
- **docs(get-started)**: simplify to install + quickstart paths
- **docs(index)**: clean up to straightforward navigation
- **plan**: move marketing-positioning-strategy.md to implemented/

### Progressive Enhancements Architecture ✅

- **themes(js)**: add `bengal-enhance.js` (~1.5KB) progressive enhancement loader with registry, auto-discovery, and lazy-loading
- **themes(js)**: add `enhancements/` directory with modular enhancement scripts (`theme-toggle`, `mobile-nav`, `tabs`, `toc`)
- **themes(js)**: unified `data-bengal` attribute pattern for declaring enhancements (e.g., `<div data-bengal="tabs">`)
- **themes(js)**: enhancement configuration via additional `data-`* attributes (booleans, numbers, JSON parsed automatically)
- **themes(js)**: MutationObserver watches for dynamic content and auto-enhances new elements
- **themes(base.html)**: load enhancement loader before other scripts; add configuration for base URL and debug mode
- **themes(base.html)**: add `data-bengal` attributes to mobile-nav, back-to-top, and lightbox components
- **themes(partials)**: add `data-bengal` to search-modal and toc-sidebar components
- **config**: add `[enhancements]` config section with `watch_dom`, `debug`, and `base_url` options
- **docs**: add enhancement README with usage examples and custom enhancement guide

### Systematic Observability Improvements ✅

- **utils**: add `observability.py` module with `ComponentStats` dataclass and `HasStats` protocol for standardized stats collection
- **utils(observability)**: `ComponentStats` provides uniform interface for counts, cache metrics, sub-timings, and custom metrics
- **utils(observability)**: `format_summary()` produces compact CLI output with processing/skip/cache/timing stats
- **utils(observability)**: `to_log_context()` flattens stats to dict for structured logging integration
- **utils(observability)**: add `format_phase_stats()` helper for displaying slow phase diagnostics
- **health(report)**: enhance `ValidatorStats` with `cache_hit_rate`, `skip_rate`, `metrics`, and `to_log_context()` methods
- **health(links)**: add stats tracking to `LinkValidatorWrapper` with link counts and validation timings
- **health(output)**: add stats tracking to `OutputValidator` with HTML file counts and asset metrics
- **orchestration(finalization)**: show detailed stats for ALL slow validators (>500ms) instead of just the slowest
- **tests**: add `test_observability.py` with 29 tests covering ComponentStats formatting and HasStats protocol
- **docs**: RFC moved to implemented

### Build-Integrated Validation ✅

- **health**: add tiered validation with `build`, `full`, and `ci` tiers for configurable health check granularity
- **health**: add `_is_validator_in_tier()` method for tier-based validator filtering
- **health(directives)**: use cached content from BuildContext, eliminating redundant disk I/O (4.6s → 64ms)
- **health(directives)**: only check rendered HTML for pages with directives (7.6s → ~1s)
- **utils(autodoc)**: fix overly broad "Generated by Bengal" detection; use specific "Generated by Bengal autodoc" marker
- **config**: add `build_validators`, `full_validators`, `ci_validators` to health_check defaults
- **tests**: add `test_build_integrated_validation.py` with 19 tests covering content caching, tiered validation, and analyzer integration
- **docs**: RFC moved to implemented

### Zstandard Cache Compression (PEP 784) ✅

- **cache**: add `compression.py` module with Zstd utilities using Python 3.14's `compression.zstd` (PEP 784)
- **cache(CacheStore)**: save cache files as `.json.zst` with 92-93% size reduction (12-14x compression)
- **cache(CacheStore)**: auto-detect format on load for seamless migration from uncompressed `.json`
- **cache(BuildCache)**: update `_save_to_file()` and `_load_from_file()` with compression support
- **cache**: add `save_compressed()`, `load_compressed()`, `load_auto()`, `migrate_to_compressed()` utilities
- **cache**: cache I/O now 10x faster (0.5ms load vs 5ms), 3x faster save (1ms vs 3ms)
- **tests**: add `test_compression.py` with 20 tests for round-trip, format detection, and migration
- **docs**: update cache and performance architecture documentation
- **ci**: compressed caches reduce CI/CD transfer size by 16x (1.6MB → 100KB)

### Parallel Health Check Validators ✅

- **health**: run validators in parallel using `ThreadPoolExecutor` for 50-70% faster health checks
- **health**: add `_run_validators_parallel()` method with auto-scaling worker count
- **health**: add `_run_validators_sequential()` method for workloads below threshold
- **health**: add `_get_optimal_workers()` for CPU-aware auto-scaling (50% of cores, 2-8 range)
- **health**: add `PARALLEL_THRESHOLD` (3 validators) to avoid thread overhead for small workloads
- **health**: add `_is_validator_enabled()` helper method for cleaner profile/config filtering
- **health**: add `_run_single_validator()` helper for isolated validator execution with error handling
- **health**: error isolation ensures one validator crash doesn't affect others
- **health**: add `HealthCheckStats` dataclass with speedup/efficiency metrics
- **health**: add `last_stats` property for observability (total_duration_ms, speedup, efficiency)
- **health**: verbose mode shows execution mode, worker count, and performance metrics
- **tests**: add `test_health_check.py` with 21 tests for parallel execution, auto-scaling, and observability

### Remove Experimental Reactive Dataflow Pipeline ❌

- **pipeline**: remove `bengal/pipeline/` module (15 files) - experimental reactive dataflow system had fundamental architectural gaps
- **cli(build)**: remove `--pipeline` flag from build command
- **cli(serve)**: remove `--pipeline` flag from serve command
- **core(site)**: remove `_build_with_pipeline()` method and `use_pipeline` parameter from `build()` and `serve()`
- **server**: remove `use_pipeline` propagation from `DevServer` and `BuildHandler`
- **tests**: remove `tests/unit/pipeline/` (9 files) and `tests/integration/test_pipeline_build.py`
- **docs**: move pipeline planning docs to `plan/completed/` (4 files archived)
- **Note**: `RenderingPipeline` (page rendering) and `assets.pipeline` (SCSS/PostCSS) are unrelated and retained

### Directive Registry - Single Source of Truth ✅

- **rendering(directives)**: add `DIRECTIVE_NAMES` class attribute to all 27 directive classes
- **rendering(directives)**: add `DIRECTIVE_CLASSES` registry and `get_known_directive_names()` function
- **rendering(directives)**: replace manual `KNOWN_DIRECTIVE_NAMES` with computed version from class attributes
- **tests**: add `test_directive_registry.py` with 47 tests for registry consistency and registration verification
- **health**: health check now uses single source of truth from rendering package (no more drift)

### Page Visibility System ✅

- **core(page)**: add `hidden` frontmatter shorthand for unlisted pages (excludes from nav, listings, sitemap, search, RSS)
- **core(page)**: add `visibility` object for granular control (menu, listings, sitemap, robots, render, search, rss)
- **core(page)**: add `in_listings`, `in_sitemap`, `in_search`, `in_rss`, `robots_meta` properties
- **core(page)**: add `should_render_in_environment()` for environment-aware rendering (local vs production)
- **core(site)**: add `listable_pages` property that respects visibility settings
- **postprocess(sitemap)**: exclude hidden pages from sitemap.xml
- **postprocess(rss)**: exclude hidden pages from RSS feeds
- **postprocess(search)**: exclude hidden pages from search index
- **rendering(navigation)**: integrate visibility.menu with auto-nav discovery
- **themes(default)**: add robots meta tag injection for hidden pages (noindex, nofollow)
- **themes(default)**: add visual indicator banner for hidden pages in dev server

### Documentation Information Architecture Overhaul

- **docs(ia)**: reorganize documentation by feature dimensions (content, theming, building, extending) instead of Diataxis types
- **docs(tutorials)**: create dedicated tutorials section for guided learning journeys
- **docs(content)**: add content dimension with organization, authoring, collections, sources, and reuse sections
- **docs(theming)**: add theming dimension with templating, assets, and themes sections
- **docs(building)**: add building dimension with configuration, commands, performance, and deployment sections
- **docs(extending)**: add extending dimension with autodoc, analysis, validation, and architecture sections
- **docs(recipes)**: expand recipes with dark-mode, rss-feed, reading-time, table-of-contents, syntax-highlighting
- **docs(snippets)**: add `_snippets/` directory for reusable content fragments (install, prerequisites, warnings)
- **docs(navigation)**: add URL aliases for backward compatibility with previous structure
- **docs(get-started)**: rename getting-started/ to get-started/ with streamlined quickstarts
- **docs**: update build pipeline concepts with reactive pipeline section

### Content Layer API (Remote Content Sources)

- **content_layer**: add unified content abstraction for fetching from any source (local, GitHub, REST APIs, Notion)
- **content_layer(entry)**: add `ContentEntry` dataclass as source-agnostic content representation
- **content_layer(source)**: add `ContentSource` abstract base class defining the loader protocol
- **content_layer(sources/local)**: add `LocalSource` for filesystem content with frontmatter parsing
- **content_layer(sources/github)**: add `GitHubSource` for fetching markdown from GitHub repos
- **content_layer(sources/rest)**: add `RESTSource` for fetching content from REST APIs with field mapping
- **content_layer(sources/notion)**: add `NotionSource` for fetching pages from Notion databases
- **content_layer(manager)**: add `ContentLayerManager` for orchestrating multi-source fetching with caching
- **content_layer(loaders)**: add factory functions (`local_loader`, `github_loader`, `rest_loader`, `notion_loader`)
- **collections**: extend `CollectionConfig` with optional `loader` parameter for remote content
- **collections**: add `is_remote` and `source_type` properties to `CollectionConfig`
- **cli(sources)**: add `bengal sources` command group (list, status, fetch, clear)
- **cli(sources)**: add REST loader to installation hints
- **pyproject.toml**: add optional dependencies for remote sources (`github`, `notion`, `rest`, `all-sources`)
- **content_layer(loaders)**: fix incorrect `bengal[github]` references to `bengal[rest]` in rest_loader

### Cache & Incremental Build Improvements

- **cache**: add global config hashing for automatic cache invalidation when configuration changes
- **config**: add `compute_config_hash()` utility for deterministic hashing of resolved config state
- **cache(build_cache)**: add `config_hash` field and `validate_config()` method for config-based invalidation
- **orchestration(incremental)**: use config hash instead of file tracking for robust config change detection
- **core(site)**: compute and expose `config_hash` property capturing effective configuration state

### Code Quality & Contributor Experience

- **orchestration(build)**: refactor 894-line `build()` method into 20 focused `_phase_`* methods (~50-100 lines each)
- **orchestration(build)**: fix duplicate phase numbers (two "Phase 5.5", two "Phase 9") with sequential renumbering
- **orchestration(build)**: add comprehensive docstrings to all phase methods documenting purpose and side effects
- **utils(build_context)**: extend BuildContext dataclass with all fields needed for phase method communication
- **utils(autodoc)**: add `is_autodoc_page()` utility for shared autodoc page detection
- **health(directives)**: refactor 1,094-line `directives.py` into focused package (constants, analysis, checkers)
- **cli(new)**: refactor 1,088-line `new.py` into focused package (presets, wizard, config, site, scaffolds)
- **analysis(graph_reporting)**: improve exception handling with specific types and debug logging
- **postprocess(output_formats)**: consolidate duplicate `strip_html`/`generate_excerpt` to use `bengal.utils.text`

### CLI UX Improvements

- **cli(site)**: deprecate `bengal site new` in favor of `bengal new site` (hidden from help, shows warning)
- **cli(new)**: add interactive baseurl prompt during site creation (skipped with `--no-init`)
- **cli(new)**: enforce `questionary` as core dependency (remove try/except fallback)
- **cli(health)**: hide 8 advanced linkcheck options from `--help` (still functional when used)

### Security & Robustness Hardening (Phase 1)

- **rendering(link_validator)**: implement actual internal link validation with URL resolution and page URL index lookup
- **rendering(include)**: add `MAX_INCLUDE_SIZE` (10MB) file size limit to prevent memory exhaustion from large includes
- **rendering(include/literalinclude)**: reject symlinks to prevent path traversal attacks
- **discovery**: add inode-based symlink loop detection to prevent infinite recursion
- **discovery**: handle permission errors gracefully when walking directories

### Feature Correctness Hardening (Phase 2)

- **utils**: add `file_lock` module for cross-platform file locking (fcntl on Unix, msvcrt on Windows)
- **cache**: integrate file locking into `BuildCache.save()`/`load()` for concurrent build safety
- **cache**: refactor save/load into separate lock acquisition and file I/O methods for clarity
- **analysis(knowledge_graph)**: graph analysis commands now correctly extract links via `_ensure_links_extracted()`
- **rendering(template_engine)**: template cycles already handled by Jinja2 native detection + rich error formatting

### Developer Experience Hardening (Phase 3)

- **rendering(i18n)**: add debug warning for missing translation keys with once-per-key deduplication
- **rendering(i18n)**: add `reset_translation_warnings()` for build isolation
- **rendering(template_engine)**: add visible stderr warning when theme not found (in addition to log)
- **postprocess(sitemap)**: skip sitemap generation gracefully when site has no pages
- **postprocess(rss)**: skip RSS generation gracefully when no pages have dates

### Health Check System Enhancements (Phase 1 & 2)

- **health**: add incremental validation with result caching (Phase 1)
- **health**: extend BuildCache with validation_results field for caching CheckResult objects
- **health**: add CheckResult serialization (to_cache_dict/from_cache_dict) for caching
- **health**: add incremental and context-aware validation to HealthCheck.run()
- **health**: create standalone `bengal validate` CLI command with --file, --changed, --incremental, --watch options
- **health**: integrate incremental validation into build orchestrator (automatic in dev server)
- **health**: add progressive severity system with SUGGESTION level (Phase 2.1)
- **health**: update CheckResult with suggestion() method and is_actionable() helper
- **health**: update report formatting to handle suggestions (collapsed unless --suggestions)
- **health**: add --suggestions flag to bengal validate command
- **health**: create AutoFixer framework with FixAction and FixSafety levels (Phase 2.2)
- **health**: add `bengal fix` command for auto-fixing common issues
- **health**: implement directive fence nesting auto-fix (SAFE level)
- **health**: add watch mode for continuous validation (`bengal validate --watch`) (Phase 2.3)
- **health**: update build_quality_score to include suggestions (0.9 points)
- **cache**: bump BuildCache.VERSION to 2 for validation_results field

### Theme Configuration Consolidation ✅

- **themes(config)**: consolidate theme configuration into single `theme.yaml` file
- **themes(config)**: add `ThemeConfig` dataclass with `load()` method for validated configuration
- **themes(config)**: add `FeatureFlags`, `AppearanceConfig`, `IconConfig` nested dataclasses
- **themes(default)**: create `theme.yaml` with features, appearance, and icon aliases
- **themes**: remove deprecated `features.py` Python registry (migrated to YAML)
- **docs**: RFC-001 moved to implemented

### Lazy Build Artifacts ✅

- **utils(build_context)**: add lazy `knowledge_graph` property to eliminate 3x redundant graph construction
- **orchestration(postprocess)**: use `build_context.knowledge_graph` instead of building local graph
- **orchestration(streaming)**: accept `build_context` and use shared knowledge graph
- **health(connectivity)**: use shared graph from build context
- **perf**: ~400-1000ms faster builds by eliminating redundant graph construction
- **docs**: RFC moved to implemented

### Progressive Enhancements Architecture ✅

- **themes(js)**: formalize `data-bengal` attribute pattern for declaring enhancements
- **themes(js)**: add central enhancement registry with auto-discovery
- **themes(js)**: implement conditional script loading for all enhancements
- **docs**: formalize "layered enhancement" philosophy (HTML works, CSS delights, JS elevates)
- **docs**: RFC moved to implemented

### Orchestrator Performance Improvements ✅

- **cache(build_cache)**: add `rendered_output` cache for full HTML caching
- **cache(build_cache)**: add `FileFingerprint` with mtime+size fast path (~200ms saved)
- **rendering(template_engine)**: leverage Jinja2 `FileSystemBytecodeCache` for template caching
- **discovery(content)**: parallel content discovery via `ThreadPoolExecutor`
- **orchestration(incremental)**: add `_get_changed_sections()` for section-level invalidation
- **cache(dependency_tracker)**: implement `get_affected_pages()` for dependency-aware rebuilds
- **docs**: RFC Phase 1 & 2 moved to implemented

### Utility Extraction and Consolidation ✅

- **utils(hashing)**: consolidate SHA256 hashing utilities from 12+ files into single module
- **utils(retry)**: extract exponential backoff retry logic with sync and async variants
- **utils(thread_local)**: add `ThreadLocalCache[T]` generic class for thread-safe caching
- **perf**: eliminate ~150 lines of duplicated logic across codebase
- **docs**: RFC moved to implemented

## 0.1.4 - 2025-11-25

### Configuration System Overhaul (MAJOR)

- **config**: introduce directory-based configuration system with `config/_default/`, `environments/`, and `profiles/` support
- **config**: add environment-aware configuration with auto-detection (Netlify, Vercel, GitHub Actions)
- **config**: add build profiles (`writer`, `theme-dev`, `dev`) for optimized workflows
- **config**: add smart feature toggles that expand into detailed configuration
- **config**: add CLI introspection commands (`bengal config show`, `doctor`, `diff`, `init`)
- **config**: maintain 100% backward compatibility with single-file configs (`bengal.toml`, `bengal.yaml`)
- **cli**: add `--environment/-e` and `--profile` flags to build and serve commands

### Assets & Build Pipeline

- **core/assets**: add deterministic `asset-manifest.json`, manifest-driven `asset_url` resolution, CLI inspection (`bengal assets status`), stale fingerprint cleanup, and `--clean-output` builds to keep dev/prod CSS in sync
- **assets**: improve fingerprint handling and cleanup of stale artifacts

### HTML Output Formatting (NEW!)

- **rendering**: add safe HTML formatter with three modes (raw/pretty/minify)
- **config**: add `[html_output]` configuration section with per-page `no_format` override
- **rendering**: integrate HTML formatter before write with comprehensive test coverage

### Health & Validation

- **health**: add async link checker with comprehensive validation (`bengal health linkcheck`)
- **health**: auto-build site and purge cache before checking links to eliminate false positives
- **cli**: add `--traceback` flag for configurable traceback display

### Core Architecture Improvements

- **core(page)**: refactor PageProxy to wrap PageCore directly for better cache-proxy contract enforcement
- **core(page)**: add PageCore dataclass with cacheable fields, simplifying cache operations
- **core(site)**: add path-based section registry with O(1) lookup for stable section references
- **core(config)**: add `stable_section_references` feature flag for path-based section tracking
- **cache**: refactor IndexEntry to implement Cacheable protocol for type safety
- **orchestration**: simplify cache save operations using PageCore composition

### Autodoc Enhancements

- **autodoc**: add URL grouping with auto-detection, explicit prefix mapping, and off modes
- **autodoc**: add alias detection and inherited member synthesis with configurable display
- **autodoc**: keep auto grouping scoped to top-level packages
- **autodoc**: update navigation block and template fixes

### CLI Enhancements

- **cli**: add command metadata system for discovery and documentation
- **cli**: add progress feedback to long-running operations
- **cli**: standardize CLIOutput usage across all commands
- **cli**: add unified helpers for error handling, site loading, and traceback config
- **cli**: add theme debug CLI with file protocol support
- **cli**: improve help text and command organization

### Theme & CSS Improvements

- **themes(css)**: complete CSS modernization phases 1-4 with logical properties, nesting, container queries, and modern features
- **themes(css)**: consolidate typography to single `.prose` system; remove `.has-prose-content`; simplify page-header
- **themes**: enhance mermaid toolbar with pan/zoom and reliable initialization
- **themes**: preserve mermaid syntax before rendering to fix copy action
- **themes(changelog)**: adopt action-bar breadcrumb component in changelog templates
- **rendering(themes)**: adopt action-bar breadcrumb component in CLI and API reference templates
- **rendering(theme)**: add fluid text effects with glow and diagonal swirling motion for mascot
- **fix(css)**: correct `@supports` syntax to use property-value pairs for W3C validation

### Rendering & Content

- **rendering(cards)**: add explanation variant with enhanced list/table styling
- **rendering**: balance header nav padding; reduce bottom padding to match top
- **server**: fix spurious dev server reloads and enable proper live reload injection
- **server**: force full rebuild on file create/delete/move events to preserve section relationships

### Documentation

- **docs(site)**: add concepts section with configuration, assets, and output formats documentation
- **docs(templates)**: update README to reflect `.prose-only` typography system
- **docs**: add spacing optimization summary and CSS modernization progress tracking
- **docs(getting-started)**: add persona-based quickstarts and enhance list-table with markdown support
