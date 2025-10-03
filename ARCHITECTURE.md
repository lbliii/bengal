# Bengal SSG - Architecture Documentation

## Overview

Bengal SSG follows a modular architecture with clear separation of concerns to avoid "God objects" and maintain high performance even with large sites.

## Core Components

### 1. Object Model

#### Site Object (`bengal/core/site.py`)
- **Purpose**: Orchestrates the entire website build process
- **Responsibilities**:
  - Holds configuration and global metadata
  - Manages collections of pages, sections, and assets
  - Coordinates the build process (sequential or parallel)
  - Triggers post-processing tasks
  - Collects taxonomies (tags, categories)
  - Generates dynamic pages (archives, tag pages)
- **Key Methods**:
  - `build()`: Main build orchestration
  - `collect_taxonomies()`: Gather tags/categories from all pages
  - `generate_dynamic_pages()`: Create archive and taxonomy pages
  - `discover_content()`: Find and parse all content files
  - `discover_assets()`: Find all static assets

#### Page Object (`bengal/core/page.py`)
- **Purpose**: Represents a single content page
- **Attributes**:
  - Source path and content
  - Metadata (frontmatter)
  - Parsed AST
  - Rendered HTML
  - Links and tags
  - Output path
  - **Table of Contents** (TOC):
    - `toc`: HTML table of contents
    - `toc_items`: Structured TOC data (list of dicts with id, title, level)
- **Properties**:
  - `title`: Get page title from metadata or generate from filename
  - `date`: Get page date from metadata
  - `slug`: Get URL slug for the page
  - `url`: Get the full URL path (e.g., `/posts/my-post/`)
- **Methods**:
  - `render()`: Render page with template
  - `validate_links()`: Check for broken links
  - `extract_links()`: Extract all links from content

#### Section Object (`bengal/core/section.py`)
- **Purpose**: Represents a logical grouping of pages (folder structure)
- **Attributes**:
  - Hierarchy information
  - Collection of pages and subsections
  - Inherited metadata
  - Optional index page
- **Methods**:
  - `aggregate_content()`: Collect metadata from all pages
  - `walk()`: Iteratively traverse section hierarchy
  - `apply_section_template()`: Generate section index

#### Asset Object (`bengal/core/asset.py`)
- **Purpose**: Handles static files (images, CSS, JS)
- **Methods**:
  - `minify()`: Minify CSS/JS
  - `optimize()`: Optimize images
  - `hash()`: Generate fingerprint for cache busting
  - `copy_to_output()`: Copy to output directory

### 2. Cache System (NEW)

Bengal implements an intelligent caching system for incremental builds, providing 18-42x faster rebuilds.

#### Build Cache (`bengal/cache/build_cache.py`)
- **Purpose**: Tracks file changes between builds to enable incremental rebuilds
- **Features**:
  - SHA256 file hashing for change detection
  - Dependency graph tracking
  - Taxonomy dependency tracking
  - JSON-based persistence (`.bengal-cache.json`)
- **Key Methods**:
  - `is_changed(path)`: Check if file has changed since last build
  - `add_dependency(source, dependency)`: Record file dependencies
  - `get_affected_pages(changed_file)`: Find pages that need rebuilding
  - `save()` / `load()`: Persist cache between builds

#### Dependency Tracker (`bengal/cache/dependency_tracker.py`)
- **Purpose**: Tracks dependencies during the build process
- **Tracks**:
  - Page → template dependencies
  - Page → partial dependencies
  - Page → config dependencies
  - Taxonomy (tag) → page relationships
- **Usage**: Integrated with rendering pipeline to build dependency graph

#### Incremental Build Flow
```
1. Load cache from disk
2. Check config file (if changed → full rebuild)
3. Compare file hashes to detect changes
4. Track template dependencies during rendering
5. Find affected pages via dependency graph
6. Rebuild only changed/affected pages
7. Process only changed assets
8. Update cache with new hashes
9. Save cache for next build
```

**Key Features:**
- ✅ Template dependency tracking (pages → templates/partials)
- ✅ Taxonomy dependency tracking (tags → pages)
- ✅ Config change detection (forces full rebuild)
- ✅ Verbose mode (`--verbose` flag shows what changed)
- ✅ Asset change detection (selective processing)

**Performance Impact:**
- Small sites (10 pages): 18x faster (0.223s → 0.012s)
- Medium sites (50 pages): 42x faster (0.839s → 0.020s)
- Large sites (100 pages): 36x faster (1.688s → 0.047s)
- Expected for very large sites (1000+ pages): 100x+ faster

