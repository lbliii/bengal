"""
Cache subsystem for incremental builds and fast queries.

This package provides caching infrastructure that enables Bengal's incremental
build system, achieving 10-100x faster rebuilds by tracking file changes,
dependencies, and pre-computed indexes.

Core Components:
    BuildCache: Central cache for file fingerprints, dependencies, and build state.
        Tracks mtime/size/hash for change detection, template dependencies, and
        taxonomy indexes. Persisted as compressed JSON (92-93% smaller with Zstandard).

    CacheStore: Generic type-safe storage for Cacheable types with version management.
        Handles JSON serialization, compression, and tolerant loading.

    DependencyTracker: Tracks template, partial, and data file dependencies during
        rendering. Enables selective rebuilding when dependencies change.

    QueryIndex: Base class for O(1) page lookups by attribute. Built-in indexes
        include section, author, category, and date_range.

    TaxonomyIndex: Bidirectional tag-to-page mappings for incremental taxonomy
        updates without full rebuilds.

Caching Strategy:
    - File fingerprints: Fast mtime+size check, SHA256 hash for verification
    - Parsed content: Cached HTML/TOC skips re-parsing when only templates change
    - Rendered output: Cached final HTML skips both parsing and template rendering
    - Query indexes: Pre-computed for O(1) template lookups

Performance Impact:
    - Incremental builds: 10-100x faster than full builds
    - Change detection: <1ms per file (mtime+size fast path)
    - Compression: 92-93% cache size reduction, <1ms overhead

Directory Structure:
    .bengal/
    ├── cache.json.zst         # Main build cache (compressed)
    ├── page_metadata.json.zst # Page discovery cache (compressed)
    ├── asset_deps.json.zst    # Asset dependency map (compressed)
    ├── taxonomy_index.json.zst # Tag/category index (compressed)
    └── indexes/               # Query indexes (section, author, etc.)

Performance Note:
    This module uses lazy imports to avoid loading heavy cache infrastructure
    until it's actually needed. The lightweight BengalPaths and STATE_DIR_NAME
    are loaded eagerly.

Related Modules:
    - bengal.orchestration.incremental: Build logic using this cache
    - bengal.rendering.pipeline: Rendering with dependency tracking

See Also:
    - architecture/cache.md: Cache architecture documentation
    - plan/active/rfc-incremental-builds.md: Incremental build design
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# =============================================================================
# EAGERLY LOADED - Lightweight path utilities (no heavy deps)
# =============================================================================
from bengal.cache.paths import STATE_DIR_NAME, BengalPaths

# =============================================================================
# TYPE_CHECKING - For static analysis without runtime cost
# =============================================================================

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.cache.cache_store import CacheStore
    from bengal.cache.cacheable import Cacheable
    from bengal.cache.compression import (
        COMPRESSION_LEVEL,
        load_compressed,
        save_compressed,
    )
    from bengal.cache.dependency_tracker import DependencyTracker
    from bengal.cache.query_index import IndexEntry, QueryIndex
    from bengal.cache.query_index_registry import QueryIndexRegistry
    from bengal.cache.utils import (
        clear_build_cache,
        clear_output_directory,
        clear_template_cache,
    )

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


# =============================================================================
# LAZY IMPORTS - Heavy modules loaded on first access
# =============================================================================

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Build cache
    "BuildCache": ("bengal.cache.build_cache", "BuildCache"),
    # Cache store
    "CacheStore": ("bengal.cache.cache_store", "CacheStore"),
    "Cacheable": ("bengal.cache.cacheable", "Cacheable"),
    # Compression
    "COMPRESSION_LEVEL": ("bengal.cache.compression", "COMPRESSION_LEVEL"),
    "load_compressed": ("bengal.cache.compression", "load_compressed"),
    "save_compressed": ("bengal.cache.compression", "save_compressed"),
    # Dependency tracker
    "DependencyTracker": ("bengal.cache.dependency_tracker", "DependencyTracker"),
    # Query index
    "IndexEntry": ("bengal.cache.query_index", "IndexEntry"),
    "QueryIndex": ("bengal.cache.query_index", "QueryIndex"),
    "QueryIndexRegistry": ("bengal.cache.query_index_registry", "QueryIndexRegistry"),
    # Utils
    "clear_build_cache": ("bengal.cache.utils", "clear_build_cache"),
    "clear_output_directory": ("bengal.cache.utils", "clear_output_directory"),
    "clear_template_cache": ("bengal.cache.utils", "clear_template_cache"),
}


def __getattr__(name: str) -> Any:
    """
    Lazy import for heavy cache infrastructure.

    This avoids loading BuildCache, compression, and other heavy modules
    until they are actually needed. BengalPaths is lightweight and loaded
    eagerly for path operations.
    """
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, attr_name)
    raise AttributeError(f"module 'bengal.cache' has no attribute {name!r}")
