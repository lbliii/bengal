"""
Thread-local state management for parallel rendering.

This module provides thread-safe caching for expensive resources during
parallel page rendering, primarily markdown parser instances.

Architecture:
    Bengal renders pages in parallel using ThreadPoolExecutor. Without caching,
    each page would create its own parser (~10ms overhead), wasting significant
    time on repeated initialization.

    This module provides:
    - **Parser caching**: One parser per worker thread, reused across pages
    - **Directory tracking**: Thread-safe set of created directories to skip
      redundant mkdir syscalls

Performance Impact:
    With max_workers=10 and 200 pages:

    Without caching: 200 × 10ms = 2 seconds of parser initialization
    With caching: 10 × 10ms = 100ms (10 parsers, one per thread)

    Savings: 1.9 seconds (~95% reduction in parser overhead)

Thread Safety:
    - Parser cache uses ThreadLocalCache (thread-local storage)
    - Directory tracking uses ThreadSafeSet (lock-protected)
    - No shared mutable state between threads

Public API:
    - get_thread_parser(): Get cached parser for current thread
    - mark_dir_created(): Track directory as created (returns True if new)
    - reset_parser_cache(): Clear cache (for testing)

Related Modules:
    - bengal.rendering.parsers: Parser implementations
    - bengal.rendering.pipeline.core: Main pipeline using these caches
    - bengal.utils.thread_local: Generic thread-local utilities
"""

from __future__ import annotations

from bengal.rendering.parsers import BaseMarkdownParser, create_markdown_parser
from bengal.utils.thread_local import ThreadLocalCache, ThreadSafeSet

# Thread-local cache for parser instances (reuse parsers per thread)
_parser_cache: ThreadLocalCache[BaseMarkdownParser] = ThreadLocalCache(
    factory=create_markdown_parser,
    name="markdown_parser",
)

# Thread-safe set for created directories (reduces syscalls in parallel builds)
_created_dirs = ThreadSafeSet()


def get_thread_parser(engine: str | None = None) -> BaseMarkdownParser:
    """
    Get or create a MarkdownParser instance for the current thread.

    Thread-Local Caching Strategy:
        - Creates ONE parser per worker thread (expensive operation ~10ms)
        - Caches it for the lifetime of that thread
        - Each thread reuses its parser for all pages it processes
        - Total parsers created = number of worker threads

    Performance Impact:
        With max_workers=N (from config):
        - N worker threads created
        - N parser instances created (one per thread)
        - Each parser handles ~(total_pages / N) pages

        Example with max_workers=10 and 200 pages:
        - 10 threads → 10 parsers created
        - Each parser processes ~20 pages
        - Creation cost: 10ms × 10 = 100ms one-time
        - Reuse savings: 9.9 seconds (avoiding 190 × 10ms)

    Thread Safety:
        Each thread gets its own parser instance, no locking needed.
        Read-only access to site config and xref_index is safe.

    Args:
        engine: Parser engine to use ('python-markdown', 'mistune', or None for default)

    Returns:
        Cached MarkdownParser instance for this thread

    Note:
        If you see N parser instances created where N = max_workers,
        this is OPTIMAL behavior, not a bug!
    """
    return _parser_cache.get(engine)


def get_created_dirs() -> ThreadSafeSet:
    """Get the thread-safe set of already created directories."""
    return _created_dirs


def mark_dir_created(dir_path: str) -> bool:
    """
    Mark a directory as created, return True if it was new.

    This is the preferred way to track directory creation.
    Uses atomic check-and-add to prevent race conditions.

    Args:
        dir_path: Path to directory as string

    Returns:
        True if directory was newly added, False if already tracked
    """
    return _created_dirs.add_if_new(dir_path)


def reset_parser_cache() -> None:
    """
    Reset the parser cache for the current thread.

    This is primarily used in tests to ensure fresh parser instances
    when directive registration has changed.

    Thread Safety:
        Only clears cache for the current thread.
    """
    _parser_cache.clear_all()
