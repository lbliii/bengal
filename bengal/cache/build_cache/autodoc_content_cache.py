"""
Autodoc content caching mixin for BuildCache.

RFC: rfc-build-performance-optimizations Phase 3
Caches parsed autodoc module information to avoid re-parsing AST on every build.

This mixin extends AutodocTrackingMixin to cache the actual parsed module data,
not just the source→page dependency mapping. This enables skipping AST parsing
for unchanged Python source files.

Key Concepts:
- Content hash keying: Cache entries keyed by source file path + content hash
- Conservative invalidation: Only invalidate when source hash changes
- Thread-safe: Cache is read-only during parallel extraction

Related Modules:
- bengal.cache.build_cache.autodoc_tracking: Source→page dependency tracking
- bengal.autodoc.extractors.python.extractor: Python AST extraction
- bengal.utils.hashing: Shared hashing utilities

See Also:
- plan/rfc-build-performance-optimizations.md: Performance optimization RFC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CachedModuleInfo:
    """Cached parsed module data.
    
    Contains all information extracted from a Python module's AST,
    allowing us to skip AST parsing on subsequent builds if the source
    file hasn't changed.
    
    Attributes:
        source_hash: Content hash of the source file (for validation)
        module_name: Inferred module name
        docstring: Module-level docstring
        classes: List of class metadata dicts
        functions: List of function metadata dicts
        aliases: Dict of alias_name → canonical_name mappings
        ast_tree: Optional serialized AST tree (if needed for inheritance synthesis)
    """
    
    source_hash: str
    module_name: str
    docstring: str | None
    classes: list[dict[str, Any]]
    functions: list[dict[str, Any]]
    aliases: dict[str, str]
    # Optional: Store AST tree if needed for inheritance synthesis
    # For now, we'll re-parse if inheritance is enabled (simpler)
    # ast_tree: Any | None = None


class AutodocContentCacheMixin:
    """
    Cache parsed autodoc content between builds.
    
    RFC: rfc-build-performance-optimizations Phase 3
    Extends AutodocTrackingMixin to cache parsed module information,
    enabling AST parsing to be skipped for unchanged source files.
    
    This mixin expects to be used with BuildCache which already has
    AutodocTrackingMixin for dependency tracking.
    """
    
    # Cache: source_file_path → CachedModuleInfo
    autodoc_content_cache: dict[str, CachedModuleInfo] = field(default_factory=dict)
    
    def get_cached_module(
        self,
        source_path: str,
        source_hash: str,
    ) -> CachedModuleInfo | None:
        """
        Return cached module info if hash matches.
        
        Args:
            source_path: Path to Python source file
            source_hash: Current content hash of source file
        
        Returns:
            CachedModuleInfo if cache hit (hash matches), None otherwise
        """
        cached = self.autodoc_content_cache.get(source_path)
        if cached and cached.source_hash == source_hash:
            logger.debug(
                "autodoc_cache_hit",
                source_path=source_path,
                hash=source_hash[:8],
            )
            return cached
        
        if cached:
            logger.debug(
                "autodoc_cache_miss_hash_mismatch",
                source_path=source_path,
                cached_hash=cached.source_hash[:8],
                current_hash=source_hash[:8],
            )
        
        return None
    
    def cache_module(
        self,
        source_path: str,
        info: CachedModuleInfo,
    ) -> None:
        """
        Cache parsed module info.
        
        Args:
            source_path: Path to Python source file
            info: CachedModuleInfo with parsed module data
        """
        self.autodoc_content_cache[source_path] = info
        logger.debug(
            "autodoc_module_cached",
            source_path=source_path,
            hash=info.source_hash[:8],
            classes=len(info.classes),
            functions=len(info.functions),
        )
    
    def clear_autodoc_content_cache(self) -> None:
        """Clear all cached autodoc content."""
        count = len(self.autodoc_content_cache)
        self.autodoc_content_cache.clear()
        logger.debug("autodoc_content_cache_cleared", count=count)
