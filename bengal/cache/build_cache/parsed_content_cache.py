"""
Parsed content caching mixin for BuildCache.

Provides methods for caching parsed markdown content (HTML, TOC, AST) to skip
re-parsing when only templates change. Optimization #2 from the cache RFC.

Key Concepts:
- Caches rendered HTML (post-markdown, pre-template)
- Caches TOC and structured TOC items
- Optionally caches true AST for parse-once, use-many patterns
- Validates against metadata, template, and parser version
- Uses content hash for dependency validation

Related Modules:
- bengal.cache.build_cache.core: Main BuildCache class
- bengal.rendering.pipeline: Markdown parsing pipeline

"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.primitives.hashing import hash_file, hash_str
from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.sentinel import MISSING

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class ParsedContentCacheMixin:
    """
    Mixin providing parsed content caching (Optimization #2).
    
    Requires these attributes on the host class:
        - parsed_content: dict[str, dict[str, Any]]
        - dependencies: dict[str, set[str]]
        - is_changed: Callable[[Path], bool]  (from FileTrackingMixin)
        
    """

    # Type hints for mixin attributes (provided by host class)
    parsed_content: dict[str, dict[str, Any]]
    dependencies: dict[str, set[str]]

    def is_changed(self, file_path: Path) -> bool:
        """Check if file changed (provided by FileTrackingMixin)."""
        raise NotImplementedError("Must be provided by FileTrackingMixin")

    def store_parsed_content(
        self,
        file_path: Path,
        html: str,
        toc: str,
        toc_items: list[dict[str, Any]],
        links: list[str] | None,
        metadata: dict[str, Any],
        template: str,
        parser_version: str,
        ast: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Store parsed content in cache (Optimization #2 + AST caching).

        This allows skipping markdown parsing when only templates change,
        resulting in 20-30% faster builds in that scenario.

        Args:
            file_path: Path to source file
            html: Rendered HTML (post-markdown, pre-template)
            toc: Table of contents HTML
            toc_items: Structured TOC data
            links: Extracted links from the page (raw markdown extraction)
            metadata: Page metadata (frontmatter)
            template: Template name used
            parser_version: Parser version string (e.g., "mistune-3.0-toc2")
            ast: True AST tokens from parser (optional, for Phase 3)
        """
        from bengal.orchestration.constants import extract_nav_metadata

        # Hash full metadata to detect any changes
        metadata_str = json.dumps(metadata, sort_keys=True, default=str)
        metadata_hash = hash_str(metadata_str)

        # Hash only nav-affecting metadata for fine-grained section index change detection
        nav_metadata = extract_nav_metadata(metadata)
        nav_metadata_str = json.dumps(nav_metadata, sort_keys=True, default=str)
        nav_metadata_hash = hash_str(nav_metadata_str)

        # Hash only cascade metadata for fine-grained cascade change detection
        # RFC: Output Cache Architecture - Skip cascade rebuild on body-only changes
        cascade_metadata = metadata.get("cascade", {})
        cascade_metadata_str = json.dumps(cascade_metadata, sort_keys=True, default=str)
        cascade_metadata_hash = hash_str(cascade_metadata_str)

        # Calculate size for cache management
        size_bytes = len(html.encode("utf-8")) + len(toc.encode("utf-8"))
        if links:
            # Rough estimate for link list size (strings + separators)
            size_bytes += sum(len(link.encode("utf-8")) for link in links)
        if ast:
            # Estimate AST size (JSON serialization)
            ast_str = json.dumps(ast, default=str)
            size_bytes += len(ast_str.encode("utf-8"))

        # Store as dict (will be serialized to JSON)
        self.parsed_content[str(file_path)] = {
            "html": html,
            "toc": toc,
            "toc_items": toc_items,
            "links": links or [],
            "ast": ast,  # Phase 3: Store true AST tokens
            "metadata_hash": metadata_hash,
            "nav_metadata_hash": nav_metadata_hash,
            "cascade_metadata_hash": cascade_metadata_hash,
            "template": template,
            "parser_version": parser_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "size_bytes": size_bytes,
        }

    def get_parsed_content(
        self, file_path: Path, metadata: dict[str, Any], template: str, parser_version: str
    ) -> dict[str, Any] | Any:
        """
        Get cached parsed content if valid (Optimization #2).

        Uses content hash for dependency validation instead of mtime-first check.
        This prevents false invalidations when files are touched but not modified.

        Validates that:
        1. Content file hasn't changed (via file_fingerprints)
        2. Metadata hasn't changed (via metadata_hash)
        3. Template hasn't changed (via template name)
        4. Parser version matches (avoid incompatibilities)
        5. Template file content hasn't changed (via content hash comparison)

        Args:
            file_path: Path to source file
            metadata: Current page metadata
            template: Current template name
            parser_version: Current parser version

        Returns:
            Cached data dict if valid, MISSING if invalid or not found
        """
        key = str(file_path)

        # Check if cached
        cached = self.parsed_content.get(key, MISSING)
        if cached is MISSING:
            return MISSING

        # Validate file hasn't changed
        if self.is_changed(file_path):
            return MISSING

        # Validate metadata hasn't changed
        metadata_str = json.dumps(metadata, sort_keys=True, default=str)
        metadata_hash = hash_str(metadata_str)
        if cached.get("metadata_hash") != metadata_hash:
            return MISSING

        # Validate template hasn't changed (name)
        if cached.get("template") != template:
            return MISSING

        # Validate parser version (invalidate on upgrades)
        if cached.get("parser_version") != parser_version:
            return MISSING

        # Validate dependencies using content hash (not mtime).
        # This prevents false invalidations when files are touched but not modified.
        if key in self.dependencies:
            for dep_path in self.dependencies[key]:
                dep = Path(dep_path)
                if not dep.exists():
                    continue

                # Get cached fingerprint for this dependency
                cached_fp = self.file_fingerprints.get(dep_path)
                if not cached_fp:
                    # Dependency not tracked - treat as changed
                    logger.debug(
                        "dependency_not_tracked",
                        page=key,
                        dependency=dep_path,
                    )
                    return MISSING

                cached_hash = cached_fp.get("hash")
                if not cached_hash:
                    # No hash stored - treat as changed
                    logger.debug(
                        "dependency_no_hash",
                        page=key,
                        dependency=dep_path,
                    )
                    return MISSING

                # Compare content hashes (immune to mtime drift)
                try:
                    current_hash = hash_file(dep)
                    if current_hash != cached_hash:
                        logger.debug(
                            "dependency_changed",
                            page=key,
                            dependency=dep_path,
                            cached_hash=cached_hash[:8],
                            current_hash=current_hash[:8],
                        )
                        return MISSING
                except (OSError, FileNotFoundError) as e:
                    logger.debug(
                        "dependency_hash_failed",
                        page=key,
                        dependency=dep_path,
                        error=str(e),
                    )
                    return MISSING

        return cached

    def invalidate_parsed_content(self, file_path: Path) -> bool:
        """
        Remove cached parsed content for a file.

        Args:
            file_path: Path to file

        Returns:
            True if cache entry was removed, False if not present
        """
        key = str(file_path)
        if key in self.parsed_content:
            del self.parsed_content[key]
            return True
        return False

    def get_parsed_content_stats(self) -> dict[str, Any]:
        """
        Get parsed content cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self.parsed_content:
            return {"cached_pages": 0, "total_size_mb": 0, "avg_size_kb": 0}

        total_size = sum(c.get("size_bytes", 0) for c in self.parsed_content.values())
        return {
            "cached_pages": len(self.parsed_content),
            "total_size_mb": total_size / 1024 / 1024,
            "avg_size_kb": (total_size / len(self.parsed_content) / 1024)
            if self.parsed_content
            else 0,
        }