**CLI Usage:**
```bash
# Incremental build
bengal build --incremental

# With detailed change information
bengal build --incremental --verbose
```

### 3. Rendering Pipeline

The rendering pipeline is divided into clear stages:

```
Parse → Build AST → Apply Templates → Render Output → Post-process
```

#### Parser (`bengal/rendering/parser.py`)
- Converts Markdown (or other formats) to HTML
- Extracts table of contents (TOC) from headings
- TOC automatically exposed to templates via `page.toc`
- Supports extensions (code highlighting, tables, etc.)

#### Template Engine (`bengal/rendering/template_engine.py`)
- Jinja2-based templating
- Supports nested templates and partials
- Custom filters and global functions
- Multiple template directories (custom, theme, default)
- Template dependency tracking for incremental builds
- Tracks includes, extends, and imports automatically

#### Renderer (`bengal/rendering/renderer.py`)
- Applies templates to pages
- Determines which template to use based on page metadata
- Fallback rendering for error cases

#### Pipeline Coordinator (`bengal/rendering/pipeline.py`)
- Orchestrates all stages for each page
- Handles output path determination
- Writes final output to disk
- Integrates with DependencyTracker for incremental builds
- Tracks template usage during rendering

### 4. Discovery System

#### Content Discovery (`bengal/discovery/content_discovery.py`)
- Walks content directory recursively
- Creates Page and Section objects
- Parses frontmatter
- Organizes content into hierarchy

#### Asset Discovery (`bengal/discovery/asset_discovery.py`)
- Finds all static assets
- Preserves directory structure
- Creates Asset objects with metadata

### 5. Configuration System

#### Config Loader (`bengal/config/loader.py`)
- Supports TOML and YAML formats
- Auto-detects config files
- Provides sensible defaults
- Flattens nested configuration for easy access

### 6. Post-Processing

#### Sitemap Generator (`bengal/postprocess/sitemap.py`)
- Generates XML sitemap for SEO
- Includes all pages with metadata
- Configurable priority and change frequency

#### RSS Generator (`bengal/postprocess/rss.py`)
- Generates RSS feed
- Includes recent posts
- Supports custom descriptions

#### Link Validator (`bengal/rendering/link_validator.py`)
- Validates internal and external links
- Reports broken links
- Can be extended for comprehensive validation

### 7. Development Server

#### Dev Server (`bengal/server/dev_server.py`)
- Built-in HTTP server
- File system watching with watchdog
- Automatic rebuild on changes
- Hot reload support (future enhancement)

### 8. CLI (`bengal/cli.py`)
- Click-based command-line interface
- Commands:
  - `bengal build`: Build the site
  - `bengal build --incremental`: Incremental build (only changed files)
  - `bengal build --parallel`: Parallel build (default)
  - `bengal serve`: Start dev server
  - `bengal clean`: Clean output
  - `bengal new site/page`: Create new content
  - `bengal --version`: Show version

### 9. Utilities (`bengal/utils/`)

#### Paginator (`bengal/utils/pagination.py`)
- **Purpose**: Generic pagination utility for splitting long lists
- **Features**:
  - Configurable items per page
  - Page range calculation (smart ellipsis)
  - Template context generation
  - Type-safe generic implementation
- **Usage**: Used for archive pages and tag pages

## Design Principles

### 1. Avoiding Stack Overflow
- **Iterative Traversal**: Section hierarchy uses `walk()` method instead of deep recursion
- **Configurable Limits**: Can set max recursion depth if needed
- **Tail Call Patterns**: Where recursion is used, structured for optimization

### 2. Avoiding God Objects
- **Single Responsibility**: Each class has one clear purpose
- **Composition over Inheritance**: Objects compose other objects rather than inheriting
- **Clear Dependencies**: Site → Sections → Pages (one direction)

### 3. Performance Optimization
- **Parallel Processing**: ✅ Fully Implemented!
  - Pages: Rendered in parallel using ThreadPoolExecutor
  - Assets: Processed in parallel for 5+ assets (2-4x speedup)
  - Post-processing: Sitemap, RSS, link validation run concurrently (2x speedup)
  - Smart thresholds avoid thread overhead for tiny workloads
  - Thread-safe error handling and output
  - Configurable via single `parallel` flag (default: true)
  - Configurable worker count (`max_workers`, default: auto-detect)
- **Incremental Builds**: ✅ Fully Implemented!
  - SHA256 file hashing for change detection
  - Dependency graph tracking (pages → templates/partials)
  - Template change detection (rebuilds only affected pages)
  - Granular taxonomy tracking (only rebuilds affected tag pages)
  - Verbose mode for debugging (`--verbose` flag)
  - 18-42x faster for single-file changes (validated)
  - Automatic caching with `.bengal-cache.json`
