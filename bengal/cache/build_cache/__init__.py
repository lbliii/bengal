"""
Build cache package for tracking file changes and dependencies.

This package provides the BuildCache class for incremental builds, split into
focused modules following Bengal's architecture patterns (400-line threshold).

Structure:
    - core.py: Main BuildCache dataclass with fields, save/load, coordination
    - fingerprint.py: FileFingerprint for fast change detection
    - file_tracking.py: FileTrackingMixin for hash/change/dependency tracking
    - validation_cache.py: ValidationCacheMixin for CheckResult caching
    - taxonomy_index_mixin.py: TaxonomyIndexMixin for tag/page indexing
    - parsed_content_cache.py: ParsedContentCacheMixin for markdown caching
    - rendered_output_cache.py: RenderedOutputCacheMixin for HTML caching

Key Concepts:
    - File fingerprints: mtime + size for fast change detection, hash for verification
    - Dependency tracking: Templates, partials, and data files used by pages
    - Taxonomy indexes: Tag/category mappings for fast reconstruction
    - Config hash: Auto-invalidation when configuration changes
    - Version tolerance: Accepts missing/older cache versions gracefully
    - Zstandard compression: 92-93% size reduction, <1ms overhead

Related Modules:
    - bengal.orchestration.incremental: Incremental build logic using cache
    - bengal.cache.dependency_tracker: Dependency graph construction
    - bengal.cache.taxonomy_index: Taxonomy reconstruction from cache
    - bengal.cache.compression: Zstandard compression utilities

Usage:

```python
from bengal.cache.build_cache import BuildCache, FileFingerprint

cache = BuildCache.load(cache_path)
if cache.is_changed(file_path):
    # Process file...
    cache.update_file(file_path)
cache.save(cache_path)
```

See Also:
    - plan/active/rfc-incremental-builds.md: Incremental build design
    - plan/active/rfc-orchestrator-performance-improvements.md: Performance RFC
"""

from __future__ import annotations

from bengal.cache.build_cache.core import BuildCache
from bengal.cache.build_cache.fingerprint import FileFingerprint

__all__ = [
    "BuildCache",
    "FileFingerprint",
]
