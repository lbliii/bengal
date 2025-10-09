# Changelog

All notable changes to Bengal SSG will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **📄 Template System Improvements** - Clarified template behavior and enhanced UX
  - **Index File Collision Detection:**
    - Detects when both `index.md` and `_index.md` exist in same section
    - Prefers `_index.md` over `index.md` (Hugo convention)
    - Logs helpful warning with suggestion to remove one
  - **Archive vs List Separation:**
    - `archive.html` now specifically for chronological/blog content
    - `index.html` as generic fallback for non-chronological sections
    - Smart content type detection with date-based heuristics
    - New content types: `archive`, `list`, `api-reference`, `cli-reference`, `tutorial`
  - **Enhanced Empty States:**
    - Helpful guidance with specific file paths
    - Different messages for archives vs generic sections
    - Instructions for adding content and subsections
  - **Comprehensive Documentation:**
    - New `TEMPLATES.md` guide covering:
      - Template selection priority
      - Index file semantics
      - Auto-generation behavior
      - Content type detection rules
      - Customization options
      - Common patterns and troubleshooting
  - **Test Coverage:**
    - 6 tests for index collision detection
    - 21 tests for content type detection and template selection
  - **Files Modified:**
    - `bengal/core/section.py` - Collision detection in `add_page()`
    - `bengal/orchestration/section.py` - Enhanced content type detection
    - `bengal/themes/default/templates/index.html` - Complete rewrite with better UX
    - `bengal/themes/default/templates/archive.html` - Enhanced documentation
  - **Benefits:**
    - Better organized content with appropriate templates
    - Clear warnings prevent configuration mistakes
    - Smart defaults reduce manual configuration
    - Helpful empty states guide writers

- **💡 Link Suggestions** - Smart cross-linking recommendations
  - Multi-signal scoring: tags, categories, PageRank, betweenness, link gaps
  - Prioritizes underlinked valuable content for better discoverability
  - **CLI Command:** `bengal suggest` with multiple output formats
    - Table format: Quick overview of top suggestions
    - JSON format: Export for programmatic processing
    - Markdown format: Implementation checklist with action items
  - **Integrated with KnowledgeGraph:**
    - `suggest_links()` - Generate smart link suggestions
    - `get_suggestions_for_page()` - Get suggestions for specific page
    - Results cached automatically for performance
  - **Scoring factors** (configurable weights):
    - Topic similarity (40%): Shared tags between pages
    - Category match (30%): Same category/section
    - PageRank (20%): Link to important pages
    - Betweenness (10%): Link to bridge pages
    - Underlink bonus: Boost orphaned/underlinked content
  - New modules:
    - `bengal/analysis/link_suggestions.py` - Smart link engine (330 LOC, 95% coverage)
    - Integrated in `bengal/analysis/knowledge_graph.py`
    - CLI command in `bengal/cli.py`
  - Comprehensive test coverage: 15 unit tests
  - Use cases:
    - Improve internal linking structure
    - Boost SEO through better site connectivity
    - Increase content discoverability
    - Identify and fill navigation gaps

- **🌉 Path Analysis** - Identify bridge pages and navigation bottlenecks
  - Implements Brandes' algorithm for betweenness centrality
  - Computes closeness centrality for accessibility analysis
  - Finds shortest paths between pages using BFS
  - **CLI Command:** `bengal bridges` with flexible metric selection
    - Table format: Shows top N bridge/accessible pages
    - JSON format: Export for programmatic analysis
    - Summary format: Detailed view with centrality scores
  - **Integrated with KnowledgeGraph:**
    - `analyze_paths()` - Compute path metrics with caching
    - `get_betweenness_centrality()` - Bridge page scores
    - `get_closeness_centrality()` - Accessibility scores
    - `find_shortest_path()` - Path finding between pages
  - **Network metrics:**
    - Betweenness: Identifies pages that connect different parts of the site
    - Closeness: Measures how easily pages can be reached
    - Network diameter: Longest shortest path
    - Average path length: Mean distance between pages
  - New modules:
    - `bengal/analysis/path_analysis.py` - Path analyzer (143 LOC, 98% coverage)
    - Integrated in `bengal/analysis/knowledge_graph.py`
    - CLI command in `bengal/cli.py`
  - Comprehensive test coverage: 16 unit + 12 integration tests
  - Use cases:
    - Optimize navigation structure
    - Identify critical bridge pages
    - Improve content discoverability
    - Find navigation bottlenecks