- **Caching**: Build cache persists between builds
- **Lazy Loading**: Parse content only when needed

### 4. Extensibility
- **Plugin System**: Hooks for pre/post build events (future enhancement)
- **Custom Content Types**: Easy to add new parsers
- **Template Flexibility**: Custom templates override defaults
- **Theme System**: Self-contained themes with templates and assets

## Data Flow

```
Content Files (Markdown)
    ↓
Content Discovery
    ↓
Page Objects
    ↓
Markdown Parser → AST
    ↓
Template Engine
    ↓
Rendered HTML
    ↓
Output Files

Assets
    ↓
Asset Discovery
    ↓
Asset Objects
    ↓
Optimization Pipeline
    ↓
Output Files
```

## Performance Considerations

### Current Optimizations
1. **Parallel Processing**: Pages, assets, and post-processing tasks run concurrently
2. **Incremental Builds**: Only rebuild changed files (50-900x speedup)
3. **Smart Thresholds**: Automatic detection of when parallelism is beneficial
4. **Efficient File I/O**: Thread-safe concurrent file operations
5. **Build Cache**: Persists file hashes and dependencies between builds
6. **Minimal Dependencies**: Only necessary libraries included

### Performance Benchmarks (October 2025)
- **Full Builds**:
  - Small sites (10 pages): 0.29s ✅
  - Medium sites (100 pages): 1.66s ✅
  - Large sites (500 pages): 7.95s ✅
- **Parallel Processing**:
  - 50 assets: 3.01x speedup
  - 100 assets: 4.21x speedup
  - Post-processing: 2.01x speedup
- **Incremental Builds** (validated October 3, 2025):
  - Small sites: 18.3x speedup (0.223s → 0.012s)
  - Medium sites: 41.6x speedup (0.839s → 0.020s)
  - Large sites: 35.6x speedup (1.688s → 0.047s)
- **Combined**: Full builds meet all targets, incremental builds near-instant

### Future Optimizations
1. **Content Caching**: Cache parsed Markdown AST between builds
2. **Asset Deduplication**: Share common assets across pages
3. **Build Profiling**: Identify bottlenecks with detailed timing
4. **Parallel Asset Processing**: Process assets in parallel (planned)

## Extension Points

### 1. Custom Content Types
Implement a new parser in `bengal/rendering/parser.py`:
```python
class ReStructuredTextParser:
    def parse(self, content: str) -> str:
        # Convert RST to HTML
        pass
```

### 2. Custom Post-Processors
Add new generators in `bengal/postprocess/`:
```python
class RobotsGenerator:
    def generate(self, site: Site) -> None:
        # Generate robots.txt
        pass
```

### 3. Build Hooks (Future)
```python
@bengal.hook('pre_build')
def custom_pre_build(site):
    # Custom logic before build
    pass
```

## Testing Strategy

Bengal uses a comprehensive testing approach with pytest and coverage tracking.

### Test Infrastructure

**Location:** `tests/` directory with organized structure:
- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests for workflows
- `tests/e2e/` - End-to-end tests with example sites
- `tests/performance/` - Performance benchmarks
- `tests/fixtures/` - Shared test data
- `tests/conftest.py` - Shared pytest fixtures

**Tools:**
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `pytest-xdist` - Parallel test execution
- `ruff` - Linting
- `mypy` - Type checking

### Coverage Goals

| Component | Target | Status |
|-----------|--------|--------|
| Cache (BuildCache, DependencyTracker) | 95%+ | ✅ 95% (32 tests) |
| Utils (Paginator) | 95%+ | ✅ 96% (10 tests) |
| Parallel Processing (Assets, Post-processing) | 90%+ | ✅ Tested (12 tests) |
| Core (Page, Site, Section) | 90%+ | ⏳ In Progress |
| Rendering Pipeline | 85%+ | ⏳ Planned |
| CLI | 80%+ | ⏳ Planned |
| **Overall Target** | **85%** | 🎯 Goal |

### Test Types

1. **Unit Tests**
   - Test individual components in isolation
   - Fast execution (< 1 second)
   - Mock external dependencies
   - Example: `tests/unit/utils/test_pagination.py` (10 tests, 96% coverage)

2. **Integration Tests**
   - Test component interactions
   - Full build workflows
   - Theme rendering
   - Example: Building a complete site from content

3. **End-to-End Tests**
   - Build example sites
   - Verify output correctness
   - Real-world scenarios

