"""
Cache module for incremental builds.

Includes Zstandard compression support (PEP 784) for 92-93% size reduction.
"""

from __future__ import annotations

from bengal.cache.build_cache import BuildCache
from bengal.cache.cache_store import CacheStore
from bengal.cache.cacheable import Cacheable

# Compression utilities (Python 3.14+ stdlib)
from bengal.cache.compression import (
    COMPRESSION_LEVEL,
    load_compressed,
    save_compressed,
)
from bengal.cache.dependency_tracker import DependencyTracker
from bengal.cache.paths import STATE_DIR_NAME, BengalPaths
from bengal.cache.query_index import IndexEntry, QueryIndex
from bengal.cache.query_index_registry import QueryIndexRegistry
from bengal.cache.utils import clear_build_cache, clear_output_directory, clear_template_cache

__all__ = [
    "BengalPaths",
    "BuildCache",
    "Cacheable",
    "CacheStore",
    "COMPRESSION_LEVEL",
    "DependencyTracker",
    "IndexEntry",
    "QueryIndex",
    "QueryIndexRegistry",
    "STATE_DIR_NAME",
    "clear_build_cache",
    "clear_output_directory",
    "clear_template_cache",
    "load_compressed",
    "save_compressed",
]
