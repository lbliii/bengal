---
title: Utilities
description: Comprehensive utility modules for common operations across the codebase.
weight: 40
category: tooling
tags: [tooling, utils, utilities, text, file-io, dates, pagination, helpers]
keywords: [utilities, utils, text processing, file I/O, dates, pagination, helpers, consolidation]
---

Bengal provides a comprehensive set of utility modules that consolidate common operations across the codebase, eliminating duplication and providing consistent, well-tested implementations.

## Text Utilities (`bengal/utils/text.py`)
- **Purpose**: Text processing and manipulation
- **Functions (12 total)**:
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
- **Coverage**: 91% with 74 comprehensive tests

## File I/O Utilities (`bengal/utils/file_io.py`)
- **Purpose**: Robust file reading/writing with consistent error handling
- **Functions (7 total)**:
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
- **Coverage**: 23-91% (increases as adoption grows)

## Date Utilities (`bengal/utils/dates.py`)
- **Purpose**: Date parsing, formatting, and manipulation
- **Functions (8 total)**:
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
- **Coverage**: 91% with 56 comprehensive tests

## Paginator (`bengal/utils/pagination.py`)
- **Purpose**: Generic pagination utility for splitting long lists
- **Features**:
  - Configurable items per page
  - Page range calculation (smart ellipsis)
  - Template context generation
  - Type-safe generic implementation
- **Usage**: Used for archive pages and tag pages
- **Coverage**: 96% with 10 tests

## Impact of Utility Consolidation
- **Code Reduction**: Eliminated 311 lines of duplicate code across 9 files
- **Test Coverage**: Added 184+ comprehensive tests
- **Consistency**: Single source of truth for text, files, and dates
- **Maintainability**: Fix once in utility module vs 4+ places
- **Type Safety**: Full type hints with type aliases
- **Error Handling**: Consistent strategies across all utilities

## Build Utilities

### BuildContext (`bengal/utils/build_context.py`)
- **Purpose**: Dependency injection container for build pipeline
- **Contains**: site, pages, assets, reporter, progress_manager, injected services
- **Usage**: Threaded through orchestrators and rendering
- **Benefits**: No globals, explicit dependencies, testability

### BuildStats (`bengal/utils/build_stats.py`)
- **Purpose**: Collect and report build statistics
- **Tracks**: Build time, pages built, assets processed, errors
- **Usage**: Returned by Site.build(), used in CLI output

### BuildSummary (`bengal/utils/build_summary.py`)
- **Purpose**: Format build statistics for display
- **Formats**: Console output, JSON export
- **Usage**: CLI commands, health reports

### ProgressReporter (`bengal/utils/progress.py`)
- **Purpose**: Protocol for progress output
- **Implementations**: LiveProgressReporterAdapter (Rich), SimpleReporter
- **Usage**: Orchestrators route progress via reporter

### LiveProgress (`bengal/utils/live_progress.py`)
- **Purpose**: Rich-based live progress display
- **Features**: Multiple phases, per-item updates, spinners
- **Usage**: CLI build commands with Rich output

## Path Utilities (`bengal/utils/paths.py`)

### BengalPaths
- **Purpose**: Consistent path management for generated files
- **Methods**:
  - `get_profile_dir()` - Performance profiling directory
  - `get_profile_path()` - Profile file path
  - `get_cache_path()` - Build cache path
  - `get_template_cache_dir()` - Jinja2 bytecode cache
  - `get_build_log_path()` - Build log path
- **Pattern**: Separates source, output, cache, and dev files

## Metadata Utilities (`bengal/utils/metadata.py`)
- **Purpose**: Frontmatter parsing and validation
- **Functions**:
  - Parse YAML/TOML frontmatter
  - Validate required fields
  - Merge cascade metadata
  - Extract metadata from content
- **Usage**: Content discovery, page initialization

## Section Utilities (`bengal/utils/sections.py`)
- **Purpose**: Section hierarchy management
- **Functions**:
  - Build section tree
  - Setup parent/child relationships
  - Calculate section depth
  - Traverse hierarchy
- **Usage**: Content orchestrator, navigation

## File Utilities (`bengal/utils/file_utils.py`)
- **Purpose**: File system operations
- **Functions**:
  - Safe file operations
  - Directory creation
  - File copying with metadata
  - Path resolution
- **Usage**: Throughout build pipeline

## Atomic Write (`bengal/utils/atomic_write.py`)
- **Purpose**: Atomic file writes for data integrity
- **Pattern**: Write to temp file → atomic rename
- **Usage**: Cache persistence, output file writing
- **Benefits**: No partial writes, crash-safe