4. **Performance Tests**
   - Build speed benchmarks
   - Memory usage profiling
   - Large site stress tests

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=bengal

# Specific test file
pytest tests/unit/utils/test_pagination.py

# Parallel execution
pytest -n auto

# Generate HTML coverage report
pytest --cov=bengal --cov-report=html
```

### Shared Fixtures

Located in `tests/conftest.py`:
- `tmp_site` - Temporary site directory
- `sample_config` - Sample configuration
- `sample_page` - Sample page with frontmatter
- `site_with_content` - Site with sample content
- `mock_template_engine` - Mocked template engine

### Current Status

- ✅ Test infrastructure complete
- ✅ Pytest configuration
- ✅ Shared fixtures
- ✅ Paginator test suite: 10 tests, 96% coverage
- ✅ Cache test suites: 32 tests, 95% coverage
  - BuildCache: 19 tests, 93% coverage
  - DependencyTracker: 13 tests, 98% coverage
- ✅ Parallel processing test suite: 12 tests
  - Asset processing: 4 tests
  - Post-processing: 3 tests
  - Configuration: 3 tests
  - Thread safety: 2 tests
- ⏳ Core component tests in progress
- ⏳ Integration tests planned

For detailed testing strategy, see `plan/TEST_STRATEGY.md`.

## Recent Additions (Phase 2A & 2B)

### Taxonomy System
- **Automatic Collection**: Tags and categories extracted from all pages
- **Dynamic Pages**: Tag index and individual tag pages auto-generated
- **Organized Data**: Taxonomies stored in structured format for templates

### Dynamic Page Generation
- **Archive Pages**: Automatically created for sections (e.g., `/posts/`)
- **Tag Pages**: Individual pages for each tag (e.g., `/tags/tutorial/`)
- **Tag Index**: Central page listing all tags (`/tags/`)
- **Virtual Pages**: Generated pages behave like real pages in the system

### Pagination System
- **Generic Paginator**: Reusable utility class for any list
- **Automatic Pagination**: Archives and tag pages paginate when > 10 items
- **URL Structure**: Page 1 at base URL, subsequent at `/page/N/`
- **Template Context**: Full pagination data (current, total, next, previous)
- **Configurable**: Per-page count configurable globally or per-section

### Theme Enhancements
- **Breadcrumb Navigation**: Auto-generated from URL structure
- **Table of Contents (TOC)**: ✅ Auto-generated from page headings
  - Sidebar navigation on desktop
  - Sticky positioning for easy access
  - JavaScript highlighting of active section
  - Responsive mobile display
- **404 Page**: Professional error page with helpful navigation
- **Responsive Pagination Controls**: With proper accessibility
- **Template Partials**: Reusable components (article-card, tag-list, pagination)

## Roadmap

**Completed:**
- [x] Core object model
- [x] Rendering pipeline
- [x] CLI basics
- [x] Dev server
- [x] Taxonomy system
- [x] Dynamic page generation
- [x] Pagination system
- [x] Production-ready default theme
- [x] Test infrastructure (pytest, coverage, fixtures)
- [x] Cache test suites (BuildCache, DependencyTracker: 32 tests, 95% coverage)
- [x] **Incremental builds - Complete!** 🎉
  - ✅ File change detection with SHA256 hashing
  - ✅ Dependency graph tracking (pages → templates)
  - ✅ Template dependency tracking during rendering
  - ✅ Granular tag change detection (only rebuilds affected tag pages)
  - ✅ Config change detection (forces full rebuild)
  - ✅ Selective page/asset rebuilding
  - ✅ Verbose mode for change reporting
  - ✅ 18-42x faster rebuilds (validated October 3, 2025)

**Recently Completed:**
- [x] **Table of Contents (TOC)** - Auto-generated from headings! 🎉
- [x] **Parallel asset processing** - 2-4x speedup achieved! 🎉
- [x] **Parallel post-processing** - 2x speedup achieved! 🎉
- [x] **Parallel processing tests** - 12 comprehensive tests
- [x] **Performance benchmarks** - Validated 2-4x speedup claims

**Next Priorities:**
- [ ] Navigation menu system (config-driven, hierarchical)
- [ ] Core component tests (Page, Site, Section) - 90% coverage target
- [ ] Enhanced asset pipeline (robust minification, optimization)
- [ ] Plugin system with hooks
- [ ] Comprehensive documentation site
- [ ] Performance benchmarking vs Hugo/Jekyll

**Future:**
- [ ] Hot reload in browser
- [ ] Build caching
- [ ] Multi-language support
- [ ] Search functionality
- [ ] Content versioning

