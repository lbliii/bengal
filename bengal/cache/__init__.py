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
    ├── page_metadata.json     # Page discovery cache
    ├── asset_deps.json        # Asset dependency map
    ├── taxonomy_index.json    # Tag/category index
    └── indexes/               # Query indexes (section, author, etc.)

Related Modules:
    - bengal.orchestration.incremental: Build logic using this cache
    - bengal.rendering.pipeline: Rendering with dependency tracking

See Also:
    - architecture/cache.md: Cache architecture documentation
    - plan/active/rfc-incremental-builds.md: Incremental build design
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
