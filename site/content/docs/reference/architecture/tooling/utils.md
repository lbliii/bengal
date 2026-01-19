---
title: Utilities
description: Utility modules for common operations
weight: 40
category: tooling
tags:
- tooling
- utils
- utilities
- text
- file-io
- dates
- pagination
- helpers
keywords:
- utilities
- utils
- text processing
- file I/O
- dates
- pagination
- helpers
- consolidation
---

Utility modules shared across subsystems. The utils package is organized into focused subpackages:

```
bengal/utils/
├── primitives/      # Pure functions with no Bengal imports
│   ├── hashing.py        # SHA256 hashing for cache keys
│   ├── text.py           # Text processing (slugify, truncate)
│   ├── dates.py          # Date parsing and formatting
│   ├── sentinel.py       # MISSING singleton
│   ├── dotdict.py        # Dict with dot notation access
│   └── lru_cache.py      # Thread-safe LRU cache
├── io/              # File I/O utilities
│   ├── file_io.py        # Read/write with error handling
│   ├── atomic_write.py   # Crash-safe file writes
│   └── json_compat.py    # JSON compatibility utilities
├── paths/           # Path management
│   ├── paths.py          # BengalPaths utility
│   ├── url_normalization.py
│   └── url_strategy.py   # URL generation strategies
├── concurrency/     # Thread/async utilities
│   ├── concurrent_locks.py
│   ├── thread_local.py
│   └── workers.py        # Thread pool management
├── observability/   # Logging and metrics
│   ├── logger.py         # Structured logging
│   ├── progress.py       # Progress reporting
│   └── performance_*.py  # Performance tracking
└── pagination/      # Collection pagination
    └── paginator.py      # Generic paginator
```

## Text Utilities (`bengal/utils/primitives/text.py`)
- **Purpose**: Text processing and manipulation
- **Functions**:
  - `slugify()` - URL-safe slug generation with configurable separators
  - `strip_html()` - Remove HTML tags and decode entities
  - `truncate_words()` - Intelligent word-based truncation
  - `truncate_chars()` - Character-based truncation with suffix
  - `truncate_middle()` - Ellipsis in the middle (for long paths)
  - `generate_excerpt()` - Create previews from content
  - `normalize_whitespace()` - Collapse and normalize spaces
  - `escape_html()` - Escape HTML special characters
  - `unescape_html()` - Unescape HTML entities
  - `pluralize()` - Simple pluralization (with custom forms)
  - `humanize_bytes()` - Format bytes as KB/MB/GB
  - `humanize_number()` - Format numbers with thousand separators
- **Usage**: Used by template functions, parser, and throughout rendering pipeline

## File I/O Utilities (`bengal/utils/io/file_io.py`)
- **Purpose**: Robust file reading/writing with consistent error handling
- **Functions**:
  - `read_text_file()` - Read text with UTF-8/latin-1 fallback
  - `load_json()` - Load JSON with validation
  - `load_yaml()` - Load YAML with graceful PyYAML detection
  - `load_toml()` - Load TOML with validation
  - `load_data_file()` - Smart loader (auto-detects JSON/YAML/TOML)
  - `write_text_file()` - Atomic writes with temp file pattern
  - `write_json()` - Atomic JSON writes with formatting
- **Features**:
  - Encoding fallback (UTF-8 → latin-1)
  - Multiple error handling strategies (raise, return_empty, return_none)
  - Structured logging with context
  - Atomic writes for data integrity
- **Usage**: Used by config loader, content discovery, template functions

## Date Utilities (`bengal/utils/primitives/dates.py`)
- **Purpose**: Date parsing, formatting, and manipulation
- **Functions**:
  - `parse_date()` - Unified date parsing (datetime, date, str, None)
  - `format_date_iso()` - Format as ISO 8601
  - `format_date_rfc822()` - Format as RFC 822 (RSS feeds)
  - `format_date_human()` - Custom strftime formatting
  - `time_ago()` - Human-readable "2 days ago" format
  - `get_current_year()` - Current year (for copyright)
  - `is_recent()` - Check if date is within N days
  - `date_range_overlap()` - Check if ranges overlap
- **Features**:
  - Flexible date parsing (many formats with fallback chain)
  - Timezone-aware operations
  - Multiple error handling strategies
  - Type-safe with DateLike type alias
- **Usage**: Used by template functions, frontmatter parsing, RSS generation

## Paginator (`bengal/utils/pagination/paginator.py`)
- **Purpose**: Generic pagination utility for splitting long lists
- **Features**:
  - Configurable items per page
  - Page range calculation (smart ellipsis)
  - Template context generation
  - Type-safe generic implementation
- **Usage**: Used for archive pages and tag pages
- **Import**: `from bengal.utils.pagination import Paginator`

## LRU Cache (`bengal/utils/primitives/lru_cache.py`)
- **Purpose**: Thread-safe LRU cache with optional TTL
- **Features**:
  - Generic type parameters for type safety
  - Statistics tracking (hits, misses, hit rate)
  - Enable/disable without clearing
  - `get_or_set()` pattern for cache population
- **Usage**: Template caching, directive caching, navigation scaffolds
- **Import**: `from bengal.utils.primitives import LRUCache`

## Build Utilities

