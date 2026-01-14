"""
Utility sub-packages for Bengal SSG.

Sub-Packages:
    primitives/: Pure functions with no Bengal imports (hashing, text, dates, sentinel, dotdict)
    io/: File I/O utilities (file_io, atomic_write, file_lock, json_compat)
    paths/: Path management (paths, path_resolver, url_normalization, url_strategy)
    concurrency/: Thread/async utilities (concurrent_locks, thread_local, async_compat, retry, gil, workers)
    observability/: Logging, metrics, progress (logger, rich_console, progress, observability, performance_*)

Example:
    >>> from bengal.utils.primitives import hash_str, slugify
    >>> from bengal.utils.io import read_text_file, load_yaml
    >>> from bengal.utils.observability.observability import get_logger

"""

from bengal.utils import concurrency, io, observability, paths, primitives

# Utilities that haven't been moved to sub-packages yet
from bengal.utils.lru_cache import LRUCache
from bengal.utils.pagination import Paginator

__all__ = [
    # Sub-packages
    "primitives",
    "io",
    "paths",
    "concurrency",
    "observability",
    # Standalone utilities
    "LRUCache",
    "Paginator",
]
