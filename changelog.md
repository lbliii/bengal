## Unreleased

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