### BuildContext (`bengal/orchestration/build_context.py`)
- **Purpose**: Shared context passed across build phases (build-scoped state + caches)
- **Contains**: site, stats, cache/tracker, pages_to_build/assets_to_process, reporter, output_collector
- **Usage**: Created by `BuildOrchestrator` and threaded through rendering + postprocess
- **Benefits**: No globals, explicit dependencies, build-scoped caching to avoid cross-build leaks

### BuildStats (`bengal/orchestration/stats/`)
- **Purpose**: Collect and report build statistics
- **Tracks**: Phase timings, pages built, assets processed, errors, health summary
- **Usage**: Returned by `BuildOrchestrator.build()` and used in CLI output

### Build Summary (`bengal/orchestration/summary.py`)
- **Purpose**: Summarize build outcomes for display (including incremental decisions)
- **Usage**: CLI/dashboard output and developer diagnostics

### ProgressReporter (`bengal/protocols` + `bengal/utils/observability/progress.py`)
- **Purpose**: Protocol + adapters for progress output
- **Canonical protocol**: `bengal.protocols.ProgressReporter`
- **Implementations/adapters**: `bengal.utils.observability.progress`

### Live Progress (`bengal/utils/observability/cli_progress.py`)
- **Purpose**: Rich-based live progress display helpers (used when enabled)
- **Usage**: CLI build commands / dashboard integrations

## Path Utilities (`bengal/utils/paths/paths.py`)

### BengalPaths
- **Purpose**: Consistent path management for generated files
- **Canonical implementation**: `bengal/cache/paths.py` (this module re-exports `BengalPaths`)
- **Key paths**:
  - `state_dir` (`.bengal/`)
  - `build_cache` (`.bengal/cache.json` → typically written as `.json.zst`)
  - `page_cache`, `asset_cache`, `taxonomy_cache`
  - `logs_dir`, `build_log`, `serve_log`
  - `metrics_dir`, `profiles_dir`, `templates_dir`, `generated_dir`

## Frontmatter & Metadata
- **Frontmatter parsing**: `bengal/core/page/frontmatter.py`
- **Page metadata helpers**: `bengal/core/page/metadata.py`

## Section Utilities
- **Section model + hierarchy/navigation/queries**: `bengal/core/section/`
- **Fast lookups (registry)**: `bengal/core/registry.py` and `bengal/core/site/section_registry.py`

## File Utilities
- **Robust reads/writes**: `bengal/utils/io/file_io.py`
- **Atomic writes**: `bengal/utils/io/atomic_write.py`

## Atomic Write (`bengal/utils/io/atomic_write.py`)
- **Purpose**: Atomic file writes for data integrity
- **Pattern**: Write to temp file → atomic rename
- **Usage**: Cache persistence, output file writing
- **Benefits**: No partial writes, crash-safe

## URL Strategy (`bengal/utils/paths/url_strategy.py`)
- **Purpose**: URL generation strategies
- **Strategies**: Pretty URLs, flat URLs, date-based URLs
- **Usage**: Content type system, page URL generation

## Theme Utilities

### Theme registry/resolution (`bengal/core/theme/`)
- **Registry**: `bengal/core/theme/registry.py`
- **Resolution**: `bengal/core/theme/resolution.py`

## Error Handling

### Errors (`bengal/errors/`)
- **Purpose**: Centralized error codes + rich error context for build/render/config issues

## CLI Utilities

### CLIOutput (`bengal/output/`)
- **Purpose**: Centralized, profile-aware CLI output helpers
- **Core class**: `bengal/output/core.py`
- **Global helpers**: `bengal/output/globals.py`

### RichConsole (`bengal/utils/observability/rich_console.py`)
- **Purpose**: Shared Rich console configuration for CLI output and progress

### Logger (`bengal/utils/observability/logger.py`)
- **Purpose**: Structured logging for Bengal
- **Features**: Levels, formatting, file output
- **Usage**: Throughout build pipeline

## Performance Utilities

### PerformanceCollector (`bengal/utils/observability/performance_collector.py`)
- **Purpose**: Collect performance metrics during build
- **Tracks**: Phase timings, memory usage, bottlenecks
- **Usage**: Performance profiling commands

### PerformanceReport (`bengal/utils/observability/performance_report.py`)
- **Purpose**: Format performance metrics for display
- **Features**: Flamegraphs, timing tables, bottleneck detection
- **Usage**: CLI perf command

### Profile (`bengal/utils/observability/profile.py`)
- **Purpose**: cProfile wrapper with context manager
- **Usage**: Performance profiling with --perf-profile flag

## Page Utilities

### Page creation (`bengal/content/discovery/page_factory.py`)
- **Purpose**: Create `Page` objects during content discovery
- **Usage**: Discovery pipeline

### DotDict (`bengal/utils/primitives/dotdict.py`)
- **Purpose**: Dict with dot notation access
- **Example**: `config.build.parallel` instead of `config['build']['parallel']`
- **Usage**: Configuration, template context

## Design Principles

1. **Single Responsibility**: Each utility module has one clear purpose
2. **No Business Logic**: Utilities are reusable helpers, not business logic
3. **Type Safety**: Full type hints throughout
4. **Error Handling**: Consistent error handling patterns
5. **Testing**: Covered by unit and integration tests
6. **Documentation**: Docstrings and examples for all utilities

## Related Documentation

- [Design Principles](../design-principles.md) - Overall design patterns
- [File Organization](../meta/file-organization.md) - Directory structure
- [Testing](../meta/testing.md) - Testing strategy
