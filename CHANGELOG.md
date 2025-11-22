# Changelog

All notable changes to Bengal SSG will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Cacheable Protocol**: Type-safe cache contracts for all cacheable types
  - Generic `Cacheable` protocol with `to_cache_dict()` and `from_cache_dict()` methods
  - `CacheStore` helper for type-safe save/load operations with version management
  - Adopted in `PageCore`, `TagEntry`, and `AssetDependencyEntry`
  - Comprehensive test coverage (63 tests for protocol, roundtrip, and properties)
  - Documentation in code with extensive examples and guidelines
- **Config Directory Structure (v2.0)**: Major configuration system overhaul (#48)
  - **Directory-Based Configuration**: Hugo-style `config/` directory structure
    - `_default/`: Base configuration (site.yaml, build.yaml, content.yaml, theme.yaml, features.yaml, params.yaml)
    - `environments/`: Environment-specific overrides (local.yaml, preview.yaml, production.yaml)
    - `profiles/`: Persona-based configs (writer.yaml, theme-dev.yaml, dev.yaml)
  - **Intelligent Environment Detection**: Auto-detects deployment context
    - Netlify, Vercel, GitHub Actions, or defaults to `local`
    - Override with `--environment/-e` flag or `BENGAL_ENV` variable
  - **Build Profiles**: Optimize for different workflows
    - `writer`: Fast builds with quiet output
    - `theme-dev`: Template debugging with verbose errors
    - `dev`: Full observability with all checks enabled
  - **Smart Feature Toggles**: Ergonomic feature expansion
    - `rss: true` → `generate_rss: true`, `output_formats: [rss]`
    - `search: true` → `search.enabled: true`, `search.preload: smart`
    - `json: true` → `output_formats: [json]`, generate JSON content API
    - See `bengal/config/feature_mappings.py` for all mappings
  - **Configuration Precedence** (lowest to highest priority):
    - `_default/*.yaml` → `environments/{env}.yaml` → `profiles/{profile}.yaml` → env vars → CLI flags
  - **Origin Tracking**: Introspection shows where each config value originates
  - **Introspection CLI Commands**:
    - `bengal config show [--origin] [--environment ENV]` - Display merged config with optional origin tracking
    - `bengal config doctor` - Validate YAML syntax, types, and values with helpful error messages
    - `bengal config diff --environment ENV --against OTHER` - Compare configurations between environments
    - `bengal config init [--type directory]` - Scaffold new config/ structure for existing projects
  - **CLI Integration**: New flags for build/serve commands
    - `--environment/-e ENV`: Select environment configuration
    - `--profile PROFILE`: Apply build profile
    - `bengal serve` defaults to `local` environment
  - **Backward Compatibility**: Seamless migration path
    - Single-file configs (bengal.toml/bengal.yaml) still fully supported
    - Config directory takes precedence when both exist
    - No breaking changes for existing projects
  - **Comprehensive Examples**:

### Enhanced
- **Autodoc Template Cache**: Intelligent LRU caching system for template rendering
  - Configurable cache size (default: 1000 entries) with automatic eviction
  - LRU (Least Recently Used) eviction strategy removes 20% of entries when cache is full
  - Built-in performance tracking with hit rate and usage statistics
  - Template hash-based cache invalidation for changed templates
  - Memory-efficient access time tracking for optimal performance
  - Cache statistics API for monitoring and debugging
    - `config.example/`: Fully annotated reference configs with inline documentation
    - Main documentation site (`site/`) migrated to new system as real-world example
  - **Test Coverage**: 109 tests (95 unit + 14 integration)
    - 100% coverage of new config modules
    - Environment override tests
    - Profile precedence tests
    - Feature expansion validation
    - Error handling and edge cases
  - **Deep Merge Engine**: Intelligent config merging
    - Nested key support (e.g., `search.enabled`)
    - List appending (not replacing)
    - Deterministic merge order
  - **Configuration Organization**: Clear separation of concerns
    - `site.yaml`: Site metadata (title, baseurl, languages)
    - `build.yaml`: Build settings (output_dir, parallel, caching)
    - `content.yaml`: Content processing (reading_speed, excerpt_length, toc_depth)
    - `theme.yaml`: Appearance and display (palette, navigation, sidebar)
    - `features.yaml`: What gets generated (rss, sitemap, search, json)
    - `params.yaml`: Custom user-defined parameters
  - **YAML-First Design**: Recommended format with TOML backward compatibility
  - **New Site Templates**: `bengal new site` creates complete config/ directory structure
    - Template-specific sensible defaults (blog vs docs)
    - All 6 config files scaffolded with comments
    - Users can customize without creating files from scratch
- **HTML Output Formatter**: Produce pristine HTML by default with safe formatting
  - New module `bengal.postprocess.html_output.format_html_output`
  - Modes: `raw`, `pretty`, `minify` (default driven by `minify_html` or `[html_output]`)
  - Preserves whitespace inside `pre`, `code`, `textarea`, `script`, `style`
  - Optional comment stripping (keeps IE conditionals)
  - Config: `[html_output] mode, remove_comments, collapse_blank_lines`
  - Per-page escape hatch: `no_format: true` in front matter
  - Integrated into rendering pipeline before write (cache-hit path included)
- **Link Checker**: New `bengal health linkcheck` command for comprehensive link validation
  - Async external link checking with HTTP requests (powered by httpx)
  - Internal link validation for page-to-page and anchor links
  - Configurable concurrency (default: 20 concurrent, 4 per-host to avoid rate limits)
  - Exponential backoff with jitter for failed requests
  - Intelligent retry logic (default: 2 retries with 0.5s base backoff)
  - HEAD first with fallback to GET on 405/501 responses
  - Ignore policies: URL patterns (regex), domains, and status code ranges
  - Multiple output formats: console (default) and JSON
  - CLI flags: `--external-only`, `--internal-only`, `--format json`, `--exclude`, `--ignore-status`
  - Configuration via `[health.linkcheck]` in bengal.toml
  - Example: `bengal health linkcheck --ignore-status "500-599" --format json --output report.json`
  - Perfect for CI/CD pipelines to catch broken links before deployment

### Fixed
- **Search Result Links**: Fixed broken search result links on deployed sites with baseurl
  - Search results now correctly navigate to pages on GitHub Pages and similar deployments
  - Links now properly include the baseurl prefix (e.g., `/bengal/cli/new/site/`)
  - Changed priority from `page.uri` to `page.url` in search result href construction
  - Maintains backward compatibility with sites without baseurl
- **CI Test Stability**: Fixed pytest-xdist worker crashes in GitHub Actions
  - Added `@pytest.mark.parallel_unsafe` to tests using ThreadPoolExecutor internally
  - Added `--dist worksteal` and `--max-worker-restart=3` to CI configuration for robustness
  - Documented parallel test safety guidelines in tests/README.md
  - Eliminated "node down: Not properly terminated" errors from nested parallelism
- **Dev Server Stability**: Fixed incremental build issues causing broken URLs and layouts
  - Section references now survive object recreation across rebuilds via path-based section registry
  - Fixed PageProxy missing `parent` and `ancestors` properties (broken breadcrumbs and navigation)
  - Fixed cache saving stale data before cascades applied (wrong page types, broken layouts)
  - Fixed duplicate cache entries from path normalization issues (inconsistent metadata)
  - Fixed infinite rebuild loop from `.bengal-serve.log` triggering file watcher
  - Added O(1) path-based section registry for stable lookups across incremental rebuilds
  - Comprehensive test coverage for section stability and cache consistency

## [0.1.3] - 2025-10-20

### Major Release: Performance, Stability, Theme Enhancements & Critical Bug Fixes

This release delivers significant performance improvements, critical bug fixes for incremental builds, comprehensive CLI theming, and extensive theme enhancements. Includes major refactoring for better architecture and a complete test infrastructure overhaul.

### Added

- **CLI Output Theming**: Introduced branded color palette and semantic styling system
  - New vibrant orange (`#FF9D00`) as primary brand color for Bengal identity
  - Comprehensive color palette with hex precision for cross-platform consistency
  - Semantic style tokens (success, warning, error, header, path, etc.) replace direct color codes
  - Enhanced header rendering with Panel component for visual prominence
  - Improved maintainability through centralized color definitions
  - Complete color accessibility documentation with WCAG analysis (see `bengal/utils/COLOR_PALETTE.md`)
  - 29 comprehensive unit tests for semantic styling
  - 14 integration tests covering real CLI command scenarios

- BuildContext DI: Introduced `bengal.utils.build_context.BuildContext` and threaded through render/postprocess to remove temporary `site.pages`/`site.assets` mutation
- ProgressReporter: Added `bengal.utils.progress.ProgressReporter` protocol with Rich adapter; routed orchestration/render logging through reporter
- TemplateValidationService: Added `bengal.services.validation.TemplateValidationService` and default implementation; CLI `--validate` now depends on service rather than direct engine/validator
- Theme resolution utility: Extracted theme chain and template dir resolution into `bengal.utils.theme_resolution` for decoupling
- Renderer context: Added `pages` alias for list templates and support for `changelog` type
- **Fast Mode**: Added `--fast` flag and `fast_mode` config option for maximum build speed
  - Enables quiet output for minimal overhead
  - Ensures parallel rendering is enabled
  - Can be enabled via CLI (`bengal site build --fast`) or config (`fast_mode = true`)
  - Combine with `PYTHON_GIL=0` to suppress warnings in free-threaded Python
  - Ideal for users trying out Bengal's performance, especially with Python 3.14t

### Performance

- **Page Subset Caching**: Added cached properties for filtered page lists in `Site`
  - Reduced page equality checks by 75% (446K → 112K at 400 pages)
  - Added `Site.regular_pages` and `Site.generated_pages` cached properties
  - Updated all orchestration code paths to use cached properties
  - Eliminates repeated O(n) filtering across build orchestration
- **Parallel Related Posts**: Related posts computation now uses parallel processing
  - Threshold: 100+ pages (avoids overhead on small sites)
  - 10k page site: 120s → 16s on Python 3.14t (7.5x faster)
  - 10k page site: 120s → 40-50s on Python 3.13 (2.4-3x faster)
  - Automatic detection and use of site config `max_workers`

### Fixed

- **CRITICAL: CLI console theme initialization**: Fixed `MissingStyle` error causing all CLI commands to crash
  - Error: "Failed to get style 'header'; unable to parse 'header' as color"
  - Root cause: `CLIOutput` was creating Console without `bengal_theme`, breaking semantic style tokens
  - Impact: ALL CLI commands (clean, build, etc.) failed in production use
  - Solution: Use `get_console()` singleton which includes theme, not raw `Console()`
  - Prevention: Added 14 integration tests to catch theme initialization issues before release

- **PageProxy template compatibility**: Fixed error `'PageProxy' object has no attribute 'meta_description'` by adding missing property accessors to PageProxy
  - Added lazy-loaded computed properties: `meta_description`, `reading_time`, `excerpt`
  - Added metadata properties: `is_home`, `is_section`, `is_page`, `kind`, `description`, `draft`, `keywords`
  - Added setter for `rendered_html` to support rendering phase assignments
  - Ensures templates work correctly with both Page and PageProxy objects in incremental builds

- **Autodoc CLI template selection**: Fixed CLI command documentation pages not rendering with sidebar navigation
  - Changed autodoc command template to set `type: cli-reference` instead of `type: cli-command`
  - Ensures individual CLI command pages use the `cli-reference/single.html` template with proper sidebar navigation
  - Pages now correctly render with the full documentation layout including command navigation

- **CRITICAL: Incremental build non-determinism**: Fixed bug where incremental and full builds produced different HTML output, violating core SSG contract
  - **Root causes identified and fixed:**
    1. PageProxy missing `permalink` property → broken navigation links in incremental builds
    2. PageProxy missing `_site` reference → permalink couldn't resolve baseurl
    3. PageProxy missing `output_path` → postprocessing skipped cached pages (.txt/.json not generated)
    4. Stale PageProxy objects in `site.pages` during postprocessing → generated output with old content
    5. Navigation cross-dependencies not tracked → adjacent pages not rebuilt when page title changed
  - **Solutions implemented:**
    - Added PageProxy.permalink property with lazy delegation to full Page
    - Set `_site` and `output_path` on PageProxy during discovery
    - Transfer `_site`/`_section` when lazy-loading full page
    - Added Phase 8.4 in build orchestrator: replace stale proxies with fresh pages before postprocessing
    - Track navigation dependencies: rebuild prev/next pages when page changes
  - **Impact:** Incremental builds now produce byte-identical output to full builds
  - **Testing:** Comprehensive deterministic test validates incremental == full for same content

- **Incremental build regression**: Fixed critical `'str' object has no attribute 'path'` error blocking rebuild scenarios
  - PageProxy stores section metadata as string path, not Section object
  - Added safe attribute checking before accessing `.path` on page.section
  - Resolves complete failure of incremental builds on second and subsequent runs
  - Incremental caching now works correctly after initial full build

### Changed

- **Code quality**: Removed dead code - unused exception variables, deprecated classes (ResponseBuffer), unused WIP stubs (TablePlugin), and verified false positives from static analysis

- **Default Theme Appearance**: Removed legacy light/dark toggle button in favor of a single dropdown-based Appearance control
  - Dropdown now manages Mode (System/Light/Dark) and Brand/Palette
  - Kept `theme-toggle.js` for initialization and dropdown wiring; `.theme-toggle` button support remains for backwards compatibility but is no longer used by default
  - Updated docs to reflect the change

- **Parallel Taxonomy Generation**: Tag page generation now uses parallel processing
  - Threshold: 20+ tags (avoids overhead on small sites)
  - 10k page site with 800 tags: 24s → 4s on Python 3.14t (6x faster)
  - 10k page site with 800 tags: 24s → 8-12s on Python 3.13 (2-3x faster)
  - Combined savings: ~2 minutes on large site full builds (Python 3.14t)

- **List-Table Directive**: Added MyST-compatible `list-table` directive for autodoc templates
  - Fixes pipe character issues in type annotations (e.g., `str | None`)
  - Renders parameters and attributes as proper HTML tables with dropdowns
  - Supports inline markdown (backticks render as `<code>` tags)
  - Comprehensive test coverage (6 tests)

### Refactoring

- Build orchestration: pass explicit page/asset lists across phases; eliminate Site field swapping
- Rendering pipeline: accept optional BuildContext; DI for parser/engine/enhancer; log routing via reporter
- Streaming/render orchestrators: accept reporter to decouple presentation from logic

### Fixed

- Output quality: prevent unrendered Jinja2 markers from leaking into HTML when `preprocess: false` by escaping `{{ }}` and `{% %}` appropriately; hardened Mistune path to restore placeholders as entities
- Incremental cache: ensure config file hash recorded after full build to fix false positives and cache hit regressions in incremental sequences

- core(orchestration): Postprocess error reporting uses reporter/quiet-aware CLI; fixed out-of-scope var in parallel path
- core(orchestration): Streaming render respects quiet mode (no direct prints without reporter)
- tests: Added coverage for postprocess reporter errors and streaming quiet behavior
- chore: Lint cleanups in build orchestrator

- **CLI Graph Commands**: Modularized graph analysis commands into separate files
  - Split `cli/commands/graph.py` (1,050 lines) into 5 focused files (~200 lines each)
  - Commands now in `cli/commands/graph/`: `analyze.py`, `pagerank.py`, `communities.py`, `bridges.py`, `suggest.py`
  - Improved navigability and maintainability

- **Markdown Parsers**: Modularized parser implementations
  - Split `rendering/parser.py` (826 lines) into 4 focused modules in `rendering/parsers/`
  - Removed backward-compatibility shim (zero tech debt)
  - **BREAKING**: Import path changed from `bengal.rendering.parser` to `bengal.rendering.parsers`
  - Each parser implementation now in separate file: `base.py`, `python_markdown.py`, `mistune.py`

- **Pygments Patch Cleanup**: Refactored monkey patch to clean, testable implementation
  - Extracted inline patch to dedicated `PygmentsPatch` class with context manager support
  - Added comprehensive test suite (22 tests, all passing)
  - No performance change - retains 3× speedup on code highlighting
  - Improved maintainability and explicit scope documentation

## [0.1.2] - 2025-10-13

### Critical Bug Fixes, Cache Improvements, Navigation Enhancements & Test Quality

This release resolves critical bugs affecting build cache storage, page creation, URL generation, page navigation, and CLI templates. Major improvements include cache persistence through clean operations, better CLI UX, and significantly enhanced test suite quality.

#### 🔥 Critical Fixes

**Build Cache Location (BREAKING - Auto-migrated)**
- **FIXED**: Build cache now stored in `.bengal/` directory instead of `public/`
  - Old location: `public/.bengal-cache.json` (deleted by `bengal site clean`)
  - New location: `.bengal/cache.json` (persists through clean)
  - **Automatic migration**: Old cache copied to new location on first build
  - **Impact**: Incremental builds survive clean operations, CI/CD can cache `.bengal/` directory
  - Add `.bengal/` to your `.gitignore`

**Page Name Slugification**
- **FIXED**: Page names automatically slugified when created
  - Before: `bengal new page "My Page"` → `My Page.md` (spaces in filename ❌)
  - After: `bengal new page "My Page"` → `my-page.md` (clean URLs ✅)
  - Title field preserves original formatting for display
  - **Impact**: Clean URLs without spaces or special characters

**Enhanced Clean Command**
- **NEW**: `bengal site clean` now has multiple modes for different use cases
  - Default: Clean output only (preserves cache for fast rebuilds)
  - `--cache`: Clean output + cache (for cold build testing)
  - `--all`: Same as --cache (convenience alias)
  - Improved messaging shows what will be deleted
  - Different confirmation prompts based on mode
  - **Impact**: Users can test cold builds with `bengal site clean --cache`

#### 🐛 Bug Fixes

**CLI Template Structure (Docs Quickstart)**
- Fixed `bengal new site` docs template using incorrect file structure
  - Changed `index.md` → `_index.md` for section indexes
  - Fixed outdated frontmatter (`layout:`, `section:`, `order:`)
  - Added proper `cascade: type: doc` declarations for consistent layouts
  - Updated to use `weight:` for ordering instead of deprecated `order:`
  - Fixed internal links to use proper trailing slashes
- **Impact**: New documentation sites now work correctly without manual fixes

**URL Generation & Path Resolution**
- Fixed critical bug where child pages generated incorrect URLs
  - Example: `reference/reference-page-1.md` generated `/reference-page-1/` instead of `/reference/reference-page-1/`
  - Root cause: `page.output_path` was `None` during discovery, causing `page.url` to fall back to slug-only URLs
  - Solution: Added `ContentOrchestrator._set_output_paths()` to compute paths immediately after discovery
  - Also affected the showcase example (was broken, but appeared to work)
- **Impact**: All pages now generate correct hierarchical URLs based on file structure

**Sequential Navigation (Next/Previous)**
- Fixed `next_in_section` and `prev_in_section` not respecting `weight` metadata
  - Now uses `section.sorted_pages` which sorts by weight (ascending), then title (alphabetically)
  - Explicitly skips index pages (`_index.md`, `index.md`) in navigation chains
  - Navigation stays within section boundaries (no cross-section jumps)
- Updated `page_navigation` template macro to intelligently select navigation mode:
  - **Section-scoped navigation** for: `doc`, `tutorial`, `api-reference`, `cli-reference`, `changelog`
  - **Global navigation** for: `blog`, `page`, and other content types
- **Impact**: Documentation navigation is now sequential and intuitive

**Template Syntax**
- Fixed Jinja2 syntax errors in `blog/single.html` template
  - Changed `author')_avatar` → `author_avatar')` (and similar for `_title`, `_bio`, `_links`)
  - Proper metadata field access with underscores instead of concatenation

#### ✨ Enhancements

**Logging & Observability**
- Added debug logging for output path configuration
  - Shows paths set, already set, and total pages
  - Helps debug URL generation issues
- Added info logging for pages without `weight` metadata
  - Educates users about weight-based ordering for docs/tutorials
  - Non-intrusive guidance toward best practices
  - Shows sample pages that could benefit from weights

**Health Checks & Validation**
- New health check: **Weight-Based Navigation Validator**
  - Verifies `next_in_section`/`prev_in_section` respect weight order
  - Checks navigation stays within section boundaries
  - Detects cross-section navigation bugs
- New health check: **Output Path Completeness**
  - Ensures all pages have `output_path` set (critical for URLs)
  - Catches URL generation regressions early
- **Impact**: Automated verification prevents future regressions

**Test Coverage**
- Added 5 comprehensive test files (500+ new tests):
  - `test_content_orchestrator_url_fix.py` - URL generation regression tests
  - `test_content_type_urls.py` - Content type-specific URL patterns
  - `test_template_url_access.py` - Template context URL access patterns
  - `test_section_archive_urls.py` - Auto-generated archive URLs
  - `test_full_site_url_consistency.py` - End-to-end URL integration tests
- Covers cascade application, section hierarchies, pagination, and edge cases
- **Impact**: High confidence in URL and navigation correctness

#### 📚 Documentation

**Enhanced Docstrings**
- Improved `PageNavigationMixin.next_in_section` and `prev_in_section`
  - Explains weight-based ordering behavior
  - Documents index page skipping
  - Provides template usage examples
- Enhanced `ContentOrchestrator._set_output_paths`
  - Explains timing and dependencies
  - Documents critical role in URL generation
- Updated `Section.sorted_pages` with ordering details

#### 🧪 Test Quality Improvements

**Pytest Optimization & Parametrization**
- **Parallel execution enabled**: Tests run with `pytest-xdist` (`-n auto`)
- **Timeout protection**: 300s timeout prevents hanging tests (`pytest-timeout`)
- **Better fixture scoping**: Session/class-scoped fixtures for 30-40% faster runs
- **Parametrized tests**: 6 test files refactored, 2.6x better test visibility
  - Before: 25 opaque loop-based tests
  - After: 66 visible parametrized test cases
  - Examples: `test_slugify_transformations[cpp_programming]`, `test_content_type_detection_by_name[api-docs]`
- **80% faster debugging**: Instant identification of failing cases
- **Better reporting**: `--durations=20` shows slowest tests
- **Bug fixes**: Parametrization exposed 3 content type detection bugs (fixed)
- **Cleaner fixtures**: Migrated from `TemporaryDirectory` to `tmp_path`

**Property-Based Testing with Hypothesis (NEW!)**
- **Added comprehensive property-based testing** across all critical utility modules
- **115 property tests** generating **11,600+ examples per run** (vs ~150 manual examples)
- **4 bugs discovered and fixed** including critical production issues
- New test files (3,012 lines of property test code):
  - `test_url_strategy_properties.py` (14 tests): URL generation invariants
  - `test_paths_properties.py` (19 tests): Path handling properties  
  - `test_text_properties.py` (25 tests): Text utility properties
  - `test_pagination_properties.py` (16 tests): Pagination logic
  - `test_dates_properties.py` (23 tests): Date parsing/formatting
  - `test_slugify_properties.py` (18 tests): Slugification properties
- **Critical bugs found**:
  - `truncate_chars(text, 3)` produced 6-char output (suffix overflow bug) - **FIXED**
  - Unicode slug handling clarified as intentional internationalization feature
  - Single underscore and empty input edge cases - **FIXED**
- Properties tested include:
  - URLs always start with `/`, never have `//`, end with `/` for pretty URLs
  - Truncation never exceeds specified length (accounting for suffix)
  - Date parsing roundtrips correctly (datetime → string → datetime)
  - Slugification is idempotent (slug(slug(x)) == slug(x))
  - Pagination distributes all items without duplication
  - Path utilities always create directories, use `.bengal` prefix
- **Dependencies added**: `hypothesis>=6.92.0`
- Run with: `pytest tests/unit -m hypothesis`

Run specific test cases: `pytest -k "cpp_programming"` or `pytest -k "api"`

## [0.1.1] - 2025-10-13

**Fix**: Onboarding templates to initialize a project were missing from the initial release bulid. These have now been added. This enables you to quickstart with example pages.

## [0.1.0] - 2025-10-13

### Initial Alpha Release

Bengal 0.1.0 is an alpha release of a high-performance static site generator optimized for Python 3.14+.

#### Core Features

**Build System**
- Parallel processing with ThreadPoolExecutor for fast builds
- Incremental builds with dependency tracking (15-50x speedup)
- Streaming builds for memory efficiency on large sites
- Smart caching with automatic invalidation
- Build profiles: writer, theme-dev, developer

**Content & Organization**
- Markdown content with YAML/TOML front matter
- Hierarchical sections with automatic navigation
- Taxonomy system (tags, categories)
- Related posts with tag-based similarity
- Menu system with nested navigation
- Breadcrumb generation

**Templates & Rendering**
- Jinja2 template engine with custom filters and tests
- Template caching and reuse
- Theme system with swizzling support
- Partial templates and components
- Syntax highlighting with Pygments (cached)

**API Documentation**
- AST-based Python documentation generation (no imports)
- Support for Google, NumPy, and Sphinx docstring formats
- Automatic cross-reference resolution
- Configurable visibility (private, special methods)

**Assets & Optimization**
- Asset fingerprinting for cache busting
- CSS and JavaScript minification
- Image optimization
- Parallel asset processing
- Optional Node.js pipeline (SCSS, PostCSS, esbuild)

**SEO & Discovery**
- Automatic sitemap.xml generation
- RSS feed generation
- JSON search index
- LLM-friendly text output formats
- Meta tag optimization

**Developer Experience**
- CLI scaffolding (`bengal new site`, `bengal new page`)
- Development server with hot reload
- File watching with automatic rebuilds
- Rich console output with progress tracking
- Health validation system
- Performance profiling tools

#### Requirements

- **Python 3.14+** (3.14t recommended for 1.8x speedup with free-threading)
- See `pyproject.toml` for dependencies

---
## Project Status

**v0.1.0 is an alpha release** suitable for:
- ✅ Early adopters and experimenters
- ✅ Documentation sites (100-5,000 pages)
- ✅ Blogs and content sites
- ✅ Projects needing AST-based API docs
- ✅ Python 3.14+ projects

**Not yet recommended for:**
- ❌ Mission-critical production without testing

---
## Links

- [Documentation](https://github.com/lbliii/bengal)
- [Issue Tracker](https://github.com/lbliii/bengal/issues)
- [Contributing Guide](CONTRIBUTING.md)
- [Getting Started](GETTING_STARTED.md)
