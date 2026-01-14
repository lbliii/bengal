"""
Utility functions and classes for Bengal SSG.

This package provides core utilities used throughout the Bengal static site generator.
Utilities are organized by function into sub-packages following Bengal's design principles
of separation of concerns, no global mutable state, and comprehensive error handling.

Sub-Packages:
    primitives/: Pure functions with no Bengal imports (hashing, text, dates, sentinel, dotdict)
    io/: File I/O utilities (file_io, atomic_write, file_lock, json_compat)
    paths/: Path management (paths, path_resolver, url_normalization, url_strategy)
    concurrency/: Thread/async utilities (concurrent_locks, thread_local, async_compat, retry, gil, workers)
    observability/: Logging, metrics, progress (logger, rich_console, progress, observability, performance_*)

Example:
    >>> from bengal.utils import hash_str, humanize_slug, run_async
    >>> from bengal.utils.io import read_text_file, load_yaml
    >>>
    >>> # Hash content for cache keys
    >>> key = hash_str("content", truncate=8)
    >>>
    >>> # Humanize slugs for display
    >>> title = humanize_slug("my-page-name")  # "My Page Name"
    >>>
    >>> # Run async code with uvloop
    >>> result = run_async(fetch_data())

Related Modules:
- bengal/core/: Data models (Page, Site, Section)
- bengal/orchestration/: Build operations
- bengal/rendering/: Template rendering
- bengal/cache/: Caching infrastructure

See Also:
- architecture/file-organization.md: File organization patterns
- bengal/.cursor/rules/python-style.mdc: Python coding standards

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# ==============================================================================
# Re-exports from sub-packages for backward compatibility
# ==============================================================================

# primitives - pure functions, no Bengal imports
from bengal.utils.primitives import (
    MISSING,
    DateLike,
    DotDict,
    date_range_overlap,
    escape_html,
    format_date_human,
    format_date_iso,
    format_date_rfc822,
    format_path_for_display,
    generate_excerpt,
    get_current_year,
    hash_bytes,
    hash_dict,
    hash_file,
    hash_file_with_stat,
    hash_str,
    humanize_bytes,
    humanize_number,
    humanize_slug,
    is_missing,
    is_recent,
    iso_timestamp,
    normalize_whitespace,
    parse_date,
    pluralize,
    slugify,
    strip_html,
    time_ago,
    truncate_chars,
    truncate_middle,
    truncate_words,
    unescape_html,
    utc_now,
    wrap_data,
)

# concurrency - thread/async utilities
from bengal.utils.concurrency import (
    Environment,
    PerKeyLockManager,
    ThreadLocalCache,
    ThreadSafeSet,
    WorkloadProfile,
    WorkloadType,
    async_retry_with_backoff,
    calculate_backoff,
    detect_environment,
    estimate_page_weight,
    format_gil_tip_for_cli,
    get_gil_status_message,
    get_optimal_workers,
    get_profile,
    has_free_threading_support,
    install_uvloop,
    is_gil_disabled,
    order_by_complexity,
    retry_with_backoff,
    run_async,
    should_parallelize,
)

# paths - path management
from bengal.utils.paths import (
    BengalPaths,
    LegacyBengalPaths,
    PathResolver,
    URLStrategy,
    join_url_paths,
    normalize_url,
    resolve_path,
    validate_url,
)

# io - file I/O utilities
from bengal.utils.io import (
    DEFAULT_LOCK_TIMEOUT,
    AtomicFile,
    JSONDecodeError,
    LockAcquisitionError,
    atomic_write_bytes,
    atomic_write_text,
    dump,
    dumps,
    file_lock,
    is_locked,
    load,
    load_data_file,
    load_json,
    load_toml,
    load_yaml,
    loads,
    read_text_file,
    remove_stale_lock,
    rmtree_robust,
    write_json,
    write_text_file,
)

# observability - logging, metrics, progress
from bengal.utils.observability import (
    BengalLogger,
    BuildMetric,
    BuildProfile,
    ComponentStats,
    HasStats,
    LazyLogger,
    LiveProgressReporterAdapter,
    LogEvent,
    LogLevel,
    NoopReporter,
    PALETTE,
    PerformanceCollector,
    PerformanceReport,
    ProgressReporter,
    bengal_theme,
    close_all_loggers,
    configure_logging,
    detect_environment as detect_rich_environment,
    format_memory,
    format_phase_stats,
    get_console,
    get_current_profile,
    get_enabled_health_checks,
    get_logger,
    is_live_display_active,
    is_validator_enabled,
    print_all_summaries,
    reset_console,
    reset_loggers,
    set_console_quiet,
    set_current_profile,
    should_collect_metrics,
    should_show_debug,
    should_track_memory,
    should_use_emoji,
    should_use_rich,
    truncate_error,
    truncate_str,
)

# Also import directly from the old flat module locations for legacy backward compatibility
# These are imported directly rather than through sub-packages
from bengal.utils import (
    concurrent_locks,
    dates,
    file_io,
    hashing,
    retry,
    sentinel,
    text,
    thread_local,
)

# LRU Cache and Paginator (utilities that aren't in sub-packages yet)
from bengal.utils.lru_cache import LRUCache
from bengal.utils.pagination import Paginator

# TYPE_CHECKING imports for static analysis (no runtime cost)
if TYPE_CHECKING:
    from bengal.core.section import resolve_page_section_path as _resolve_page_section_path
    from bengal.utils import async_compat as _async_compat
    from bengal.utils.async_compat import run_async as _run_async

__all__ = [
    # primitives
    "hash_str",
    "hash_bytes",
    "hash_dict",
    "hash_file",
    "hash_file_with_stat",
    "slugify",
    "strip_html",
    "truncate_words",
    "truncate_chars",
    "truncate_middle",
    "generate_excerpt",
    "normalize_whitespace",
    "escape_html",
    "unescape_html",
    "pluralize",
    "humanize_bytes",
    "humanize_number",
    "humanize_slug",
    "format_path_for_display",
    "DateLike",
    "parse_date",
    "format_date_iso",
    "format_date_rfc822",
    "format_date_human",
    "time_ago",
    "get_current_year",
    "is_recent",
    "date_range_overlap",
    "utc_now",
    "iso_timestamp",
    "MISSING",
    "is_missing",
    "DotDict",
    "wrap_data",
    # paths
    "BengalPaths",
    "LegacyBengalPaths",
    "PathResolver",
    "resolve_path",
    "normalize_url",
    "join_url_paths",
    "validate_url",
    "URLStrategy",
    # io
    "read_text_file",
    "load_json",
    "load_yaml",
    "load_toml",
    "load_data_file",
    "write_text_file",
    "write_json",
    "rmtree_robust",
    "atomic_write_text",
    "atomic_write_bytes",
    "AtomicFile",
    "file_lock",
    "is_locked",
    "remove_stale_lock",
    "LockAcquisitionError",
    "DEFAULT_LOCK_TIMEOUT",
    "dumps",
    "loads",
    "dump",
    "load",
    "JSONDecodeError",
    # concurrency
    "PerKeyLockManager",
    "ThreadLocalCache",
    "ThreadSafeSet",
    "run_async",
    "install_uvloop",
    "calculate_backoff",
    "retry_with_backoff",
    "async_retry_with_backoff",
    "is_gil_disabled",
    "has_free_threading_support",
    "get_gil_status_message",
    "format_gil_tip_for_cli",
    "WorkloadType",
    "Environment",
    "WorkloadProfile",
    "detect_environment",
    "get_optimal_workers",
    "should_parallelize",
    "estimate_page_weight",
    "order_by_complexity",
    "get_profile",
    # observability
    "BengalLogger",
    "LazyLogger",
    "LogLevel",
    "LogEvent",
    "get_logger",
    "configure_logging",
    "set_console_quiet",
    "close_all_loggers",
    "reset_loggers",
    "print_all_summaries",
    "truncate_str",
    "truncate_error",
    "PALETTE",
    "bengal_theme",
    "get_console",
    "should_use_rich",
    "should_use_emoji",
    "detect_rich_environment",
    "reset_console",
    "is_live_display_active",
    "ProgressReporter",
    "NoopReporter",
    "LiveProgressReporterAdapter",
    "ComponentStats",
    "HasStats",
    "format_phase_stats",
    "PerformanceCollector",
    "format_memory",
    "BuildMetric",
    "PerformanceReport",
    "BuildProfile",
    "set_current_profile",
    "get_current_profile",
    "should_show_debug",
    "should_track_memory",
    "should_collect_metrics",
    "get_enabled_health_checks",
    "is_validator_enabled",
    # other utilities
    "LRUCache",
    "Paginator",
    # legacy module references
    "async_compat",
    "concurrent_locks",
    "dates",
    "file_io",
    "hashing",
    "resolve_page_section_path",
    "retry",
    "sentinel",
    "text",
    "thread_local",
]


def __getattr__(name: str) -> Any:
    """
    Lazy import for heavy dependencies.
    
    This avoids pulling in bengal.core.section (which triggers the full core infra)
    and async_compat (which loads uvloop) until they're actually needed.
        
    """
    if name == "resolve_page_section_path":
        from bengal.core.section import resolve_page_section_path

        return resolve_page_section_path
    if name == "async_compat":
        from bengal.utils import async_compat

        return async_compat
    raise AttributeError(f"module 'bengal.utils' has no attribute {name!r}")