- **🔍 Community Detection** - Discover topical clusters in content
  - Implements Louvain algorithm for modularity optimization
  - Automatically finds natural groupings of related pages
  - **CLI Command:** `bengal communities` with multiple output formats
    - Table format: Shows top N communities with representative pages
    - JSON format: Export for programmatic analysis
    - Summary format: Detailed view with top pages per community
  - **Integrated with KnowledgeGraph:**
    - `detect_communities()` - Find topical clusters
    - `get_community_for_page()` - Lookup page's community
    - Results cached automatically for performance
  - **Configurable parameters:**
    - Resolution: Control community granularity (default 1.0)
    - Random seed: Reproducible results for testing
    - Minimum size: Filter out small communities
  - New modules:
    - `bengal/analysis/community_detection.py` - Louvain detector (143 LOC, 89% coverage)
    - Integrated in `bengal/analysis/knowledge_graph.py`
    - CLI command in `bengal/cli.py`
  - Comprehensive test coverage: 16 unit + 10 integration tests
  - Use cases:
    - Discover hidden content structure automatically
    - Organize content into logical topic groups
    - Guide taxonomy and navigation design
    - Identify content gaps and opportunities

- **🏆 PageRank Analysis** - Data-driven page importance scoring
  - Identifies most important content using Google's PageRank algorithm
  - Iterative power method with configurable damping factor (default 0.85)
  - Converges in typically 10-50 iterations for sites of any size
  - **Personalized PageRank:** Find content related to specific topics
  - **CLI Command:** `bengal pagerank` with multiple output formats
    - Table format: Top N pages with scores and link counts
    - JSON format: Export for programmatic analysis
    - Summary format: Quick overview with insights
  - **Integrated with KnowledgeGraph:**
    - `compute_pagerank()` - Standard PageRank computation
    - `compute_personalized_pagerank()` - Topic-specific scoring
    - `get_top_pages_by_pagerank()` - Convenience method
    - Results cached automatically for performance
  - New modules:
    - `bengal/analysis/page_rank.py` - PageRank calculator (81 LOC, 88% coverage)
    - Integrated in `bengal/analysis/knowledge_graph.py`
    - CLI command in `bengal/cli.py`
  - Comprehensive test coverage: 17 unit + 11 integration tests
  - Use cases:
    - Prioritize content updates based on importance
    - Guide sitemap and navigation design
    - Identify underlinked valuable content
    - Find hub pages for cross-linking opportunities

### Changed
- **🔧 Hashable Pages and Sections** - Core data structures now support set operations
  - `Page` and `Section` objects are now hashable based on their `source_path` and `path` respectively
  - Enables O(1) membership tests instead of O(n) list lookups
  - **Performance:** Set-based deduplication is 5-10x faster than list operations
  - **Memory:** Knowledge graph uses 33% less memory (eliminated `page_by_id` mapping)
  - **Type Safety:** `Set[Section]` instead of `Set[Any]` in incremental builds
  - Refactored modules:
    - `bengal/core/page/__init__.py` - Added `__hash__` and `__eq__` methods
    - `bengal/core/section.py` - Added `__hash__` and `__eq__` methods
    - `bengal/orchestration/build.py` - Set-based page deduplication
    - `bengal/orchestration/incremental.py` - Type-safe section tracking
    - `bengal/orchestration/related_posts.py` - Direct page keys (no ID mapping)
    - `bengal/analysis/knowledge_graph.py` - Direct page references (-33% memory)
  - Comprehensive test coverage: 42 unit + 8 integration tests
  - **Backward Compatible:** All APIs still use `List[Page]`, sets used internally

