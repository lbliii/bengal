"""
Cache module for incremental builds.
"""

from __future__ import annotations

from bengal.cache.build_cache import BuildCache
from bengal.cache.dependency_tracker import DependencyTracker
from bengal.cache.query_index import IndexEntry, QueryIndex
from bengal.cache.query_index_registry import QueryIndexRegistry
from bengal.cache.utils import clear_build_cache, clear_output_directory

__all__ = [
    "BuildCache",
    "DependencyTracker",
    "QueryIndex",
    "IndexEntry",
    "QueryIndexRegistry",
    "clear_build_cache",
    "clear_output_directory",
]
