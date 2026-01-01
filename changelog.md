## [Unreleased]

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
- **core(parsers)**: Add Patitas as optional markdown parser with typed AST and O(n) lexer
- **patitas**: Directive and role systems for extensible markup (Phase 2)
- **patitas(directives)**: Complete Bengal directive migration — 54 handlers with full parity
- **patitas**: Zero-Copy Lexer Handoff (ZCLH) protocol for Rosettes integration
- **patitas(parser)**: Fix list termination when followed by non-indented paragraph

### 🚀 Rosettes Syntax Highlighter ✅
- **rosettes**: Pure-Python syntax highlighter for Python 3.14t (no GIL re-enablement)
- **lexers**: 50+ language support including tree, myst, jinja2, configs, diagrams
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
- **perf**: ~40% reduction in `.bengal/` directory size (~2.8M savings)

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
- **themes(js)**: enhancement configuration via additional `data-*` attributes (booleans, numbers, JSON parsed automatically)
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
- **orchestration(build)**: refactor 894-line `build()` method into 20 focused `_phase_*` methods (~50-100 lines each)
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
