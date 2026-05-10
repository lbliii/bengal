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
