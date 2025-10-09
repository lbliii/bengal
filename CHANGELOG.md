# Changelog

All notable changes to Bengal SSG will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
