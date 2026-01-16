"""
Utility sub-packages for Bengal SSG.

Sub-Packages:
    primitives/: Pure functions with no Bengal imports (hashing, text, dates, sentinel, dotdict, lru_cache)
    io/: File I/O utilities (file_io, atomic_write, file_lock, json_compat)
    paths/: Path management (paths, path_resolver, url_normalization, url_strategy)
    concurrency/: Thread/async utilities (concurrent_locks, thread_local, async_compat, retry, gil, workers)
    observability/: Logging, metrics, progress (logger, rich_console, progress, observability, performance_*)
    pagination/: Collection pagination utilities

Example:
    >>> from bengal.utils.primitives import hash_str, slugify, LRUCache
    >>> from bengal.utils.io import read_text_file, load_yaml
    >>> from bengal.utils.observability.observability import get_logger
    >>> from bengal.utils.pagination import Paginator

"""

from bengal.utils import concurrency, io, observability, pagination, paths, primitives

# Re-export commonly used utilities for convenience
from bengal.utils.pagination import Paginator
from bengal.utils.primitives.lru_cache import LRUCache

__all__ = [
    # Sub-packages
    "primitives",
    "io",
    "paths",
    "concurrency",
    "observability",
    "pagination",
    # Re-exported utilities
    "LRUCache",
    "Paginator",
]
