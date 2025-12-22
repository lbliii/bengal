"""
Utility functions and classes for Bengal SSG.

This package provides core utilities used throughout the Bengal static site generator.
Utilities are organized by function and follow Bengal's design principles of separation
of concerns, no global mutable state, and comprehensive error handling.

Categories:
    **Async & Concurrency**:
        - async_compat: uvloop integration for Rust-accelerated async I/O
        - thread_local: Thread-local caching for expensive objects
        - retry: Exponential backoff retry utilities

    **File Operations**:
        - file_io: Robust file reading/writing with encoding fallback
        - atomic_write: Crash-safe file writes using temp-then-rename
        - file_lock: Cross-platform file locking for concurrent builds

    **Path Management**:
        - paths: Directory structure management (BengalPaths)
        - path_resolver: CWD-independent path resolution (PathResolver)
        - url_normalization: URL path normalization and validation
        - url_strategy: URL and output path computation

    **Data Processing**:
        - hashing: Cryptographic hashing for cache keys and fingerprinting
        - text: Text processing (slugify, truncate, HTML strip)
        - dates: Date parsing, formatting, and "time ago"
        - dotdict: Dictionary with dot notation access for templates
        - json_compat: Rust-accelerated JSON via orjson

    **Build Infrastructure**:
        - build_context: Shared state across build phases
        - progress: Protocol-based progress reporting
        - profile: Build profiles (Writer/Theme-Dev/Developer)
        - observability: Standardized stats collection
        - logger: Structured logging with phase tracking

    **Asset Processing**:
        - css_minifier: Safe CSS minification preserving modern features
        - js_bundler: Pure Python JavaScript bundling

    **Performance & Metrics**:
        - performance_collector: Build metrics collection
        - performance_report: Metrics analysis and reporting

    **Theme & Versioning**:
        - swizzle: Safe theme template override management
        - version_diff: Documentation version comparison
        - metadata: Build metadata generation for templates

Key Design Principles:
    - No global mutable state (see bengal/.cursor/rules/no-globals.mdc)
    - Graceful error handling with actionable suggestions
    - Thread-safety where concurrent access is expected
    - Pure functions where possible for testability

Example:
    >>> from bengal.utils import hash_str, humanize_slug, run_async
    >>> from bengal.utils.file_io import read_text_file, load_yaml
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

from bengal.core.section import resolve_page_section_path
from bengal.utils import (
    async_compat,
    dates,
    file_io,
    hashing,
    retry,
    text,
    thread_local,
)
from bengal.utils.async_compat import run_async
from bengal.utils.hashing import hash_bytes, hash_dict, hash_file, hash_file_with_stat, hash_str
from bengal.utils.pagination import Paginator
from bengal.utils.path_resolver import PathResolver, resolve_path
from bengal.utils.paths import BengalPaths
from bengal.utils.retry import async_retry_with_backoff, calculate_backoff, retry_with_backoff
from bengal.utils.text import humanize_slug
from bengal.utils.thread_local import ThreadLocalCache, ThreadSafeSet

__all__ = [
    "BengalPaths",
    "Paginator",
    "PathResolver",
    "ThreadLocalCache",
    "ThreadSafeSet",
    "async_compat",
    "async_retry_with_backoff",
    "calculate_backoff",
    "dates",
    "file_io",
    "hash_bytes",
    "hash_dict",
    "hash_file",
    "hash_file_with_stat",
    "hash_str",
    "hashing",
    "humanize_slug",
    "resolve_path",
    "resolve_page_section_path",
    "retry",
    "retry_with_backoff",
    "run_async",
    "text",
    "thread_local",
]