## [0.3.0] - 2025-10-04

### Added
- 🚀 **Autodoc System** - Game-changing API documentation generation
  - AST-based Python source code extraction (no imports needed!)
  - **175+ pages/sec** performance (10-100x faster than Sphinx)
  - Rich docstring parsing: Google, NumPy, and Sphinx formats
  - Extracts: args, returns, raises, examples, type hints, deprecations
  - Config-driven workflow via `bengal.toml`
  - New CLI command: `bengal autodoc`
  - Two-layer template system: `.md.jinja2` → `.html`
  - Fully customizable templates
  - Safe: zero code execution, works with any dependencies
  - Extensible: unified `DocElement` model ready for OpenAPI, CLI extractors
  - New modules:
    - `bengal/autodoc/base.py` - Core data models
    - `bengal/autodoc/generator.py` - Documentation generator
    - `bengal/autodoc/extractors/python.py` - Python AST extractor
    - `bengal/autodoc/docstring_parser.py` - Multi-style docstring parser
    - `bengal/autodoc/config.py` - Configuration loader
    - `bengal/autodoc/templates/python/module.md.jinja2` - Default template
  - Example: Showcase site now includes full Bengal API documentation (99 modules)

- **Atomic writes for all file operations** - Critical reliability improvement
  - All file writes now use write-to-temp-then-rename pattern
  - Prevents data corruption during unexpected build interruptions (Ctrl+C, power loss, etc.)
  - Applies to: pages, assets, sitemap, RSS, cache, all output formats
  - Zero performance impact (rename is essentially free)
  - New utility module: `bengal.utils.atomic_write`

### Changed
- File write operations now crash-safe across entire codebase

### Technical
- Added `atomic_write_text()` function for simple text writes
- Added `atomic_write_bytes()` function for binary writes
- Added `AtomicFile` context manager for incremental writes (JSON, XML)
- Updated 7 production files, protecting 13 write sites
- Added comprehensive test suite (20 test cases)

### Added
- **Comprehensive resource cleanup system** - Dev server now properly cleans up resources in ALL termination scenarios
  - New `ResourceManager` class for centralized lifecycle management with signal handlers, atexit, and context manager support
  - New `PIDManager` class for process tracking and stale process detection
  - New `bengal cleanup` CLI command for manually cleaning up stale server processes
  - Automatic stale process detection on server startup with user-friendly recovery prompts
  - Proper cleanup on SIGTERM, SIGHUP, parent process death, and terminal crashes
  - PID file tracking (`.bengal.pid`) to identify and recover from zombie processes
  - Idempotent cleanup (safe to call multiple times)
  - LIFO resource cleanup order (like context managers)
  - Timeout protection to prevent hanging on cleanup

### Changed
- **Refactored `DevServer` class** to use ResourceManager pattern
  - Separated server creation from starting for better resource management
  - Added proactive stale process checking before server start
  - Improved error messages and user guidance for port conflicts
  - Better separation of concerns (observer creation, server creation, startup messages)

### Fixed
- **Eliminated zombie processes** - Dev server no longer leaves orphaned processes holding ports
- **Port conflicts on restart** - Automatic detection and recovery from stale processes
- **Resource leaks** - All resources (TCP sockets, file system observers, PID files) now properly cleaned up

### Dependencies
- Added `psutil>=5.9.0` for better process management and validation (optional, graceful fallback)

## [0.1.0] - Previous Release

### Added
- Initial release of Bengal SSG
- Core static site generation
- Development server with hot reload
- Parallel build processing
- Template system with Jinja2
- Asset pipeline
- And much more...

[Unreleased]: https://github.com/bengal-ssg/bengal/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/bengal-ssg/bengal/releases/tag/v0.1.0
