# Changelog

All notable changes to Bengal SSG will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Refactoring

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
  - Old location: `public/.bengal-cache.json` (deleted by `bengal clean`)
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
- **NEW**: `bengal clean` now has multiple modes for different use cases
  - Default: Clean output only (preserves cache for fast rebuilds)
  - `--cache`: Clean output + cache (for cold build testing)
  - `--all`: Same as --cache (convenience alias)
  - Improved messaging shows what will be deleted
  - Different confirmation prompts based on mode
  - **Impact**: Users can test cold builds with `bengal clean --cache`

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

Bengal 0.1.0 is an alpha release of a high-performance static site generator optimized for Python 3.13+.

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

- **Python 3.13+** (3.14t recommended for 1.8x speedup)
- See `pyproject.toml` for dependencies

---

## Project Status

**v0.1.0 is an alpha release** suitable for:
- ✅ Early adopters and experimenters
- ✅ Documentation sites (100-5,000 pages)
- ✅ Blogs and content sites
- ✅ Projects needing AST-based API docs
- ✅ Python 3.13+ projects

**Not yet recommended for:**
- ❌ Mission-critical production without testing

---

## Links

- [Documentation](https://github.com/lbliii/bengal)
- [Issue Tracker](https://github.com/lbliii/bengal/issues)
- [Contributing Guide](CONTRIBUTING.md)
- [Getting Started](GETTING_STARTED.md)
