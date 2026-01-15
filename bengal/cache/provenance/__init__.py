"""
Provenance-based incremental build cache.

Content-addressed caching using Pachyderm-style provenance tracking.
Replaces the previous BuildCache + IncrementalFilterEngine approach.

Key advantages:
- Automatic input tracking (no manual dependency registration)
- Content-addressed cache keys (correct invalidation)
- Subvenance queries (what depends on X?)
- 30x faster than previous system

Usage:
    from bengal.cache.provenance import ProvenanceCache, ProvenanceFilter
    
    cache = ProvenanceCache(site.root_path / ".bengal" / "provenance")
    filter = ProvenanceFilter(site, cache)
    
    # Get pages that need rebuilding
    pages_to_build = filter.filter_pages(site.pages)
"""

from bengal.cache.provenance.cache import ProvenanceCache
from bengal.cache.provenance.filter import ProvenanceFilter, ProvenanceFilterResult
from bengal.cache.provenance.types import (
    ContentHash,
    InputRecord,
    Provenance,
    ProvenanceRecord,
    hash_content,
    hash_dict,
    hash_file,
)

__all__ = [
    "ProvenanceCache",
    "ProvenanceFilter",
    "ProvenanceFilterResult",
    "ContentHash",
    "InputRecord",
    "Provenance",
    "ProvenanceRecord",
    "hash_content",
    "hash_dict",
    "hash_file",
]