## URL Strategy (`bengal/utils/url_strategy.py`)
- **Purpose**: URL generation strategies
- **Strategies**: Pretty URLs, flat URLs, date-based URLs
- **Usage**: Content type system, page URL generation

## Theme Utilities

### ThemeRegistry (`bengal/utils/theme_registry.py`)
- **Purpose**: Manage available themes
- **Functions**: Register, discover, validate themes
- **Usage**: Theme selection and loading

### ThemeResolution (`bengal/utils/theme_resolution.py`)
- **Purpose**: Resolve theme inheritance chain
- **Functions**: Resolve templates, resolve assets, fallback chain
- **Usage**: Template engine, asset discovery

### Swizzle (`bengal/utils/swizzle.py`)
- **Purpose**: Override theme components (swizzling)
- **Functions**: Copy theme file to site, track overrides
- **Usage**: CLI swizzle command

## Error Handling

### ErrorHandlers (`bengal/utils/error_handlers.py`)
- **Purpose**: Centralized error handling patterns
- **Handlers**: File errors, template errors, build errors
- **Usage**: Throughout build pipeline

### TracebackConfig (`bengal/utils/traceback_config.py`)
- **Purpose**: Configure Rich traceback display
- **Features**: Colored output, local variables, filtering
- **Usage**: CLI error display

### TracebackRenderer (`bengal/utils/traceback_renderer.py`)
- **Purpose**: Custom traceback formatting
- **Features**: Context lines, syntax highlighting
- **Usage**: Dev server, CLI error output

## CLI Utilities

### CLIOutput (`bengal/utils/cli_output.py`)
- **Purpose**: Formatted CLI output helpers
- **Functions**: Success/error/warning messages, tables, progress
- **Usage**: All CLI commands

### RichConsole (`bengal/utils/rich_console.py`)
- **Purpose**: Shared Rich console instance
- **Features**: Consistent styling, color themes
- **Usage**: CLI output, progress display

### Logger (`bengal/utils/logger.py`)
- **Purpose**: Structured logging for Bengal
- **Features**: Levels, formatting, file output
- **Usage**: Throughout build pipeline

## Performance Utilities

### PerformanceCollector (`bengal/utils/performance_collector.py`)
- **Purpose**: Collect performance metrics during build
- **Tracks**: Phase timings, memory usage, bottlenecks
- **Usage**: Performance profiling commands

### PerformanceReport (`bengal/utils/performance_report.py`)
- **Purpose**: Format performance metrics for display
- **Features**: Flamegraphs, timing tables, bottleneck detection
- **Usage**: CLI perf command

### Profile (`bengal/utils/profile.py`)
- **Purpose**: cProfile wrapper with context manager
- **Usage**: Performance profiling with --perf-profile flag

## Page Utilities

### PageInitializer (`bengal/utils/page_initializer.py`)
- **Purpose**: Initialize Page objects from files
- **Functions**: Parse frontmatter, extract content, setup metadata
- **Usage**: Content discovery

### DotDict (`bengal/utils/dotdict.py`)
- **Purpose**: Dict with dot notation access
- **Example**: `config.build.parallel` instead of `config['build']['parallel']`
- **Usage**: Configuration, template context

## Design Principles

1. **Single Responsibility**: Each utility module has one clear purpose
2. **No Business Logic**: Utilities are reusable helpers, not business logic
3. **Type Safety**: Full type hints throughout
4. **Error Handling**: Consistent error handling patterns
5. **Testing**: High test coverage (70-96% across modules)
6. **Documentation**: Docstrings and examples for all utilities

## Utility Adoption Pattern

When functionality is duplicated across multiple files:
1. Extract to utility module
2. Add comprehensive tests
3. Update all call sites
4. Document in architecture docs

**Example**: Text utilities extracted from 9 files, reducing code by 311 lines and adding 74 tests.

## Benefits of Utility Consolidation

- **Code Reduction**: Eliminate duplication
- **Consistency**: Single implementation
- **Testability**: Test once, use everywhere
- **Maintainability**: Fix once, benefit everywhere
- **Type Safety**: Centralized type checking
- **Performance**: Optimize once

## Related Documentation

- [Design Principles](../core/design-principles.md) - Overall design patterns
- [File Organization](../meta/file-organization.md) - Directory structure
- [Testing](../meta/testing.md) - Testing strategy and coverage
