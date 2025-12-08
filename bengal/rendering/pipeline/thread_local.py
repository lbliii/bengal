"""
Thread-local parser management for rendering pipeline.

Provides thread-safe parser instance caching to avoid expensive re-initialization
during parallel page rendering.

Related Modules:
    - bengal.rendering.parsers: Parser implementations
    - bengal.rendering.pipeline.core: Uses thread-local parsers
"""

from __future__ import annotations

import threading

from bengal.rendering.parsers import BaseMarkdownParser, create_markdown_parser

# Thread-local storage for parser instances (reuse parsers per thread)
_thread_local = threading.local()

# Cache for created directories (reduces syscalls in parallel builds)
_created_dirs: set = set()
_created_dirs_lock = threading.Lock()


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
    # Store parser per engine type
    cache_key = f"parser_{engine or 'default'}"
    if not hasattr(_thread_local, cache_key):
        setattr(_thread_local, cache_key, create_markdown_parser(engine))
    return getattr(_thread_local, cache_key)


def get_created_dirs() -> set:
    """Get the set of already created directories."""
    return _created_dirs


def get_created_dirs_lock() -> threading.Lock:
    """Get the lock for thread-safe directory creation."""
    return _created_dirs_lock

